"""音乐标签写入：把元数据 / 封面 / 歌词写进音频文件。

各容器支持的标签体系完全不同，这里按扩展名分派：

  MP3            ID3v2（TIT2/TPE1/TALB/TDRC/COMM/USLT + APIC）
  FLAC           Vorbis comment + 独立 picture 块（FLAC.add_picture）
  OGG Vorbis     Vorbis comment + METADATA_BLOCK_PICTURE（base64 的 FLAC picture 块）
  Opus           同上（mutagen 的 OggOpus 没有 add_picture，必须手工编码）
  M4A/MP4/AAC    iTunes atoms（©nam/©ART/©alb/©day/©cmt/©lyr + covr）
  WAV            无原生标签，写 ID3 chunk
  AIFF           同 WAV

字段命名以参考实现的跨格式映射表为准（ID3 / Vorbis / MP4 三列的对应关系）。
"""
import base64
import os


# ---------------------------------------------------------------------------
# 图片类型探测（不依赖 Pillow，避免为了嵌封面引入几十 MB 依赖）
# ---------------------------------------------------------------------------
def _sniff_image(data):
    """从文件头判断图片类型，返回 (mime, 宽, 高)。宽高取不到时返回 0。"""
    if not data or len(data) < 12:
        return "", 0, 0
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        # PNG: IHDR 紧跟在 8 字节签名 + 4 字节长度 + 4 字节类型之后
        try:
            w = int.from_bytes(data[16:20], "big")
            h = int.from_bytes(data[20:24], "big")
        except Exception:  # noqa: BLE001
            w = h = 0
        return "image/png", w, h
    if data[:3] == b"\xff\xd8\xff":
        w, h = _jpeg_size(data)
        return "image/jpeg", w, h
    if data[:6] in (b"GIF87a", b"GIF89a"):
        try:
            w = int.from_bytes(data[6:8], "little")
            h = int.from_bytes(data[8:10], "little")
        except Exception:  # noqa: BLE001
            w = h = 0
        return "image/gif", w, h
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", 0, 0
    if data[:2] == b"BM":
        return "image/bmp", 0, 0
    return "", 0, 0


def _jpeg_size(data):
    """扫描 JPEG 的 SOF 段拿宽高。"""
    i, n = 2, len(data)
    while i < n - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        try:
            seglen = int.from_bytes(data[i + 2:i + 4], "big")
        except Exception:  # noqa: BLE001
            break
        # SOF0..SOF15（排除 DHT=C4、JPG=C8、DAC=CC）
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            try:
                h = int.from_bytes(data[i + 5:i + 7], "big")
                w = int.from_bytes(data[i + 7:i + 9], "big")
                return w, h
            except Exception:  # noqa: BLE001
                break
        i += 2 + seglen
    return 0, 0


def _deep_bits(data):
    """位深：PNG 取 IHDR 的 bit depth，JPEG 固定 24（8bit × 3 通道）。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 24:
        try:
            color_type = data[25]
            return 32 if color_type == 6 else 24
        except Exception:  # noqa: BLE001
            return 24
    return 24


# ---------------------------------------------------------------------------
# 通用入口
# ---------------------------------------------------------------------------
def write_tags(path, meta, cover=None, lyrics=None):
    """把元数据写入音频文件。

    meta   {"title","artist","album","date","track","disc","genre","comment","albumartist"}
    cover  封面原始字节（jpg/png/webp…），None 表示不处理
    lyrics 歌词文本（可含 LRC 时间戳），None 表示不处理

    返回 {"written": [字段名...], "cover": bool, "lyrics": bool, "error": str|None}
    """
    result = {"written": [], "cover": False, "lyrics": False, "error": None}
    if not path or not os.path.isfile(path):
        result["error"] = "文件不存在"
        return result

    ext = os.path.splitext(path)[1].lower()
    fields = {k: ("" if v is None else str(v).strip())
              for k, v in (meta or {}).items() if str(v or "").strip()}

    try:
        if ext == ".mp3":
            _write_id3(path, fields, cover, lyrics, result)
        elif ext == ".flac":
            _write_flac(path, fields, cover, lyrics, result)
        elif ext in (".ogg", ".oga"):
            _write_ogg(path, fields, cover, lyrics, result, opus=False)
        elif ext == ".opus":
            _write_ogg(path, fields, cover, lyrics, result, opus=True)
        elif ext in (".m4a", ".mp4", ".m4b", ".aac"):
            _write_mp4(path, fields, cover, lyrics, result)
        elif ext in (".wav", ".wave"):
            _write_id3(path, fields, cover, lyrics, result, container="wave")
        elif ext in (".aiff", ".aif"):
            _write_id3(path, fields, cover, lyrics, result, container="aiff")
        else:
            result["error"] = f"不支持的格式 {ext}"
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


# ---------------------------------------------------------------------------
# ID3（MP3 / WAV / AIFF）
# ---------------------------------------------------------------------------
_ID3_TEXT = {
    "title": "TIT2", "artist": "TPE1", "albumartist": "TPE2", "album": "TALB",
    "date": "TDRC", "genre": "TCON", "track": "TRCK", "disc": "TPOS",
}


def _write_id3(path, fields, cover, lyrics, result, container=None):
    from mutagen.id3 import (ID3, APIC, COMM, TIT2, TPE1, TPE2, TALB, TDRC,
                             TCON, TRCK, TPOS, USLT, PictureType)

    if container == "wave":
        from mutagen.wave import WAVE
        audio = WAVE(path)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
    elif container == "aiff":
        from mutagen.aiff import AIFF
        audio = AIFF(path)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags
    else:
        try:
            tags = ID3(path)
        except Exception:  # noqa: BLE001
            tags = ID3()
        audio = None

    frame_cls = {"TIT2": TIT2, "TPE1": TPE1, "TPE2": TPE2, "TALB": TALB,
                 "TDRC": TDRC, "TCON": TCON, "TRCK": TRCK, "TPOS": TPOS}
    for name, fid in _ID3_TEXT.items():
        val = fields.get(name)
        if not val:
            continue
        tags.delall(fid)
        tags.add(frame_cls[fid](encoding=3, text=[val]))
        result["written"].append(name)

    if fields.get("comment"):
        tags.delall("COMM")
        tags.add(COMM(encoding=3, lang="chi", desc="", text=[fields["comment"]]))
        result["written"].append("comment")

    if lyrics:
        tags.delall("USLT")
        tags.add(USLT(encoding=3, lang="chi", desc="", text=lyrics))
        result["lyrics"] = True

    if cover:
        mime, _, _ = _sniff_image(cover)
        if mime.startswith("image/"):
            tags.delall("APIC")
            tags.add(APIC(encoding=3, mime=mime, type=PictureType.COVER_FRONT,
                          desc="Cover", data=cover))
            result["cover"] = True

    if audio is not None:
        audio.save(v2_version=4) if container else tags.save(path, v2_version=4)
    else:
        tags.save(path, v2_version=4)


# ---------------------------------------------------------------------------
# FLAC
# ---------------------------------------------------------------------------
_VORBIS_KEYS = {
    "title": "TITLE", "artist": "ARTIST", "album": "ALBUM",
    "albumartist": "ALBUMARTIST", "date": "DATE", "genre": "GENRE",
    "track": "TRACKNUMBER", "disc": "DISCNUMBER", "comment": "COMMENT",
}


def _make_flac_picture(cover):
    import mutagen.flac as flac
    from mutagen.id3 import PictureType

    mime, w, h = _sniff_image(cover)
    if not mime.startswith("image/"):
        return None
    pic = flac.Picture()
    pic.type = int(PictureType.COVER_FRONT)
    pic.mime = mime
    pic.desc = "Cover"
    pic.width, pic.height, pic.depth = w, h, _deep_bits(cover)
    pic.data = cover
    return pic


def _write_flac(path, fields, cover, lyrics, result):
    from mutagen.flac import FLAC

    audio = FLAC(path)
    for name, key in _VORBIS_KEYS.items():
        val = fields.get(name)
        if not val:
            continue
        audio[key] = val
        result["written"].append(name)
    if lyrics:
        audio["LYRICS"] = lyrics
        result["lyrics"] = True
    if cover:
        pic = _make_flac_picture(cover)
        if pic is not None:
            audio.clear_pictures()
            audio.add_picture(pic)
            result["cover"] = True
    audio.save()


# ---------------------------------------------------------------------------
# OGG Vorbis / Opus
# ---------------------------------------------------------------------------
def _write_ogg(path, fields, cover, lyrics, result, opus):
    if opus:
        from mutagen.oggopus import OggOpus
        audio = OggOpus(path)
    else:
        from mutagen.oggvorbis import OggVorbis
        audio = OggVorbis(path)

    for name, key in _VORBIS_KEYS.items():
        val = fields.get(name)
        if not val:
            continue
        audio[key] = val
        result["written"].append(name)
    if lyrics:
        audio["LYRICS"] = lyrics
        result["lyrics"] = True

    if cover:
        # OggOpus / OggVorbis 都没有 add_picture，
        # 规范做法是把 FLAC picture 块整体 base64 后存进 METADATA_BLOCK_PICTURE
        pic = _make_flac_picture(cover)
        if pic is not None:
            audio["METADATA_BLOCK_PICTURE"] = [
                base64.b64encode(pic.write()).decode("ascii")
            ]
            result["cover"] = True
    audio.save()


# ---------------------------------------------------------------------------
# M4A / MP4
# ---------------------------------------------------------------------------
_MP4_KEYS = {
    "title": "\xa9nam", "artist": "\xa9ART", "albumartist": "aART",
    "album": "\xa9alb", "date": "\xa9day", "genre": "\xa9gen",
    "comment": "\xa9cmt",
}


def _write_mp4(path, fields, cover, lyrics, result):
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(path)
    for name, key in _MP4_KEYS.items():
        val = fields.get(name)
        if not val:
            continue
        audio[key] = [val]
        result["written"].append(name)

    # trkn / disk 是 (序号, 总数) 的整数对
    for name, key in (("track", "trkn"), ("disc", "disk")):
        val = fields.get(name)
        if not val:
            continue
        try:
            cur, _, total = val.partition("/")
            audio[key] = [(int(cur or 0), int(total or 0))]
            result["written"].append(name)
        except Exception:  # noqa: BLE001
            pass

    if lyrics:
        audio["\xa9lyr"] = [lyrics]
        result["lyrics"] = True

    if cover:
        mime, _, _ = _sniff_image(cover)
        if mime.startswith("image/"):
            fmt = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
            audio["covr"] = [MP4Cover(cover, imageformat=fmt)]
            result["cover"] = True
    audio.save()


# ---------------------------------------------------------------------------
# 读取（用于验证写入结果）
# ---------------------------------------------------------------------------
def read_tags(path):
    """读回标签，用于验证。返回 dict。"""
    ext = os.path.splitext(path)[1].lower()
    out = {"path": path, "ext": ext, "tags": {}, "cover": False, "lyrics": False,
           "bitrate": None, "samplerate": None, "channels": None, "duration": None}
    try:
        if ext == ".mp3":
            from mutagen.mp3 import MP3
            a = MP3(path)
            if a.tags:
                for fid, name in (("TIT2", "title"), ("TPE1", "artist"),
                                  ("TALB", "album"), ("TDRC", "date"),
                                  ("TCON", "genre"), ("TRCK", "track")):
                    fr = a.tags.get(fid)
                    if fr is not None:
                        out["tags"][name] = str(fr)
                out["lyrics"] = a.tags.getall("USLT") != []
                out["cover"] = a.tags.getall("APIC") != []
            out.update(bitrate=a.info.bitrate, samplerate=a.info.sample_rate,
                       channels=a.info.channels, duration=a.info.length)
        elif ext == ".flac":
            from mutagen.flac import FLAC
            a = FLAC(path)
            for k in ("TITLE", "ARTIST", "ALBUM", "ALBUMARTIST", "DATE", "GENRE",
                      "TRACKNUMBER", "COMMENT"):
                if a.get(k):
                    out["tags"][k.lower()] = a[k][0]
            out["lyrics"] = bool(a.get("LYRICS"))
            out["cover"] = bool(a.pictures)
            out.update(bitrate=a.info.bitrate, samplerate=a.info.sample_rate,
                       channels=a.info.channels, duration=a.info.length)
        elif ext in (".m4a", ".mp4", ".m4b", ".aac"):
            from mutagen.mp4 import MP4
            a = MP4(path)
            for key, name in (("\xa9nam", "title"), ("\xa9ART", "artist"),
                              ("\xa9alb", "album"), ("\xa9day", "date")):
                if a.get(key):
                    out["tags"][name] = str(a[key][0])
            out["lyrics"] = bool(a.get("\xa9lyr"))
            out["cover"] = bool(a.get("covr"))
            out.update(bitrate=a.info.bitrate, samplerate=a.info.sample_rate,
                       channels=a.info.channels, duration=a.info.length)
        elif ext in (".ogg", ".oga", ".opus"):
            from mutagen import File
            a = File(path)
            for k in ("TITLE", "ARTIST", "ALBUM", "DATE"):
                if a.get(k):
                    out["tags"][k.lower()] = a[k][0]
            out["lyrics"] = bool(a.get("LYRICS"))
            out["cover"] = bool(a.get("METADATA_BLOCK_PICTURE"))
            # OggOpusInfo 没有 sample_rate 属性（Opus 固定 48kHz），用 getattr 兜底
            out.update(samplerate=getattr(a.info, "sample_rate", 48000),
                       channels=getattr(a.info, "channels", None),
                       duration=getattr(a.info, "length", None))
        elif ext in (".wav", ".wave"):
            from mutagen.wave import WAVE
            a = WAVE(path)
            if a.tags:
                for fid, name in (("TIT2", "title"), ("TPE1", "artist"),
                                  ("TPE2", "albumartist"), ("TALB", "album"),
                                  ("TDRC", "date"), ("TCON", "genre"),
                                  ("TRCK", "track"), ("COMM", "comment")):
                    fr = a.tags.get(fid)
                    if fr is not None:
                        out["tags"][name] = str(fr)
                out["lyrics"] = a.tags.getall("USLT") != []
                out["cover"] = a.tags.getall("APIC") != []
            out.update(samplerate=a.info.sample_rate, channels=a.info.channels,
                       duration=a.info.length)
        elif ext in (".aiff", ".aif"):
            from mutagen.aiff import AIFF
            a = AIFF(path)
            if a.tags:
                for fid, name in (("TIT2", "title"), ("TPE1", "artist"),
                                  ("TPE2", "albumartist"), ("TALB", "album"),
                                  ("TDRC", "date"), ("TCON", "genre"),
                                  ("TRCK", "track"), ("COMM", "comment")):
                    fr = a.tags.get(fid)
                    if fr is not None:
                        out["tags"][name] = str(fr)
                out["lyrics"] = a.tags.getall("USLT") != []
                out["cover"] = a.tags.getall("APIC") != []
            out.update(samplerate=a.info.sample_rate, channels=a.info.channels,
                       duration=a.info.length)
        else:
            out["error"] = f"不支持的格式 {ext}"
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out
