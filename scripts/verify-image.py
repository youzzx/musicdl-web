#!/usr/bin/env python3
"""校验 docker save 产物是否自洽：层 sha256 与 diff_ids 一一对应、manifest/config 可解析。

用法：
    python scripts/verify-image.py musicdl-web-1.0.tar
"""
import hashlib
import json
import sys
import tarfile


def sha256_of(tf, name):
    h = hashlib.sha256()
    fh = tf.extractfile(name)
    for chunk in iter(lambda: fh.read(1 << 20), b""):
        h.update(chunk)
    return h.hexdigest()


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: python verify-image.py <image.tar>")
    path = sys.argv[1]
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  OK   " if cond else "  FAIL ") + msg)
        ok = ok and bool(cond)

    with tarfile.open(path) as tf:
        names = set(tf.getnames())
        check("manifest.json" in names, "manifest.json 存在")
        check("repositories" in names, "repositories 存在")
        man = json.loads(tf.extractfile("manifest.json").read().decode("utf-8"))[0]
        check(bool(man.get("RepoTags")), "RepoTags = %s" % man.get("RepoTags"))
        cfg_name = man["Config"]
        check(cfg_name in names, "config 存在: " + cfg_name)
        cfg = json.loads(tf.extractfile(cfg_name).read().decode("utf-8"))
        layers = man["Layers"]
        diff_ids = cfg["rootfs"]["diff_ids"]
        check(len(layers) == len(diff_ids), "层数 = %d，diff_ids = %d" % (len(layers), len(diff_ids)))
        for i, (lpath, did) in enumerate(zip(layers, diff_ids)):
            check(sha256_of(tf, lpath) == did.split(":", 1)[1], "第 %d 层 sha256 匹配" % i)
        c = cfg.get("config", {})
        check(bool(c.get("Cmd")), "Cmd = %s" % c.get("Cmd"))
        check(cfg.get("os") == "linux", "os = %s" % cfg.get("os"))
        check(cfg.get("architecture") == "amd64", "arch = %s" % cfg.get("architecture"))

    print("\n结果:", "通过" if ok else "失败")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
