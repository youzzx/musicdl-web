"""歌词翻译规则离线自检：任意非中文语种 → 中文，译文格式沿用现状。

用法（仓库根目录）：
    python scripts/check_translate_rules.py

纯本地断言，走 needs_translation / has_translatable_lines / make_bilingual /
translate_lyrics（模型调用打桩），全程不联网。
"""
import os
import sys
import unittest.mock as mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "web")))
import translator  # noqa: E402

T = "中文"
checks = 0


def expect(line, target, want, label):
    global checks
    got = translator.needs_translation(line, target)
    assert got == want, f"{label}: needs_translation({line!r}, {target!r}) = {got}, 期望 {want}"
    checks += 1


def ok(cond, label):
    global checks
    assert cond, label
    checks += 1


# 1) 任意非中文语种整句：全部进入翻译队列
for line, label in [
    ("Where did you go", "英文"),
    ("Comment ça va", "法文·重音字母"),
    ("Guten Morgen", "德文"),
    ("Buenos días", "西文"),
    ("Buongiorno", "意文"),
    ("君の名は", "日文·汉字加假名混排"),
    ("さくら さくら", "日文·纯假名"),
    ("ｻｸﾗ", "日文·半角片假名"),
    ("사랑해요", "韩文"),
    ("Привет мир", "俄文·西里尔"),
    ("Γεια σου", "希腊文"),
    ("مرحبا", "阿拉伯文"),
    ("สวัสดี", "泰文"),
    ("नमस्ते", "天城文"),
]:
    expect(line, T, True, label)

# 2) 已经含中文、且只混拉丁字母：按既有约定保留原文
for line, label in [
    ("我还在原地", "纯中文"),
    ("where did you go 我还在原地", "中英夹杂"),
    ("Hello 世界 123", "中英夹杂带数字"),
    ("夜曲，周杰伦", "中文带全角标点"),
]:
    expect(line, T, False, label)

# 2b) 混着假名 / 西里尔等非中文文字：即便含中文也送模型
for line, label in [
    ("君の名は 我还在原地", "日中夹杂"),
    ("Привет 你好", "俄中夹杂"),
]:
    expect(line, T, True, label)

# 3) 元数据 / 标记 / 纯符号 / 编号：原文直出
for line, label in [
    ("[ti:夜曲]", "ti 元数据"),
    ("[ar:周杰伦]", "ar 元数据"),
    ("[offset:0]", "offset 元数据"),
    ("[00:12.30]", "时间戳空行"),
    ("（纯音乐）", "全角纯音乐标记"),
    ("(Instrumental)", "半角纯音乐标记"),
    ("---", "纯符号"),
    ("123", "纯编号"),
    ("", "空行"),
]:
    expect(line, T, False, label)

# 4) 目标语言切到日文：沿用旧判定（含假名即保留）
expect("さくら さくら", "日本語", False, "日文目标·日文行")
expect("Where did you go", "日本語", True, "日文目标·英文行")

# 5) 目标语言为其他语种：纯符号保留，其余送模型
expect("---", "English", False, "英文目标·纯符号")
expect("我还在原地", "English", True, "英文目标·中文行")

# 6) 双语排版格式沿用现状
original = "\n".join([
    "[ti:夜曲]",
    "[00:12.30]Where did you go",
    "[00:15.00]我还在原地",
    "[00:18.00]（纯音乐）",
])
translated = "\n".join([
    "[ti:夜曲]",
    "[00:12.30]你去了哪里",
    "[00:15.00]我还在原地",
    "[00:18.00]（纯音乐）",
])
lines = translator.make_bilingual(original, translated).splitlines()
ok(lines[0] == "[ti:夜曲]", "元数据行原文直出")
ok(lines[1] == "[00:12.30]Where did you go", "原文行完整保留")
ok(lines[2] == "[00:12.30]「你去了哪里」", "译文用「」包住、沿用同一时间戳")
ok(lines.index("[00:12.30]「你去了哪里」") == lines.index("[00:12.30]Where did you go") + 1,
   "译文排在原文下一行")
ok(lines.count("[00:15.00]我还在原地") == 1, "跳过翻译的行未重复输出")
ok(lines.count("[ti:夜曲]") == 1, "元数据行未重复输出")
ok(len(lines) == 5, "总行数符合原文加一行译文")
ok("「「" not in "\n".join(lines), "译文未被重复包裹")

# 7) 整首判定入口
cfg = {"target_lang": T}
ok(translator.has_translatable_lines(original, cfg) is True, "含英文行时判定为可翻")
ok(translator.has_translatable_lines("[00:01.00]我还在原地\n[ti:x]", cfg) is False,
   "纯中文加元数据时保留原文")
ok(translator.has_translatable_lines("[00:01.00]さくら さくら", cfg) is True,
   "纯日文整首也判定为可翻")

# 8) 翻译队列：英 / 日 / 韩三行都送模型，中文行与中英夹杂行保留
lyrics = "\n".join([
    "[00:01.00]Where did you go",
    "[00:02.00]さくら さくら",
    "[00:03.00]사랑해요",
    "[00:04.00]我还在原地",
    "[00:05.00]where did you go 我还在原地",
])
full_cfg = {
    "enabled": True, "api_key": "stub", "base_url": "http://127.0.0.1:1",
    "target_lang": T, "timeout": 90, "translate_lyrics": True, "embed_bilingual": True,
    "model": "stub",
}
sent = []


def fake_chunk(_cfg, chunk):
    sent.extend(t for _, t in chunk)
    return ["译文" for _ in chunk]


with mock.patch.object(translator, "_translate_chunk", fake_chunk):
    out, err = translator.translate_lyrics(lyrics, full_cfg)
ok(err is None, "打桩翻译调用成功")
ok(sent == ["Where did you go", "さくら さくら", "사랑해요"], "英日韩三行均进入模型队列")
ok("[00:04.00]我还在原地" in out, "纯中文行保留原文")
ok("[00:05.00]where did you go 我还在原地" in out, "中英夹杂行保留原文")

print(f"OK: {checks} 个断言全部通过")
