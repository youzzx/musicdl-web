"""同源刮削：优先用「下载来源自身」的元数据补全标签。

思路
----
musicdl 的 SongInfo 已经带着下载来源提供的 song_name / singers / album / cover_url /
lyric —— 这本身就是「同源」。但不同来源填的完整度不一样，且 SongInfo 没有年份字段。

所以这里做三件事：
  1. 以下载来源的 SongInfo 为**基底**（不覆盖已有内容）
  2. 若基底缺字段，用**同一个来源的客户端**再搜一次「标题 歌手」取最佳匹配来补
     —— 明确不去跨源取，避免出现「QQ 下的歌挂网易云封面」这种串味
  3. 从 raw_data（原始 API 响应）里尽力挖年份 —— 各来源字段名不同，统一按常见写法递归找
"""
import difflib
import re
import urllib.request

# raw_data 里可能承载年份的键名（统一小写去分隔符后比较）
_YEAR_KEYS = (
    "publishtime", "publishdate", "publishyear", "releasedate", "releasetime",
    "releaseyear", "releasedtime", "year", "createtime", "albumdate",
    "issuedate", "issueyear", "regdate", "timepublic", "pubtime",
    "relasedate", "releaseyear",
)

# 明确不当作年份的键（避免把时长、大小、码率误判成年份）
def _norm_key(k):
    return re.sub(r"[^a-z]", "", str(k).lower())


def _plausible_year(v):
    """把各种形态的值规范成 4 位年份字符串；不可信则返回 None。"""
    import datetime
    now = datetime.date.today().year
    n = None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        n = int(v)
        # 13 位是毫秒时间戳，10 位是秒
        if n > 10 ** 11:
            n = n // 1000
        if n > 10 ** 8:
            try:
                y = datetime.datetime.fromtimestamp(n).year
            except Exception:  # noqa: BLE001
                return None
            # 时间戳同样要过合理性校验，否则 9999999999999 会算出 2286 年
            return str(y) if 1900 <= y <= now + 1 else None
        return str(n) if 1900 <= n <= now + 1 else None
    if isinstance(v, str):
        s = v.strip()
        m = re.match(r"^(\d{4})[-/.]?(\d{2})?[-/.]?(\d{2})?", s)
        if m:
            y = int(m.group(1))
            return str(y) if 1900 <= y <= now + 1 else None
        if s.isdigit() and len(s) in (10, 13):
            return _plausible_year(int(s))
    return None


def find_year(obj, depth=0, _seen=None):
    """在嵌套 dict/list 里递归找年份。命中第一个可信值就返回。"""
    if depth > 6 or obj is None:
        return None
    if _seen is None:
        _seen = set()
    if isinstance(obj, dict):
        # 先看键名直接命中的
        for k, v in obj.items():
            if _norm_key(k) in _YEAR_KEYS:
                y = _plausible_year(v)
                if y:
                    return y
        for v in obj.values():
            if id(v) in _seen:
                continue
            _seen.add(id(v))
            y = find_year(v, depth + 1, _seen)
            if y:
                return y
    elif isinstance(obj, list):
        for v in obj[:40]:
            if id(v) in _seen:
                continue
            _seen.add(id(v))
            y = find_year(v, depth + 1, _seen)
            if y:
                return y
    return None


# ---------------------------------------------------------------------------
# 匹配
# ---------------------------------------------------------------------------
def _norm(s):
    return re.sub(r"[\s\-_·，,。.、'\"!！?？()（）\[\]【】]+", "", str(s or "")).lower()


def match_score(target_title, target_artist, cand):
    """候选与目标的匹配度（0~1）。标题权重高于歌手。"""
    t = _norm(target_title)
    c = _norm(getattr(cand, "song_name", "") or "")
    if not t or not c:
        return 0.0
    title_sim = difflib.SequenceMatcher(None, t, c).ratio()
    if t == c:
        title_sim = 1.0
    a = _norm(target_artist)
    b = _norm(getattr(cand, "singers", "") or "")
    artist_sim = 0.0
    if a and b:
        artist_sim = 1.0 if (a in b or b in a) else difflib.SequenceMatcher(None, a, b).ratio()
    return title_sim * 0.75 + artist_sim * 0.25


def pick_best(target, candidates, threshold=0.62):
    """从候选里挑与 target 最像的一条。"""
    best, best_score = None, 0.0
    for c in candidates or []:
        s = match_score(getattr(target, "song_name", None),
                        getattr(target, "singers", None), c)
        if s > best_score:
            best, best_score = c, s
    return (best, best_score) if best_score >= threshold else (None, best_score)


# ---------------------------------------------------------------------------
# 封面
# ---------------------------------------------------------------------------
def fetch_cover(url, timeout=15, max_bytes=2 * 1024 * 1024, referer=None):
    """取封面原始字节。

    用 requests 而不是 urllib：部分平台（QQ/酷狗）的图床会做防盗链，
    需要跟随重定向并带上 Referer。超过 max_bytes 或不是图片则返回 None。
    """
    if not (isinstance(url, str) and url.startswith("http")):
        return None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if referer:
        headers["Referer"] = referer
    try:
        import requests
        resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True,
                            stream=True)
        resp.raise_for_status()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        chunks, total = [], 0
        for chunk in resp.iter_content(64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                resp.close()
                return None
            chunks.append(chunk)
        resp.close()
        data = b"".join(chunks)
    except Exception:  # noqa: BLE001
        # requests 不可用时退回 urllib（无 Referer）
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as up:
                ctype = (up.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                data = up.read(max_bytes + 1)
        except Exception:  # noqa: BLE001
            return None
        if len(data) > max_bytes:
            return None

    if not data:
        return None
    # Content-Type 不可信时按文件头兜底
    if not ctype.startswith("image/"):
        if not (data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG"
                or data[:4] == b"RIFF" or data[:6] in (b"GIF87a", b"GIF89a")):
            return None
    return data


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
SOURCE_LABELS = {
    "NeteaseMusicClient": "网易云音乐",
    "QQMusicClient": "QQ音乐",
    "KugouMusicClient": "酷狗音乐",
    "KuwoMusicClient": "酷我音乐",
    "MiguMusicClient": "咪咕音乐",
    "BodianMusicClient": "波点音乐",
    "AppleMusicClient": "Apple Music",
    "TIDALMusicClient": "TIDAL",
}


def source_label(name):
    n = str(name or "")
    return SOURCE_LABELS.get(n, n.replace("MusicClient", ""))


def build_meta(song, client=None, allow_same_source_search=True,
               cover_max_bytes=2 * 1024 * 1024, progress=None):
    """为一条 SongInfo 产出待写入的标签元数据。

    progress: 可选回调 fn(text)，用于把刮削过程实时输出到下载日志。

    返回 dict：
      title/artist/album/date/genre/track/disc/comment  -> 字符串
      cover   -> 封面字节或 None
      lyrics  -> 歌词文本或 None
      scraped -> {"same_source","score","album_filled","year","searched"}
    """
    def say(msg):
        if progress:
            try:
                progress(msg)
            except Exception:  # noqa: BLE001
                pass

    src = getattr(song, "source", None)
    meta = {
        "title": (getattr(song, "song_name", None) or "").strip(),
        "artist": (getattr(song, "singers", None) or "").strip(),
        "album": (getattr(song, "album", None) or "").strip(),
        "albumartist": (getattr(song, "singers", None) or "").strip(),
        "comment": f"MusicDL · {source_label(src)}",
    }
    cover_url = getattr(song, "cover_url", None)
    lyrics = (getattr(song, "lyric", None) or "").strip() or None
    info = {"same_source": False, "score": 0.0, "album_filled": False,
            "year": None, "searched": False}

    have = []
    if meta["album"]:
        have.append("专辑")
    if cover_url:
        have.append("封面")
    if lyrics:
        have.append("歌词")
    if getattr(song, "duration_s", None):
        have.append("时长")
    say(f"自带元数据：{'、'.join(have) if have else '（无）'}")

    # --- 同源补全 -----------------------------------------------------------
    need_more = (not meta["album"]) or (not cover_url) or (not lyrics) \
        or (not getattr(song, "duration_s", None))
    if allow_same_source_search and client is not None and src and need_more and meta["title"]:
        info["searched"] = True
        say(f"同源刮削：用 {source_label(src)} 再搜「{meta['title']} {meta['artist']}」")
        keyword = f"{meta['title']} {meta['artist']}".strip()
        try:
            results = client.music_clients[src].search(
                keyword=keyword, num_threadings=3,
                request_overrides=client.requests_overrides.get(src, {}),
            ) or []
        except Exception:  # noqa: BLE001
            results = []
        say(f"同源刮削：返回 {len(results)} 条候选")
        best, score = pick_best(song, results)
        if best is not None:
            info["same_source"] = True
            info["score"] = round(score, 3)
            filled = []
            for field, attr in (("album", "album"), ("artist", "singers")):
                if not meta.get(field) and getattr(best, attr, None):
                    meta[field] = str(getattr(best, attr)).strip()
                    filled.append("专辑" if field == "album" else "歌手")
                    if field == "album":
                        info["album_filled"] = True
                    if field == "artist":
                        meta["albumartist"] = meta["artist"]
            if not cover_url and getattr(best, "cover_url", None):
                cover_url = best.cover_url
                filled.append("封面")
            if not lyrics and getattr(best, "lyric", None):
                lyrics = best.lyric.strip() or None
                filled.append("歌词")
            say(f"同源刮削命中（匹配度 {info['score']}）"
                + (f"，补全：{'、'.join(filled)}" if filled else "，无需补字段"))
            extra = getattr(best, "raw_data", None)
            if extra:
                year_from_best = find_year(extra)
                if year_from_best:
                    info["year"] = year_from_best
        else:
            say(f"同源刮削未命中（最高匹配度 {round(score, 3)}，低于阈值）")

    # --- 年份 ---------------------------------------------------------------
    if not info["year"]:
        info["year"] = find_year(getattr(song, "raw_data", None))
    if info["year"]:
        meta["date"] = info["year"]
        say(f"年份：{info['year']}")
    else:
        say("年份：未提取到")

    # --- 封面 ---------------------------------------------------------------
    cover = None
    if cover_url:
        say("封面：正在抓取…")
        cover = fetch_cover(cover_url, max_bytes=cover_max_bytes)
        say(f"封面：{'已取到 ' + str(len(cover)) + ' 字节' if cover else '抓取失败，跳过'}")
    else:
        say("封面：无地址")

    meta["cover"] = cover
    meta["lyrics"] = lyrics
    meta["scraped"] = info
    meta["source"] = source_label(src)
    return meta
