#!/usr/bin/env python3
"""把改动过的 web 文件打成一个新的 docker 镜像 tar（不需要 Docker）。

用途：手上只有一份 `docker save` 出来的镜像 tar，又不想装 Docker 时，
可以直接产出一个可 `docker load` 的新镜像。做法是把改动文件做成一个增量层，
追加到原镜像的层列表后面，并同步更新 config / manifest / repositories。

用法：
    python scripts/build-image.py \
        --base musicdl-web-local.tar \
        --output musicdl-web-1.0.tar \
        --tag musicdl-web:1.0 \
        --source app/web \
        --target-dir app/web

    docker load -i musicdl-web-1.0.tar

校验：
    python scripts/verify-image.py musicdl-web-1.0.tar
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import sys
import tarfile


def build_layer(files, mtime):
    """按 (归档内路径, 本地路径) 列表构造一个未压缩层 tar。"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as lt:
        for arcname, local in files:
            data = open(local, "rb").read()
            ti = tarfile.TarInfo(arcname)
            ti.size = len(data)
            ti.mode = 0o644
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = "root"
            ti.mtime = mtime
            lt.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def collect(source, target_dir):
    """收集 source 目录下所有文件，映射到容器里的 target_dir。"""
    files = []
    for root, dirs, names in os.walk(source):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".cache", "downloads")]
        for name in sorted(names):
            if name.endswith((".pyc", ".pyo")):
                continue
            local = os.path.join(root, name)
            rel = os.path.relpath(local, source).replace(os.sep, "/")
            files.append((target_dir.rstrip("/") + "/" + rel, local))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="原始镜像 tar（docker save 产物）")
    ap.add_argument("--output", required=True, help="输出镜像 tar")
    ap.add_argument("--tag", required=True, help="新 tag，如 musicdl-web:1.0")
    ap.add_argument("--source", required=True, help="本地要打进镜像的目录")
    ap.add_argument("--target-dir", default="app/web", help="在容器里的目标目录")
    args = ap.parse_args()

    files = collect(args.source, args.target_dir)
    if not files:
        sys.exit("没有可打包的文件：" + args.source)

    src = tarfile.open(args.base)
    manifest = json.loads(src.extractfile("manifest.json").read().decode("utf-8"))[0]
    cfg = json.loads(src.extractfile(manifest["Config"]).read().decode("utf-8"))

    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    layer_bytes = build_layer(files, int(now.timestamp()))
    diffid = "sha256:" + hashlib.sha256(layer_bytes).hexdigest()
    layer_id = hashlib.sha256(diffid.encode()).hexdigest()

    cfg["created"] = now_iso
    cfg["rootfs"]["diff_ids"].append(diffid)
    cfg.setdefault("history", []).append({
        "created": now_iso,
        "created_by": "COPY %s /%s # buildkit" % (args.source.rstrip("/"), args.target_dir),
        "comment": "buildkit.dockerfile.v0",
    })
    cfg_bytes = json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    cfg_name = hashlib.sha256(cfg_bytes).hexdigest() + ".json"

    layers = list(manifest["Layers"]) + [layer_id + "/layer.tar"]
    repo, _, tag = args.tag.partition(":")
    new_manifest = [{"Config": cfg_name, "RepoTags": [args.tag], "Layers": layers}]
    repositories = {repo: {tag or "latest": layer_id}}

    skip = {"manifest.json", "repositories", manifest["Config"]}
    with tarfile.open(args.output, "w", format=tarfile.PAX_FORMAT) as out:

        def add(name, data):
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mode = 0o644
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = "root"
            ti.mtime = int(now.timestamp())
            out.addfile(ti, io.BytesIO(data))

        add(cfg_name, cfg_bytes)
        for m in src:
            if m.name in skip:
                continue
            out.addfile(m, src.extractfile(m))

        add(layer_id + "/VERSION", b"1.0")
        tmpl = json.loads(src.extractfile(manifest["Layers"][-1].split("/")[0] + "/json").read().decode("utf-8"))
        tmpl.update({"id": layer_id, "parent": manifest["Layers"][-1].split("/")[0], "created": now_iso})
        tmpl.setdefault("container_config", {})["Cmd"] = [
            "/bin/sh", "-c", "#(nop) COPY %s /%s" % (args.source, args.target_dir)]
        add(layer_id + "/json", json.dumps(tmpl, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        add(layer_id + "/layer.tar", layer_bytes)

        add("manifest.json", json.dumps(new_manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        add("repositories", json.dumps(repositories, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    src.close()
    print("输出 :", args.output)
    print("大小 : %.1f MB" % (os.path.getsize(args.output) / 1024 / 1024))
    print("tag  :", args.tag)
    print("层数 : %d（原 %d + 增量 1）" % (len(layers), len(manifest["Layers"])))
    print("diffid:", diffid)


if __name__ == "__main__":
    main()
