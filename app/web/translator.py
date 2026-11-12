"""AI 翻译：走 OpenAI 兼容的 /chat/completions 接口。

兼容 DeepSeek / OpenAI / Ollama / 各类中转站 —— 只要支持
`POST {base_url}/chat/completions` 且用 Bearer 鉴权即可。

主要用途是**歌词翻译**：LRC 带时间戳，翻译时必须原样保留时间戳，
否则时间轴就废了。所以采用「整段交给模型，要求逐行保持时间戳」的策略，
并按行数分块，避免超出上下文。
"""
import json
import os
import re
import urllib.error
import urllib.request

CONFIG_FILE_NAME = "ai-config.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "base_url": "https://api.deepseek.com",
    "api_key": "",
    "model": "deepseek-flash",
    "target_lang": "中文",
    "timeout": 90,
    "translate_lyrics": True,
    "embed_bilingual": True,     # True: 原文+译文都写进标签；False: 只写译文
}

# 可选目标语言（前端下拉用）
TARGET_LANGS = [
    "中文", "English", "日本語", "한국어", "Français", "Deutsch",
    "Español", "Русский", "Português", "Italiano", "繁體中文",
]

# 只认真正的时间戳 [mm:ss.xx] 和元数据标签 [ti:..] / [ar:..] 等。
# 不能用宽松的 \[\][^\]]*\] —— 那样译文里任何以 [ 开头的内容都会被当成时间戳吞掉。
_LRC_TIME = re.compile(
    r"^\s*((?:"
    r"\[(?:ti|ar|al|by|offset|re|ve|length|lang|au|la|tool):[^\]]*\]"
    r"|\[\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?\]"
    r")+)"
)

# 中日韩字符：用来判断「这句是不是已经在说目标语言」。
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u3000-\u303f\uff00-\uffef]")
# 带到任一种字母（含重音、假名、谚文等）的行才算「有外语内容」
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)

# 目标语言属于「中日韩」时，只要这句里已经有中日韩字，就不翻。
# 例：GEM 的 “where did you go 我还在原地” 这种中英夹杂 —— 不翻；
#     整句都是外语（“Where did you go”）—— 才翻。
_CJK_TARGETS = ("中文", "简体", "繁體", "繁体", "日本", "한국", "朝鲜", "粤语", "粤語")


def _is_cjk_target(target):
    t = str(target or "")
    return any(k in t for k in _CJK_TARGETS)


# 元数据行（[ti:] / [ar:] / [offset:] 等）：不是歌词，不翻译也不参与双语配对
_LRC_META = re.compile(r"^\s*\[(?:ti|ar|al|by|offset|re|ve|length|lang|au|la|tool):", re.IGNORECASE)


def _is_meta_line(line):
    return bool(_LRC_META.match(str(line or "")))


def needs_translation(text, target):
    """这一行要不要送翻译模型。

    - 目标语言是中日韩：句子里已经有中日韩字 → 不翻（中英夹杂的歌词保持原样）；
      纯外语 → 翻。
    - 目标语言是其他语种：没有字母的行（纯符号/编号）→ 不翻；其余都翻。
    """
    s = str(text or "").strip()
    if not s:
        return False
    if _is_meta_line(s):
        return False
    # 「纯音乐」之类的标记不翻
    if s.startswith(("[", "（", "(")) and s.endswith(("]", "）", ")")):
        return False
    if _is_cjk_target(target):
        return not _CJK.search(s)
    return bool(_LETTER.search(s))


# ---------------------------------------------------------------------------
# 配置读写
# ---------------------------------------------------------------------------
def load_config(cache_dir):
    path = os.path.join(cache_dir, CONFIG_FILE_NAME)
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        if isinstance(obj, dict):
            for k in DEFAULT_CONFIG:
                if k in obj:
                    cfg[k] = obj[k]
    except Exception:  # noqa: BLE001
        pass
    return cfg


def save_config(cache_dir, obj):
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(obj, dict):
        for k in DEFAULT_CONFIG:
            if k in obj:
                cfg[k] = obj[k]
    cfg["enabled"] = bool(cfg["enabled"])
    cfg["translate_lyrics"] = bool(cfg.get("translate_lyrics", True))
    cfg["embed_bilingual"] = bool(cfg.get("embed_bilingual", True))
    for k in ("base_url", "api_key", "model", "target_lang"):
        cfg[k] = str(cfg.get(k) or "").strip()
    try:
        cfg["timeout"] = max(10, min(300, int(cfg.get("timeout") or 90)))
    except Exception:  # noqa: BLE001
        cfg["timeout"] = 90
    if not cfg["base_url"]:
        cfg["base_url"] = DEFAULT_CONFIG["base_url"]
    if not cfg["model"]:
        cfg["model"] = DEFAULT_CONFIG["model"]
    if not cfg["target_lang"]:
        cfg["target_lang"] = "中文"

    os.makedirs(cache_dir, exist_ok=True)
    with open(os.path.join(cache_dir, CONFIG_FILE_NAME), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    return cfg


def is_ready(cfg):
    return bool(cfg.get("enabled") and cfg.get("api_key") and cfg.get("base_url"))


# ---------------------------------------------------------------------------
# 底层请求
# ---------------------------------------------------------------------------
def _chat(cfg, messages, timeout=None):
    base = (cfg.get("base_url") or "").rstrip("/")
    if base.endswith("/chat/completions"):
        url = base
    else:
        url = base + "/chat/completions"
    payload = {
        "model": cfg.get("model") or "deepseek-flash",
        "messages": messages,
        "temperature": 0.3,
        "stream": False,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + str(cfg.get("api_key") or ""),
        "User-Agent": "MusicDL-Web/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout or cfg.get("timeout") or 90) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            pass
        raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc

    try:
        obj = json.loads(raw.decode("utf-8", "replace"))
        return obj["choices"][0]["message"]["content"] or ""
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"响应格式不符合 OpenAI 兼容规范: {raw[:200]!r}") from exc


# ---------------------------------------------------------------------------
# 歌词翻译
# ---------------------------------------------------------------------------
def _split_lyrics(lyrics):
    """拆成 (时间戳, 文本) 列表；纯文本行时间戳为空，元数据行时间戳为空且文本原样。"""
    rows = []
    for line in str(lyrics or "").splitlines():
        if _is_meta_line(line):
            # 元数据既不是时间戳也不是歌词：整行塞进文本，拼回时原样输出
            rows.append(("", line.strip()))
            continue
        m = _LRC_TIME.match(line)
        if m:
            rows.append((m.group(0).strip(), line[m.end():].strip()))
        else:
            rows.append(("", line.strip()))
    return rows


def _chunked(rows, max_lines=60, max_chars=2600):
    """按行数和字符数切块。"""
    buf, size = [], 0
    for row in rows:
        ln = len(row[0]) + len(row[1]) + 1
        if buf and (len(buf) >= max_lines or size + ln > max_chars):
            yield buf
            buf, size = [], 0
        buf.append(row)
        size += ln
    if buf:
        yield buf


def _translate_chunk(cfg, chunk):
    """翻译一块歌词，返回与 chunk 等长的文本列表。"""
    target = cfg.get("target_lang") or "中文"
    numbered = [f"{i + 1}. {text}" for i, (_, text) in enumerate(chunk)]
    # 纯音乐标记等也要原样保留
    prompt = (
        f"把下面的歌词逐行翻译成{target}。\n"
        "要求：\n"
        "1. 每行以原有编号开头，编号必须与输入一一对应，不要合并或拆分行；\n"
        f"2. 只是翻译，不要保留原文；不要在中途解释或加注；\n"
        "3. 只输出译文，不要任何解释、不要加引号或额外标点；\n"
        "4. 空行返回空内容。\n\n" + "\n".join(numbered)
    )
    out = _chat(cfg, [
        {"role": "system", "content": f"你是专业的音乐歌词翻译，把歌词准确、自然地译成{target}。"},
        {"role": "user", "content": prompt},
    ])
    # 解析回编号行
    got = {}
    for line in str(out or "").splitlines():
        m = re.match(r"^\s*(\d+)\s*[.、)]\s*(.*)$", line)
        if m:
            got[int(m.group(1))] = m.group(2).strip()
    result = []
    for i, (_, text) in enumerate(chunk):
        if not text:
            result.append("")
            continue
        result.append(got.get(i + 1) or "")
    return result


def has_translatable_lines(lyrics, cfg):
    """歌词里有没有真正需要翻译的行（目标语言是中文时，纯中文/中英夹杂都不算）。"""
    target = cfg.get("target_lang") or "中文"
    return any(needs_translation(text, target) for _, text in _split_lyrics(lyrics))


def translate_lyrics(lyrics, cfg, progress=None):
    """把 LRC/纯文本歌词翻译成目标语言，保留时间戳。

    只把「真的需要翻」的行送给模型：目标语言是中文时，
    中英夹杂的句子（比如 “where did you go 我还在原地”）原样保留，
    整句外语的才翻。返回 (译文, 错误信息)。失败时译文为 None。
    """
    if not is_ready(cfg):
        return None, "AI 翻译未启用或未配置 api_key"
    rows = _split_lyrics(lyrics)
    if not rows:
        return None, "歌词为空"
    target = cfg.get("target_lang") or "中文"

    translated = [""] * len(rows)
    # 需要翻译的下标 -> 送去翻；跳过的行译文留空，后面拼回时用原文
    todo = [i for i, (_, text) in enumerate(rows) if needs_translation(text, target)]
    if not todo:
        return None, "没有需要翻译的行（都是目标语言或纯符号）"

    chunks = list(_chunked([(rows[i][0], rows[i][1]) for i in todo]))
    offset = 0
    try:
        for idx, chunk in enumerate(chunks):
            texts = _translate_chunk(cfg, chunk)
            for j, t in enumerate(texts):
                translated[todo[offset + j]] = t
            offset += len(chunk)
            if progress:
                progress(f"歌词翻译 {idx + 1}/{len(chunks)} 块")
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"

    # 拼回 LRC：跳过的行原样保留
    lines = []
    for (ts, orig), tr in zip(rows, translated):
        text = tr or orig
        lines.append(f"{ts}{text}" if ts else text)
    return "\n".join(lines), None


def make_bilingual(original, translated):
    """原文与译文拼成双语歌词：译文排在原文下面一行，用「」包起来。

    形如：
        [00:12.30]Where did you go
        [00:12.30]「你去了哪里」
    没翻的行（译文与原文相同或为空）不重复输出。
    """
    o_rows = _split_lyrics(original)
    t_rows = _split_lyrics(translated)
    n = max(len(o_rows), len(t_rows))
    lines = []
    for i in range(n):
        o = o_rows[i] if i < len(o_rows) else ("", "")
        t = t_rows[i] if i < len(t_rows) else ("", "")
        ts = o[0] or t[0]
        if o[1]:
            lines.append(f"{ts}{o[1]}" if ts else o[1])
        tr = t[1].strip()
        if tr and tr != o[1].strip():
            tr = f"「{tr}」"
            lines.append(f"{ts}{tr}" if ts else tr)
    return "\n".join(lines)


def test_config(cfg):
    """连通性测试：发一句最短的请求。"""
    try:
        out = _chat(cfg, [{"role": "user", "content": "回复两个字：可用"}], timeout=30)
        return True, (out or "").strip()[:60] or "(空响应)"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"
