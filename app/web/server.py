#!/usr/bin/env python3
"""
MusicDL Web 后端 — 标准库实现（无第三方 Web 框架依赖）。

功能：
  GET  /                  -> 前端页面 (static/index.html)
  GET  /static/*          -> 静态资源
  GET  /api/health        -> 后端与 musicdl 依赖状态
  GET  /api/sources       -> 可用音乐来源列表（动态探测需凭证的来源）
  GET  /api/stream?id=    -> 音频代理（供在线试听，转发 Range）
  GET  /api/cover?id=     -> 封面代理（搜索结果封面，防防盗链）
  GET  /api/cookies       -> 凭证配置 + 当前缺凭证的来源
  POST /api/cookies       -> 保存凭证并重新探测可用性
  POST /api/search        -> 搜索（聚合多平台，一次性返回）
  POST /api/search/stream -> 搜索（NDJSON 流式返回运行过程 + 结果）
  POST /api/download      -> 下载指定结果
  POST /api/download/stream -> 下载（NDJSON 流式返回字节进度 + 日志）

设计：musicdl 依赖缺失时优雅降级——页面/来源列表仍可用，搜索与下载返回
明确错误，便于本地与镜像内快速判断问题。
"""
import gzip
import hashlib
import itertools
import json
import mimetypes
import os
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ROOT, "static")
REPO_ROOT = os.path.dirname(ROOT)                      # musicdl-docker-build
MUSICDL_DIR = os.path.join(REPO_ROOT, "musicdl")       # 源码树
OUTPUT_DIR = os.environ.get("MUSICDL_OUTPUT", os.path.join(REPO_ROOT, "downloads"))
CACHE_DIR = os.environ.get("MUSICDL_CACHE",
                           os.path.join(os.path.expanduser("~"), ".cache", "musicdl-web"))
HOST = os.environ.get("MUSICDL_HOST", "0.0.0.0")
PORT = int(os.environ.get("MUSICDL_PORT", "8000"))

# ---------------------------------------------------------------------------
# 重定向 musicdl 的日志目录（必须在导入 musicdl 之前）
# ---------------------------------------------------------------------------
# musicdl 的 LoggerHandle 在 import 阶段就会往「用户日志目录」写文件
# （Windows 走 Known Folder API，落到 %LOCALAPPDATA%\zcjin\musicdl\Logs）。
# 这带来两个问题：一是不受 MUSICDL_CACHE 控制、在系统目录留文件；
# 二是部分受限环境该路径不可写，会让 musicdl 直接导入失败。
# musicdl 用的是 `from platformdirs import user_log_dir`，所以在它 import 之前
# 替换 platformdirs.user_log_dir 即可生效（改环境变量在 Windows 上无效，
# 因为 platformdirs 走的是 Known Folder API）。
try:
    import platformdirs

    _MUSICDL_LOG_DIR = os.path.join(CACHE_DIR, "musicdl-logs")
    os.makedirs(_MUSICDL_LOG_DIR, exist_ok=True)
    platformdirs.user_log_dir = lambda *a, **k: _MUSICDL_LOG_DIR
except Exception:  # noqa: BLE001
    pass

# ---------------------------------------------------------------------------
# musicdl 可选加载
# ---------------------------------------------------------------------------
MUSICDL_AVAILABLE = False
MUSICDL_IMPORT_ERROR = ""
_musicdl = None
try:
    sys.path.insert(0, MUSICDL_DIR)
    from musicdl import musicdl as _musicdl
    MUSICDL_AVAILABLE = True
except Exception as exc:  # noqa: BLE001
    MUSICDL_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

# 标签写入、同源刮削与 AI 翻译（与本文件同目录）
import scraper  # noqa: E402
import tagger  # noqa: E402
import translator  # noqa: E402


# ---------------------------------------------------------------------------
# 凭证（Cookie）配置
# ---------------------------------------------------------------------------
# musicdl 的凭证通过「每个来源的 init cfg」注入，可用的键：
#   default_search_cookies / default_download_cookies / default_parse_cookies
#       —— 普通平台（TIDAL、Deezer、Qobuz、SoundCloud、网易云…）
#   quark_parser_config = {"cookies": "..."}
#       —— 夸克网盘系来源（FiveSong / Heishan / KKWS / Xiageba 硬性依赖，
#          另有十来个来源没它只能下 mp3）
# 三者都接受标准 Cookie 字符串（"k=v; k2=v2"），musicdl 内部用 cookies2dict 解析。
CREDENTIALS_FILE = os.path.join(CACHE_DIR, "credentials.json")
_CRED_LOCK = threading.Lock()


def load_credentials():
    """读取用户凭证。返回 {"quark": str, "sources": {来源名: cookie}}。"""
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        if isinstance(obj, dict):
            return {
                "quark": str(obj.get("quark") or "").strip(),
                "sources": {k: str(v).strip()
                            for k, v in (obj.get("sources") or {}).items() if str(v).strip()},
            }
    except Exception:  # noqa: BLE001
        pass
    return {"quark": "", "sources": {}}


def save_credentials(obj):
    """保存凭证，并让可用性探测与客户端缓存失效。"""
    global _UNAVAILABLE_CACHE
    data = {
        "quark": str((obj or {}).get("quark") or "").strip(),
        "sources": {k: str(v).strip()
                    for k, v in ((obj or {}).get("sources") or {}).items() if str(v).strip()},
    }
    with _CRED_LOCK:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    _UNAVAILABLE_CACHE = None          # 可用性可能变了
    with CLIENT_CACHE_LOCK:
        CLIENT_CACHE.clear()           # 旧客户端带着旧凭证，必须重建
    try:                               # 磁盘探测缓存也要作废
        os.remove(_probe_cache_path())
    except OSError:
        pass
    return data


def _source_cfg(source, creds=None):
    """构造单个来源的 init cfg：work_dir + 用户填写的凭证。"""
    creds = creds if creds is not None else load_credentials()
    cfg = {"work_dir": OUTPUT_DIR}
    ck = (creds.get("sources") or {}).get(source)
    if ck:
        cfg["default_search_cookies"] = ck
        cfg["default_download_cookies"] = ck
        cfg["default_parse_cookies"] = ck
    q = creds.get("quark")
    if q:
        # 传给所有来源：不用夸克的会忽略它（base 客户端统一有这个属性）
        cfg["quark_parser_config"] = {"cookies": q}
    return cfg


def _credential_hint(reason):
    """把 musicdl 的原始英文异常压成一行短提示（完整异常仍放在 title 里）。"""
    r = reason or ""
    for key, text in (
        ("quark_parser_config", "需要夸克网盘 Cookie"),
        ("SessionStorage", "会话字段格式不对"),
        ("cookies are not configured", "需要该平台登录 Cookie"),
        ("should be configured", "需要该平台登录 Cookie"),
        ("is not configured", "需要额外凭证"),
    ):
        if key in r:
            return text
    return "需要额外凭证"


_QUARK_SOURCE_CACHE = {}
_QUARK_SCOPE = None


def _source_uses_quark(source):
    """该来源是否靠 quark_parser_config 取下载地址（歌曲存放在夸克网盘）。

    结果与 musicdl 版本绑定、运行期不会变，所以必须缓存：
    inspect.getsource() 要逐个读文件并分词，57 个来源累计约 230ms；
    而凭证页每次打开都会用到，不缓存会让界面切过去先空一下再弹内容。
    """
    cached = _QUARK_SOURCE_CACHE.get(source)
    if cached is not None:
        return cached
    try:
        mod = _musicdl.MusicClientBuilder.REGISTERED_MODULES.get(source)
        if mod is None:
            result = False
        else:
            import inspect
            result = "quark_parser_config" in inspect.getsource(mod)
    except Exception:  # noqa: BLE001
        result = False
    _QUARK_SOURCE_CACHE[source] = result
    return result


def _quark_scope():
    """受夸克 Cookie 影响的来源总数（算一次就够）。"""
    global _QUARK_SCOPE
    if _QUARK_SCOPE is None:
        _QUARK_SCOPE = len([s for s in SOURCES if _source_uses_quark(s)])
    return _QUARK_SCOPE


def credentials_payload():
    """给前端的凭证页数据。

    按「需要什么凭证」分成两组：
      quark_slots —— 靠夸克网盘 Cookie 的来源（共用一个输入框，所以只列名字）
      slots       —— 各平台独立凭证（各自一个输入框）
    """
    creds = load_credentials()
    unavail = discover_unavailable()
    quark_slots, slots = [], []
    for n in SOURCES:
        if n not in unavail:
            continue
        item = {"name": n,
                "reason": unavail[n],
                "hint": _credential_hint(unavail[n]),
                "value": (creds.get("sources") or {}).get(n, "")}
        (quark_slots if "quark_parser_config" in unavail[n] else slots).append(item)
    return {
        "quark": creds.get("quark", ""),
        "quark_slots": quark_slots,
        "slots": slots,
        "unavailable_total": len(unavail),
        # 夸克凭证影响的来源数（这类来源的歌曲都存在夸克网盘）
        "quark_scope": _quark_scope(),
    }


def _parse_registered_sources():
    """获取可用的音乐来源列表。

    优先从已安装的 musicdl 读取注册表（容器 / 正常 pip 安装场景）；
    若 musicdl 不可用，再静态解析源码树作为降级路径。
    """
    # 1) 已安装的 musicdl —— 最可靠
    try:
        from musicdl.modules import MusicClientBuilder
        names = sorted(MusicClientBuilder.REGISTERED_MODULES.keys())
        if names:
            return names
    except Exception:  # noqa: BLE001
        pass
    # 2) 静态解析源码树（未安装依赖时的兜底）
    path = os.path.join(MUSICDL_DIR, "musicdl", "modules", "sources", "__init__.py")
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return []
    marker = "REGISTERED_MODULES = {"
    start = src.index(marker)
    end = src.index("}", start)
    block = src[start:end]
    return sorted(set(re.findall(r"'(\w+MusicClient)'\s*:", block)))


SOURCES = _parse_registered_sources()

# ---------------------------------------------------------------------------
# 运行时探测：找出所有"未配置凭证/依赖就无法初始化"的来源。
# 这些来源的 __init__ 会直接 assert（如需要夸克网盘 Cookie 的、需要 TIDAL Cookie 的），
# 若被选中会导致 MusicClient 整体构造失败，进而让整个搜索报错。
# 逐个来源 try 构造并缓存结果；前端据此灰显，后端据此兜底过滤。
# ---------------------------------------------------------------------------
_UNAVAILABLE_CACHE = None
_UNAVAILABLE_LOCK = threading.Lock()
_PROBE_TTL = 6 * 3600          # 探测结果缓存 6 小时


def _probe_cache_path():
    """来源探测结果落盘，重启后无需重跑（原每次约 3.7 秒）。"""
    return os.path.join(CACHE_DIR, "unavailable-sources.json")


def _short_reason(exc):
    msg = str(exc)
    msg = re.sub(r"https?://\S+", "", msg)
    msg = msg.strip().strip('"').strip("'").strip()
    return msg[:100] or type(exc).__name__


def discover_unavailable():
    global _UNAVAILABLE_CACHE
    if _UNAVAILABLE_CACHE is not None:
        return _UNAVAILABLE_CACHE
    with _UNAVAILABLE_LOCK:
        if _UNAVAILABLE_CACHE is not None:
            return _UNAVAILABLE_CACHE
        if not MUSICDL_AVAILABLE:
            _UNAVAILABLE_CACHE = {}
            return _UNAVAILABLE_CACHE

        sig = hashlib.sha1("\n".join(SOURCES).encode("utf-8")).hexdigest()[:12]
        try:                                     # 命中磁盘缓存则直接返回
            with open(_probe_cache_path(), "r", encoding="utf-8") as fh:
                obj = json.load(fh)
            if obj.get("sig") == sig and (time.time() - float(obj.get("ts", 0))) < _PROBE_TTL:
                _UNAVAILABLE_CACHE = obj.get("unavailable") or {}
                return _UNAVAILABLE_CACHE
        except Exception:  # noqa: BLE001
            pass

        result = {}
        creds = load_credentials()
        for s in SOURCES:
            try:
                _musicdl.MusicClient(
                    music_sources=[s],
                    init_music_clients_cfg={s: _source_cfg(s, creds)},
                )
            except Exception as exc:  # noqa: BLE001
                result[s] = _short_reason(exc)
        _UNAVAILABLE_CACHE = result

        try:                                     # 写回缓存
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(_probe_cache_path(), "w", encoding="utf-8") as fh:
                json.dump({"sig": sig, "ts": time.time(), "unavailable": result},
                          fh, ensure_ascii=False)
        except Exception:  # noqa: BLE001
            pass
        return result


def available_sources():
    unavail = discover_unavailable()
    return [s for s in SOURCES if s not in unavail]


# ---------------------------------------------------------------------------
# 运行过程流：搜索时的真实日志 + 进度
# ---------------------------------------------------------------------------
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def _musicdl_log_path():
    """musicdl 日志文件路径（disable_print=True 时 LoggerHandle 写这里）。"""
    try:
        from platformdirs import user_log_dir
        return os.path.join(user_log_dir(appname="musicdl", appauthor="zcjin"), "musicdl.log")
    except Exception:  # noqa: BLE001
        return None


def _open_log_tail():
    """打开 musicdl 日志并定位末尾，只读后续新增行。"""
    path = _musicdl_log_path()
    if not path or not os.path.exists(path):
        return None
    try:
        fp = open(path, "r", encoding="utf-8", errors="replace")
        fp.seek(0, os.SEEK_END)
        return fp
    except Exception:  # noqa: BLE001
        return None


def _drain_log(fp):
    """读取日志新增行（剥掉 ANSI 颜色码）。"""
    if fp is None:
        return []
    out = []
    try:
        for raw in fp:
            line = ANSI_RE.sub("", raw).rstrip()
            if line.strip():
                out.append(line)
    except Exception:  # noqa: BLE001
        pass
    return out


def _search_one_source(client, source, keyword):
    """对单个来源执行搜索（与 MusicClient.search 内部调用方式一致）。"""
    return client.music_clients[source].search(
        keyword=keyword,
        num_threadings=client.clients_threadings.get(source, 5),
        request_overrides=client.requests_overrides.get(source, {}),
        rule=client.search_rules.get(source, {}),
    )


def _flatten_output(save_path):
    """把下载产物拍平到 OUTPUT_DIR 根目录，并清掉 musicdl 建的多层空目录。

    musicdl 会写成 <OUTPUT_DIR>/<来源>/<时间戳 歌名>/<文件>，
    这里把该目录下的所有文件（含自动附带的 .lrc）搬到 <OUTPUT_DIR>/ 下，
    再逐级删除空目录，最终只留一个 downloads/ 目录。
    """
    if not save_path:
        return save_path
    try:
        root = os.path.abspath(OUTPUT_DIR)
        src = os.path.abspath(save_path)
        src_dir = os.path.dirname(src)
        if src_dir == root or not os.path.isfile(src):
            return save_path
        os.makedirs(root, exist_ok=True)

        new_main = save_path
        for name in sorted(os.listdir(src_dir)):
            cur = os.path.join(src_dir, name)
            if not os.path.isfile(cur):
                continue
            if name.endswith(".pkl"):                 # musicdl 的元数据缓存，直接丢掉
                try:
                    os.remove(cur)
                except OSError:
                    pass
                continue
            dest = os.path.join(root, name)
            base, ext = os.path.splitext(name)
            n = 1
            while os.path.exists(dest):                 # 重名则加序号，不覆盖
                dest = os.path.join(root, f"{base} ({n}){ext}")
                n += 1
            try:
                shutil.move(cur, dest)
            except Exception:  # noqa: BLE001
                continue
            if os.path.abspath(cur) == src:
                new_main = dest

        cur_dir = src_dir                                 # 逐级删空目录
        while cur_dir != root and cur_dir.startswith(root + os.sep):
            try:
                os.rmdir(cur_dir)
            except OSError:
                break
            cur_dir = os.path.dirname(cur_dir)
        return new_main
    except Exception:  # noqa: BLE001
        return save_path


def _tidy_output():
    """清掉 musicdl 散落的元数据缓存（*.pkl）与空目录，让 downloads/ 里只剩音频文件。"""
    try:
        root = os.path.abspath(OUTPUT_DIR)
        if not os.path.isdir(root):
            return
        for cur_dir, _dirs, files in os.walk(root, topdown=False):
            for name in files:
                if name.endswith(".pkl"):
                    try:
                        os.remove(os.path.join(cur_dir, name))
                    except OSError:
                        pass
            if os.path.abspath(cur_dir) != root:
                try:
                    os.rmdir(cur_dir)          # 仅当目录为空才会成功
                except OSError:
                    pass
    except Exception:  # noqa: BLE001
        pass


def _parse_size_bytes(s):
    """把 "6.16 MB" 这类字符串换算成字节数（用于估算下载进度）。"""
    m = re.search(r"([\d.]+)\s*(TB|GB|MB|KB|B)?", str(s or ""), re.I)
    if not m:
        return 0
    try:
        n = float(m.group(1))
    except ValueError:
        return 0
    mul = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4}
    return int(n * mul.get((m.group(2) or "B").upper(), 1))


def _watch_size(root, since):
    """返回 root 下「since 之后被修改过的文件」中的最大体积，用于估算下载字节数。"""
    best = 0
    try:
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.endswith(".pkl"):
                    continue
                try:
                    st = os.stat(os.path.join(dirpath, f))
                except OSError:
                    continue
                if st.st_mtime >= since and st.st_size > best:
                    best = st.st_size
    except Exception:  # noqa: BLE001
        pass
    return best


def _safe_filename(s):
    """清掉文件名里的非法字符。"""
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", str(s or ""))
    s = re.sub(r"\s+", " ", s).strip().strip(".")
    return s or "unknown"



def _postprocess_downloaded(audio_path, song, client=None, progress=None):
    """下载后处理：同源刮削 → AI 翻译歌词 → 写标签 → 重命名。

    刮削一律以「下载所用的来源」为准（见 scraper.build_meta），
    不会出现 QQ 下的歌挂上网易云封面这种串味。
    歌词只在确实写进音频本体后才删 .lrc，否则保留。
    progress: 可选回调 fn(text)，把每一步实时输出到下载日志。
    """
    def say(msg):
        if progress:
            try:
                progress(msg)
            except Exception:  # noqa: BLE001
                pass

    result = {"lyrics_embedded": False, "cover_embedded": False,
              "tags_written": [], "scraped": None, "path": audio_path,
              "translated": False}
    if not audio_path or not os.path.isfile(audio_path):
        return result

    title = getattr(song, "song_name", None) or ""
    artist = getattr(song, "singers", None) or ""

    # 1) 同源刮削（失败不影响后续，退化为只用 SongInfo 自带字段）
    meta, cover, lyrics = {}, None, None
    try:
        meta = scraper.build_meta(song, client, progress=say) if song is not None else {}
        cover = meta.pop("cover", None)
        lyrics = meta.pop("lyrics", None)
        result["scraped"] = meta.pop("scraped", None)
    except Exception as exc:  # noqa: BLE001
        result["scrape_error"] = f"{type(exc).__name__}: {exc}"
        say(f"刮削异常：{type(exc).__name__}: {exc}")
        meta = {"title": title, "artist": artist}

    title = meta.get("title") or title
    artist = meta.get("artist") or artist

    # 2) 刮削没给歌词就退回同名 .lrc
    d = os.path.dirname(audio_path)
    lrc = os.path.join(d, os.path.splitext(os.path.basename(audio_path))[0] + ".lrc")
    if not os.path.isfile(lrc):
        try:
            cands = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".lrc")]
            lrc = cands[0] if len(cands) == 1 else None
        except OSError:
            lrc = None
    from_lrc = False
    if not lyrics and lrc and os.path.isfile(lrc):
        try:
            with open(lrc, "r", encoding="utf-8", errors="replace") as fh:
                lyrics = fh.read().strip() or None
            from_lrc = bool(lyrics)
            say("歌词：取自同名 .lrc 文件")
        except OSError:
            lyrics = None
    elif lyrics:
        say("歌词：来自刮削结果")

    # 2.5) AI 翻译（可选）
    ai_cfg = translator.load_config(CACHE_DIR)
    if lyrics and translator.is_ready(ai_cfg) and ai_cfg.get("translate_lyrics"):
        target = ai_cfg.get("target_lang") or "中文"
        say(f"AI 翻译：正在译为{target}…")
        t0 = time.time()
        translated, err = translator.translate_lyrics(lyrics, ai_cfg, progress=say)
        if translated:
            result["translated"] = True
            result["translated_lang"] = target
            result["translated_lyrics"] = translated
            if ai_cfg.get("embed_bilingual", True):
                lyrics = translator.make_bilingual(lyrics, translated)
                say(f"AI 翻译：完成（{time.time()-t0:.1f}s），写入双语歌词")
            else:
                lyrics = translated
                say(f"AI 翻译：完成（{time.time()-t0:.1f}s），只写入译文")
        else:
            say(f"AI 翻译失败，保留原文：{err}")
            result["translate_error"] = err
    elif lyrics:
        say("AI 翻译：未启用，跳过")

    # 3) 写标签
    size_before = os.path.getsize(audio_path) if os.path.isfile(audio_path) else -1
    w = tagger.write_tags(audio_path, meta, cover=cover, lyrics=lyrics)
    result["tags_written"] = w["written"]
    result["debug"] = {
        "audio_path_in": audio_path,
        "size_before": size_before,
        "size_after": os.path.getsize(audio_path) if os.path.isfile(audio_path) else -1,
        "write_error": w["error"],
        "cover_bytes": len(cover) if cover else 0,
        "lyrics_chars": len(lyrics or ""),
        "lyrics_lines": len((lyrics or "").splitlines()),
    }
    if w["error"]:
        result["tag_error"] = w["error"]

    # 标志位以「文件真实状态」为准：musicdl 下载时自己也会写基础标签和封面，
    # 只看我们这次调用的返回值会把「本来就有封面」误报成没有。
    back = tagger.read_tags(audio_path)
    result["cover_embedded"] = bool(back.get("cover"))
    result["lyrics_embedded"] = bool(back.get("lyrics"))
    result["final_tags"] = back.get("tags") or {}
    result["cover_by_us"] = bool(w["cover"])
    result["lyrics_by_us"] = bool(w["lyrics"])

    # 只要歌词确实写进了音频本体，就删掉散落的 .lrc —— 无论歌词来自刮削还是 .lrc 本身。
    # 否则刮削路径会把 .lrc 留成孤儿文件（音频已被重命名，.lrc 却没动）。
    if result["lyrics_embedded"] and lrc and os.path.isfile(lrc):
        try:
            os.remove(lrc)
        except OSError:
            pass

    # 4) 重命名成 标题_歌手.ext
    ext = os.path.splitext(audio_path)[1]
    base = f"{_safe_filename(title)}_{_safe_filename(artist)}".strip("_")
    if base:
        dest = os.path.join(d, base + ext)
        n = 1
        while os.path.exists(dest) and os.path.abspath(dest) != os.path.abspath(audio_path):
            dest = os.path.join(d, f"{base} ({n}){ext}")
            n += 1
        if os.path.abspath(dest) != os.path.abspath(audio_path):
            try:
                shutil.move(audio_path, dest)
                result["path"] = dest
            except Exception:  # noqa: BLE001
                pass
    return result


def _finalize_download(song, downloaded, client=None, progress=None):
    """下载后处理（同源刮削 + AI 翻译 + 写标签）+ 拍平 + 清理。"""
    saved = []
    for d in (downloaded or []):
        # 以「实际下载下来的那条 SongInfo」为主体去刮削，来源天然一致
        info = _postprocess_downloaded(getattr(d, "save_path", None),
                                       d if d is not None else song, client,
                                       progress=progress)
        saved.append({
            "song_name": getattr(d, "song_name", None) or getattr(song, "song_name", None),
            "save_path": _flatten_output(info["path"]),
            "lyrics_embedded": info["lyrics_embedded"],
            "cover_embedded": info["cover_embedded"],
            "tags_written": info["tags_written"],
            "scraped": info.get("scraped"),
            "source": getattr(d, "source", None) or getattr(song, "source", None),
            "translated": info.get("translated", False),
            "translated_lang": info.get("translated_lang"),
            "translate_error": info.get("translate_error"),
            # 调试用：写完后立刻读回的真实标签，确认有没有被后续步骤覆盖
            "final_tags": info.get("final_tags"),
            "tag_error": info.get("tag_error"),
            "scrape_error": info.get("scrape_error"),
            "debug": info.get("debug"),
        })
    _tidy_output()
    return saved

# ---------------------------------------------------------------------------
# 运行时缓存
# ---------------------------------------------------------------------------
SEARCH_CACHE = {}          # id -> SongInfo
SEARCH_CACHE_LOCK = threading.Lock()
SEARCH_CACHE_MAX = 600     # 上限：容器长期运行也不会被搜索结果把内存吃穿
_SEARCH_SEQ = itertools.count(1)   # 单调序号，保证 id 唯一（不能用 len()，淘汰后会重号）
CLIENT_CACHE = {}          # (sources tuple) -> MusicClient
CLIENT_CACHE_LOCK = threading.Lock()


def _cache_song(source, song):
    """把一条搜索结果放进缓存并返回给前端的 id（调用方需持有 SEARCH_CACHE_LOCK）。

    超出上限时按写入顺序淘汰最老的条目 —— 前端拿到的是旧结果时只会收到
    「结果已过期，请重新搜索」，比进程越跑内存越大要好。
    """
    rid = "%s::%s::%d" % (source, song.identifier, next(_SEARCH_SEQ))
    SEARCH_CACHE[rid] = song
    overflow = len(SEARCH_CACHE) - SEARCH_CACHE_MAX
    if overflow > 0:
        for old_key in list(SEARCH_CACHE)[:overflow]:
            SEARCH_CACHE.pop(old_key, None)
    return rid


def get_client(sources):
    key = tuple(sorted(sources))
    creds = load_credentials()
    with CLIENT_CACHE_LOCK:
        if key not in CLIENT_CACHE:
            cfg = {s: _source_cfg(s, creds) for s in sources}
            CLIENT_CACHE[key] = _musicdl.MusicClient(
                music_sources=list(sources), init_music_clients_cfg=cfg)
        return CLIENT_CACHE[key]


def _is_previewable(song):
    """能否在线试听：直接的 http(s) 音频地址，且不是 HLS 流。"""
    url = getattr(song, "download_url", None)
    proto = str(getattr(song, "protocol", "HTTP") or "HTTP").upper()
    return bool(isinstance(url, str) and url.startswith("http") and proto != "HLS")


def serialize_song(song, rid):
    return {
        "id": rid,
        "source": song.source,
        "song_name": song.song_name,
        "singers": song.singers,
        "album": song.album,
        "ext": song.ext,
        "file_size": song.file_size,
        "duration": song.duration,
        "cover_url": song.cover_url,
        "previewable": _is_previewable(song),
    }


# ---------------------------------------------------------------------------
# 静态资源 gzip 缓存
# ---------------------------------------------------------------------------
_GZIP_CACHE = {}          # abs path -> (mtime, gz_bytes)
_GZIP_LOCK = threading.Lock()


def _gzip_cached(path, body, mtime):
    """按 mtime 缓存 gzip 结果，避免每次请求都重新压缩。"""
    with _GZIP_LOCK:
        hit = _GZIP_CACHE.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
    try:
        data = gzip.compress(body, 6)
    except Exception:  # noqa: BLE001
        return None
    if len(data) >= len(body):        # 压不小就别压
        return None
    with _GZIP_LOCK:
        _GZIP_CACHE[path] = (mtime, data)
    return data


# ---------------------------------------------------------------------------
# HTTP 处理器
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "MusicDLWeb/1.0"

    # -- 工具 --
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _serve_static(self, rel_path):
        rel_path = rel_path.lstrip("/")
        if rel_path.startswith("static/"):
            rel_path = rel_path[len("static/"):]
        if rel_path in ("", "/"):
            rel_path = "index.html"
        # 防目录穿越
        full = os.path.normpath(os.path.join(STATIC_DIR, rel_path))
        if not full.startswith(os.path.normpath(STATIC_DIR)):
            self._send_json(403, {"error": "forbidden"})
            return
        if not os.path.isfile(full):
            self._send_json(404, {"error": "not found"})
            return

        st = os.stat(full)
        # 带 ETag 协商缓存：浏览器每次会带 If-None-Match 询问，
        # 文件没变就回 304（无响应体）——既省流量，又能立刻感知改动。
        etag = '"%x-%x"' % (int(st.st_mtime), st.st_size)
        # 自有的前端资源一律走「可缓存但必须校验」：配合 ETag，未变时只回 304（几十字节），
        # 变了立刻生效。这里不能对 .css 用 max-age —— 否则 HTML/JS 已更新而 CSS 还是旧的，
        # 结构与样式错配会直接把界面弄乱（这种「新 JS + 旧 CSS」正是布局出错的常见来源）。
        cache_ctl = "no-cache" if full.endswith((".html", ".js", ".css")) else "public, max-age=3600"
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache_ctl)
            self.end_headers()
            return

        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if full.endswith((".html", ".css", ".js")):
            ctype += "; charset=utf-8"
        with open(full, "rb") as fh:
            body = fh.read()

        # 文本资源 gzip 压缩（结果按 mtime 缓存，不重复压缩）
        gz = None
        if (len(body) >= 1024
                and full.endswith((".html", ".css", ".js", ".json", ".svg"))
                and "gzip" in (self.headers.get("Accept-Encoding") or "").lower()):
            gz = _gzip_cached(full, body, st.st_mtime)

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", self.date_time_string(int(st.st_mtime)))
        self.send_header("Cache-Control", cache_ctl)
        if gz is not None:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(gz)))
            self.end_headers()
            self.wfile.write(gz)
            return
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- 音频代理：供前端 <audio> 在线试听（转发 Range，支持拖动进度） --
    def _stream_audio(self, qs):
        EXT_MIME = {
            "mp3": "audio/mpeg", "flac": "audio/flac", "m4a": "audio/mp4", "mp4": "audio/mp4",
            "ogg": "audio/ogg", "oga": "audio/ogg", "opus": "audio/ogg", "wav": "audio/wav",
            "aac": "audio/aac", "wma": "audio/x-ms-wma", "ape": "audio/x-ape",
        }
        song_id = (qs.get("id") or [""])[0]
        with SEARCH_CACHE_LOCK:
            song = SEARCH_CACHE.get(song_id)
        if song is None:
            self._send_json(404, {"error": "结果已过期，请重新搜索"})
            return

        # 已在内存中的内容（少数来源）
        contents = getattr(song, "downloaded_contents", None)
        if contents:
            try:
                data = bytes(contents)
            except Exception:  # noqa: BLE001
                data = b""
            if data:
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(data)
                except Exception:  # noqa: BLE001
                    pass
                return

        if not _is_previewable(song):
            self._send_json(400, {"error": "该结果不支持在线试听（非直接音频地址或为 HLS 流）"})
            return

        url = song.download_url
        base_headers = {"User-Agent": "Mozilla/5.0"}
        for k, v in (getattr(song, "default_download_headers", None) or {}).items():
            try:
                base_headers[str(k)] = str(v)
            except Exception:  # noqa: BLE001
                pass
        cookies = getattr(song, "default_download_cookies", None)
        if isinstance(cookies, dict) and cookies and "Cookie" not in base_headers:
            try:
                base_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())
            except Exception:  # noqa: BLE001
                pass

        ctype_holder = {"v": None}

        def fetch(lo, hi):
            """取一段「有界」Range。上游对无界/超大请求的响应延迟与字节数成正比，必须切块。"""
            h = dict(base_headers)
            h["Range"] = f"bytes={lo}-{hi}"
            up = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60)
            if ctype_holder["v"] is None:
                raw = (up.headers.get("Content-Type") or "").split(";")[0].strip()
                if not raw or raw in ("application/octet-stream", "binary/octet-stream"):
                    ext = str(getattr(song, "ext", "") or "").lstrip(".").lower()
                    raw = EXT_MIME.get(ext, "application/octet-stream")
                ctype_holder["v"] = raw
            return up

        # 解析客户端请求的区间
        rng = self.headers.get("Range")
        start, end_req = 0, None
        if rng and rng.strip().lower().startswith("bytes="):
            spec = rng.strip()[6:].split(",")[0].strip()
            if "-" in spec:
                a, b = spec.split("-", 1)
                try:
                    start = int(a) if a.strip() else 0
                    end_req = int(b) if b.strip() else None
                except ValueError:
                    start, end_req = 0, None

        # 探测总长度（1 字节，极快），用于把开放式请求转成有界块
        total = None
        try:
            probe = fetch(0, 0)
            cr = probe.headers.get("Content-Range") or ""
            probe.close()
            if "/" in cr:
                total = int(cr.rsplit("/", 1)[1])
        except Exception:  # noqa: BLE001
            total = None

        if total is None:
            # 探测失败：退化为一次性直连转发
            try:
                h = dict(base_headers)
                if rng:
                    h["Range"] = rng
                up = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60)
                self.send_response(getattr(up, "status", 200))
                self.send_header("Content-Type", ctype_holder["v"] or "application/octet-stream")
                for name in ("Content-Length", "Content-Range"):
                    if up.headers.get(name):
                        self.send_header(name, up.headers[name])
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                while True:
                    b = up.read(64 * 1024)
                    if not b:
                        break
                    self.wfile.write(b)
                up.close()
            except Exception:  # noqa: BLE001
                pass
            return

        if end_req is None or end_req >= total:
            end_req = total - 1
        if start > end_req:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{total}")
            self.end_headers()
            return

        want = end_req - start + 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype_holder["v"] or "application/octet-stream")
        self.send_header("Content-Length", str(want))
        self.send_header("Accept-Ranges", "bytes")
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end_req}/{total}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        CHUNK, pos, sent = 1024 * 1024, start, 0
        while sent < want:
            stop = min(pos + CHUNK - 1, end_req)
            try:
                up = fetch(pos, stop)
            except Exception:  # noqa: BLE001
                break
            try:
                while True:
                    b = up.read(64 * 1024)
                    if not b:
                        break
                    self.wfile.write(b)
                    sent += len(b)
            except Exception:  # noqa: BLE001
                return          # 客户端断开（如拖动进度条）
            finally:
                try:
                    up.close()
                except Exception:  # noqa: BLE001
                    pass
            pos = stop + 1

    # -- 封面代理：只允许取本次搜索结果里的 cover_url（避免成为开放代理） --
    def _cover_image(self, qs):
        rid = (qs.get("id") or [""])[0]
        with SEARCH_CACHE_LOCK:
            song = SEARCH_CACHE.get(rid)
        if song is None:
            self._send_json(404, {"error": "结果已过期，请重新搜索"})
            return
        url = getattr(song, "cover_url", None)
        if not (isinstance(url, str) and url.startswith("http")):
            self._send_json(404, {"error": "该结果没有封面"})
            return

        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            upstream = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15)
        except Exception as exc:  # noqa: BLE001
            self._send_json(502, {"error": f"封面获取失败：{type(exc).__name__}"})
            return
        try:
            data = upstream.read(4 * 1024 * 1024)     # 封面不必太大，4MB 上限
            ctype = (upstream.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip()
        except Exception:  # noqa: BLE001
            data, ctype = b"", "image/jpeg"
        finally:
            try:
                upstream.close()
            except Exception:  # noqa: BLE001
                pass
        if not data:
            self._send_json(502, {"error": "封面内容为空"})
            return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:  # noqa: BLE001
            pass

    # -- 路由 --
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/favicon.ico":
            # 浏览器对标签页图标的兜底请求；HTML 里已声明 SVG/PNG 图标，这里再兜一手避免 404
            self._serve_static("/static/favicon.ico")
        elif path in ("/", "/index.html") or path.startswith("/static/"):
            self._serve_static(path)
        elif path == "/api/health":
            self._send_json(200, {
                "ready": MUSICDL_AVAILABLE,
                "sources": len(SOURCES),
                "output_dir": OUTPUT_DIR,
                "error": MUSICDL_IMPORT_ERROR or None,
            })
        elif path == "/api/sources":
            unavail = discover_unavailable()
            self._send_json(200, {
                "sources": [s for s in SOURCES if s not in unavail],
                "unavailable": unavail,
            })
        elif path == "/api/cookies":
            self._send_json(200, credentials_payload())
        elif path == "/api/ai":
            cfg = translator.load_config(CACHE_DIR)
            # 不回传完整 api_key，只给一个掩码，避免明文四处传播
            safe = dict(cfg)
            key = safe.get("api_key") or ""
            safe["api_key_set"] = bool(key)
            safe["api_key"] = (key[:4] + "…" + key[-4:]) if len(key) > 10 else ("已设置" if key else "")
            self._send_json(200, {"config": safe, "target_langs": translator.TARGET_LANGS})
        elif path == "/api/stream":
            self._stream_audio(parse_qs(urlparse(self.path).query))
        elif path == "/api/cover":
            self._cover_image(parse_qs(urlparse(self.path).query))
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_json()
        if path == "/api/search":
            self._search(body)
        elif path == "/api/search/stream":
            self._search_stream(body)
        elif path == "/api/download":
            self._download(body)
        elif path == "/api/download/stream":
            self._download_stream(body)
        elif path == "/api/cookies":
            self._save_cookies(body)
        elif path == "/api/ai":
            self._save_ai(body)
        elif path == "/api/ai/test":
            self._test_ai(body)
        else:
            self._send_json(404, {"error": "not found"})

    def _search(self, body):
        if not MUSICDL_AVAILABLE:
            self._send_json(503, {"error": "musicdl 依赖未安装，无法搜索：", "detail": MUSICDL_IMPORT_ERROR})
            return
        keyword = (body.get("keyword") or "").strip()
        sources = body.get("sources") or []
        if not keyword or not sources:
            self._send_json(400, {"error": "keyword 与 sources 均为必填"})
            return
        valid = [s for s in sources if s in available_sources()]
        if not valid:
            self._send_json(400, {"error": "无有效来源", "detail": f"valid sources are {available_sources()}"})
            return
        try:
            client = get_client(valid)
            raw = client.search(keyword=keyword)   # dict[source -> list[SongInfo]]
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": f"搜索异常：{type(exc).__name__}: {exc}"})
            return

        results = []
        with SEARCH_CACHE_LOCK:
            for src, songs in (raw or {}).items():
                for song in songs or []:
                    results.append(serialize_song(song, _cache_song(src, song)))
        self._send_json(200, {"results": results})

    def _search_stream(self, body):
        """NDJSON 流式搜索：先实时吐运行过程（musicdl 日志 + 每来源进度），最后吐结果。"""
        def emit(obj):
            try:
                self.wfile.write((json.dumps(obj, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
                self.wfile.flush()
                return True
            except Exception:  # noqa: BLE001
                return False

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        if not MUSICDL_AVAILABLE:
            emit({"type": "fatal", "error": "musicdl 依赖未安装", "detail": MUSICDL_IMPORT_ERROR})
            return

        keyword = (body.get("keyword") or "").strip()
        sources = body.get("sources") or []
        valid = [s for s in sources if s in available_sources()]
        if not keyword or not valid:
            emit({"type": "fatal", "error": "keyword 与 sources 均为必填（且需至少一个可用来源）"})
            return

        emit({"type": "phase", "text": f"关键字「{keyword}」· {len(valid)} 个来源 · 输出 {OUTPUT_DIR}"})
        try:
            client = get_client(valid)
        except Exception as exc:  # noqa: BLE001
            emit({"type": "fatal", "error": f"客户端初始化失败：{type(exc).__name__}: {exc}"})
            return

        log_fp = _open_log_tail()
        t0 = time.time()
        gathered, failed = {}, {}

        def run_source(src):
            st = time.time()
            try:
                return src, (_search_one_source(client, src, keyword) or []), time.time() - st, None
            except Exception as exc:  # noqa: BLE001
                return src, None, time.time() - st, f"{type(exc).__name__}: {exc}"

        try:
            for s in valid:
                emit({"type": "start", "source": s, "text": f"→ {s}"})
            with ThreadPoolExecutor(max_workers=min(len(valid), 10)) as pool:
                futures = [pool.submit(run_source, s) for s in valid]
                pending = set(futures)
                while pending:
                    finished = [f for f in pending if f.done()]
                    if not finished:
                        for line in _drain_log(log_fp):
                            emit({"type": "log", "text": line})
                        time.sleep(0.1)
                        continue
                    for fut in finished:
                        pending.discard(fut)
                        src, songs, dur, err = fut.result()
                        dur = round(dur, 2)
                        if err is None:
                            gathered[src] = songs
                            emit({"type": "done_source", "source": src, "count": len(songs), "elapsed": dur})
                        else:
                            failed[src] = err
                            emit({"type": "error_source", "source": src, "error": err, "elapsed": dur})
                    for line in _drain_log(log_fp):
                        emit({"type": "log", "text": line})
        finally:
            for line in _drain_log(log_fp):
                emit({"type": "log", "text": line})
            if log_fp:
                try:
                    log_fp.close()
                except Exception:  # noqa: BLE001
                    pass

        results = []
        with SEARCH_CACHE_LOCK:
            for src, songs in gathered.items():
                for song in songs:
                    results.append(serialize_song(song, _cache_song(src, song)))

        emit({
            "type": "finished",
            "total": len(results),
            "ok_sources": len(gathered),
            "failed_sources": failed,
            "elapsed": round(time.time() - t0, 2),
            "results": results,
        })

    def _save_cookies(self, body):
        """保存凭证并重新探测可用性（填对 Cookie 后原本不可用的来源会变为可用）。"""
        if not MUSICDL_AVAILABLE:
            self._send_json(503, {"error": "musicdl 依赖未安装"})
            return
        save_credentials({"quark": body.get("quark") or "",
                          "sources": body.get("sources") or {}})
        unavail = discover_unavailable()          # 重新跑一遍探测
        payload = credentials_payload()
        payload["available"] = len([s for s in SOURCES if s not in unavail])
        payload["unavailable"] = len(unavail)
        self._send_json(200, payload)

    def _ai_payload(self):
        cfg = translator.load_config(CACHE_DIR)
        safe = dict(cfg)
        key = safe.get("api_key") or ""
        safe["api_key_set"] = bool(key)
        safe["api_key"] = (key[:4] + "…" + key[-4:]) if len(key) > 10 else ("已设置" if key else "")
        return {"config": safe, "target_langs": translator.TARGET_LANGS}

    def _save_ai(self, body):
        """保存 AI 翻译配置。

        注意：前端拿到的 api_key 是掩码，所以这里遇到掩码值（含 … 或「已设置」）
        表示「沿用原来的密钥」，绝不能把它当成新密钥覆盖掉。
        """
        old = translator.load_config(CACHE_DIR)
        incoming = dict(body or {})
        key = str(incoming.get("api_key") or "").strip()
        if not key or "…" in key or key == "已设置":
            incoming["api_key"] = old.get("api_key") or ""
        if incoming.get("clear_api_key"):
            incoming["api_key"] = ""
        translator.save_config(CACHE_DIR, incoming)
        self._send_json(200, self._ai_payload())

    def _test_ai(self, body):
        """连通性测试。允许用页面上尚未保存的值直接测。"""
        old = translator.load_config(CACHE_DIR)
        cfg = dict(old)
        incoming = dict(body or {})
        key = str(incoming.get("api_key") or "").strip()
        if key and "…" not in key and key != "已设置":
            cfg["api_key"] = key
        for k in ("base_url", "model", "target_lang"):
            if incoming.get(k):
                cfg[k] = incoming[k]
        ok, msg = translator.test_config(cfg)
        self._send_json(200 if ok else 400, {"ok": ok, "message": msg})

    def _download(self, body):
        if not MUSICDL_AVAILABLE:
            self._send_json(503, {"error": "musicdl 依赖未安装，无法下载：", "detail": MUSICDL_IMPORT_ERROR})
            return
        song_id = body.get("id") or (body.get("song") or {}).get("id")
        with SEARCH_CACHE_LOCK:
            song = SEARCH_CACHE.get(song_id)
        if song is None:
            self._send_json(404, {"error": "结果已过期，请重新搜索后再下载"})
            return
        try:
            client = get_client([song.source])
            downloaded = client.download(song_infos=[song])
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": f"下载异常：{type(exc).__name__}: {exc}"})
            return
        saved = _finalize_download(song, downloaded, client)
        self._send_json(200, {"saved": saved, "count": len(saved)})

    def _download_stream(self, body):
        """NDJSON 流式下载：真实字节进度 + musicdl 日志，前端把进度画成圆环。"""
        def emit(obj):
            try:
                self.wfile.write((json.dumps(obj, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
                self.wfile.flush()
                return True
            except Exception:  # noqa: BLE001
                return False

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        if not MUSICDL_AVAILABLE:
            emit({"type": "fatal", "error": "musicdl 依赖未安装"})
            return

        song_id = body.get("id") or (body.get("song") or {}).get("id")
        with SEARCH_CACHE_LOCK:
            song = SEARCH_CACHE.get(song_id)
        if song is None:
            emit({"type": "fatal", "error": "结果已过期，请重新搜索后再下载"})
            return

        title = getattr(song, "song_name", None) or "unknown"
        artist = getattr(song, "singers", None) or ""
        emit({"type": "phase", "text": f"{title} — {artist}".strip(" —")})
        emit({"type": "progress", "pct": 5, "text": "准备"})

        log_fp = _open_log_tail()
        try:
            emit({"type": "progress", "pct": 12, "text": "初始化客户端"})
            try:
                client = get_client([song.source])
            except Exception as exc:  # noqa: BLE001
                emit({"type": "fatal", "error": f"客户端初始化失败：{type(exc).__name__}: {exc}"})
                return

            expected = _parse_size_bytes(getattr(song, "file_size", ""))
            size_txt = f"{expected / 1048576:.1f} MB" if expected else "大小未知"
            emit({"type": "progress", "pct": 18, "text": f"开始下载（{size_txt}）"})

            box = {}

            def worker():
                try:
                    box["result"] = client.download(song_infos=[song])
                except Exception as exc:  # noqa: BLE001
                    box["error"] = f"{type(exc).__name__}: {exc}"

            started = time.time()
            th = threading.Thread(target=worker, daemon=True)
            th.start()
            while th.is_alive():
                for line in _drain_log(log_fp):
                    emit({"type": "log", "text": line})
                got = _watch_size(OUTPUT_DIR, started - 1)
                if expected > 0:
                    pct = 18 + int(min(got / expected, 1.0) * 56)          # 18% → 74%
                    text = f"下载中 {got / 1048576:.1f} / {expected / 1048576:.1f} MB"
                else:
                    pct, text = 45, f"下载中 {got / 1048576:.1f} MB"
                emit({"type": "progress", "pct": pct, "text": text})
                time.sleep(0.4)
            th.join()
            for line in _drain_log(log_fp):
                emit({"type": "log", "text": line})

            if "error" in box:
                emit({"type": "fatal", "error": f"下载失败：{box['error']}"})
                return

            emit({"type": "progress", "pct": 78, "text": "音频下载完成"})
            emit({"type": "progress", "pct": 82, "text": "刮削元数据…"})

            # 把刮削/翻译过程实时写进下载日志（前端那块的输出窗口）
            def on_step(msg):
                emit({"type": "log", "text": msg})

            saved = _finalize_download(song, box.get("result"), client, progress=on_step)

            emit({"type": "progress", "pct": 94, "text": "写入标签…"})
            for line in _drain_log(log_fp):
                emit({"type": "log", "text": line})
            for s in saved:
                if s.get("tags_written"):
                    emit({"type": "log",
                          "text": f"已写入标签 {len(s['tags_written'])} 项："
                                  + "、".join(s["tags_written"])})
                if s.get("cover_embedded"):
                    emit({"type": "log", "text": "封面：已嵌入音频文件"})
                if s.get("translated"):
                    emit({"type": "log",
                          "text": f"AI 翻译：已写入{ s.get('translated_lang') or ''}歌词"})
                elif s.get("translate_error"):
                    emit({"type": "log", "text": f"AI 翻译跳过：{s['translate_error']}"})
                emit({"type": "log", "text": "歌词已写入音频标签，并删除同名 .lrc"
                      if s.get("lyrics_embedded") else "未找到歌词，跳过嵌入"})
                emit({"type": "log", "text": f"→ {s.get('save_path')}"})

            emit({"type": "progress", "pct": 100, "text": "完成"})
            emit({"type": "finished", "saved": saved, "count": len(saved)})
        finally:
            if log_fp:
                try:
                    log_fp.close()
                except Exception:  # noqa: BLE001
                    pass

    def log_message(self, fmt, *args):
        sys.stderr.write("[web] %s - %s\n" % (self.address_string(), fmt % args))


def _warmup():
    """后台预热：来源探测、夸克来源统计与首个客户端构造，避免首个请求干等。"""
    try:
        discover_unavailable()
    except Exception:  # noqa: BLE001
        pass
    try:
        _quark_scope()          # 约 230ms 的一次性扫描，提前算掉
    except Exception:  # noqa: BLE001
        pass
    try:
        srcs = available_sources()[:3]
        if srcs:
            get_client(srcs)
    except Exception:  # noqa: BLE001
        pass


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[MusicDL Web] listening on http://{HOST}:{PORT}")
    print(f"[MusicDL Web] musicdl available: {MUSICDL_AVAILABLE}" +
          ("" if MUSICDL_AVAILABLE else f"  ({MUSICDL_IMPORT_ERROR})"))
    print(f"[MusicDL Web] sources: {len(SOURCES)}  output: {OUTPUT_DIR}")
    threading.Thread(target=_warmup, daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
