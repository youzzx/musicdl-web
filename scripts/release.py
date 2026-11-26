#!/usr/bin/env python3
"""一次发布：升版本 → 提交 → 推送 → 打 tag → 构建镜像 → 校验。

版本规则（用户定的）：
    1.1 → 1.2 → … → 1.9 → 2.0 → 2.1 → …
也就是次版本号 +1，到 10 就进位到主版本号。

用法：
    python scripts/release.py --message "feat: xxx"            # 完整流程
    python scripts/release.py --message "feat: xxx" --dry-run  # 只算版本+看要改什么
    python scripts/release.py --message "feat: xxx" --no-build # 不构建镜像
    python scripts/release.py --message "feat: xxx" --no-push  # 只本地提交+构建

Token：从环境变量 GITHUB_TOKEN 读（也可 --token 传入）。只用一次，不落盘。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = ROOT
VERSION_FILE = os.path.join(REPO_DIR, "VERSION")
GIT = None  # 运行时探测


# --------------------------------------------------------------------------
# 版本号
# --------------------------------------------------------------------------
def read_version():
    with open(VERSION_FILE, "r", encoding="utf-8") as fh:
        return fh.read().strip()


def next_version(cur):
    """1.1 → 1.2；1.9 → 2.0；2.0 → 2.1"""
    m = re.fullmatch(r"(\d+)\.(\d+)", cur)
    if not m:
        raise SystemExit("VERSION 文件格式不对：%r（应为 X.Y）" % cur)
    major, minor = int(m.group(1)), int(m.group(2))
    minor += 1
    if minor > 9:
        return "%d.0" % (major + 1)
    return "%d.%d" % (major, minor)


# --------------------------------------------------------------------------
# 把版本号写进各处
# --------------------------------------------------------------------------
def replace_in_file(path, pattern, repl, dry):
    if not os.path.isfile(path):
        return False
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    new = re.sub(pattern, repl, src)
    if new == src:
        return False
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
    print("  更新 %s" % os.path.relpath(path, ROOT))
    return True


def bump_files(old, new, dry):
    print("版本 %s → %s" % (old, new))
    # 统一替换镜像串：musicdl-web:旧 → musicdl-web:新
    pat = re.escape("musicdl-web:%s" % old)
    for name in ("Dockerfile", "docker-compose.yml", "README.md"):
        replace_in_file(os.path.join(ROOT, name), pat, "musicdl-web:%s" % new, dry)
    # README 里可能还有裸的 ":1.0" 之类，交给上面的统一规则
    if not dry:
        with open(VERSION_FILE, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new + "\n")
    print("  更新 VERSION")


# --------------------------------------------------------------------------
# git
# --------------------------------------------------------------------------
def find_git():
    global GIT
    cands = [
        os.path.join(os.path.dirname(ROOT), ".tools", "git", "cmd", "git.exe"),
        shutil.which("git"),
    ]
    for c in cands:
        if c and os.path.isfile(c):
            GIT = c
            return c
    raise SystemExit("找不到 git（试过 .tools/git 和 PATH）")


def run(cmd, check=True, capture=True):
    r = subprocess.run(cmd, cwd=REPO_DIR, capture_output=capture, text=True,
                       encoding="utf-8", errors="replace")
    if capture and r.stdout:
        print(r.stdout.rstrip())
    if capture and r.stderr and r.returncode != 0:
        print(r.stderr.rstrip(), file=sys.stderr)
    if check and r.returncode != 0:
        raise SystemExit("命令失败（%d）：%s" % (r.returncode, " ".join(cmd)))
    return r


def git(*args, check=True):
    return run([GIT] + list(args), check=check)


def has_changes():
    r = run([GIT, "status", "--porcelain"], check=True)
    return bool(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--message", "-m", required=True, help="提交信息（多行用 \\n）")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--base-image", default=None,
                    help="构建用的基础镜像 tar（默认 ../musicdl-web(local).syno.tar）")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="没有改动也照常升版本发布")
    ap.add_argument("--tag-name", default=None,
                    help="标签名（默认 v<版本>；beta 阶段可传 beta1 / beta2）")
    args = ap.parse_args()

    old = read_version()
    new = next_version(old)

    print("=" * 60)
    print("发布：%s → %s" % (old, new))
    print("=" * 60)

    if args.dry_run:
        bump_files(old, new, dry=True)
        print("\n[dry-run] 不写文件、不提交、不构建")
        return 0

    # 1) 改版本号
    bump_files(old, new, dry=False)

    # 2) 提交
    find_git()
    if not has_changes() and not args.force:
        raise SystemExit("没有待提交的改动（要强制发版加 --force）")
    git("add", "-A")
    git("commit", "-m", args.message.replace("\\n", "\n"))
    msg = args.message.replace("\\n", "\n").splitlines()[0]
    print("已提交：%s" % msg)

    # 3) 推送
    tag = args.tag_name or ("v%s" % new)
    if args.no_push:
        # beta 阶段：只留本地提交与本地 tag，GitHub 保持不动
        run([GIT, "tag", "-d", tag], check=False)
        git("tag", "-a", tag, "-m", "MusicDL Web %s" % tag)
        print("跳过推送（--no-push），已创建本地 tag %s" % tag)
    else:
        if not args.token:
            raise SystemExit("缺少 GITHUB_TOKEN（或 --token），推不了")
        url = "https://x-access-token:%s@github.com/youzzx/musicdl-web.git" % args.token
        out = run([GIT, "push", url, args.branch], check=False)
        if out.returncode != 0:
            raise SystemExit("推送失败（网络？）——本地提交已保留，稍后重试即可")
        # 4) 打 tag 并推送
        run([GIT, "tag", "-d", tag], check=False)
        git("tag", "-a", tag, "-m", "MusicDL Web %s" % tag)
        out = run([GIT, "push", url, "refs/tags/%s" % tag], check=False)
        if out.returncode != 0:
            print("! tag 推送失败，代码已推上去")
        else:
            print("已推送 tag %s" % tag)
        try:
            git("remote", "set-url", args.remote,
                "https://github.com/youzzx/musicdl-web.git")
        except SystemExit:
            pass

    # 5) 构建镜像
    if args.no_build:
        print("跳过构建（--no-build）")
        return 0

    base = args.base_image or os.path.join(os.path.dirname(ROOT),
                                           "musicdl-web(local).syno.tar")
    if not os.path.isfile(base):
        raise SystemExit("基础镜像不存在：%s（用 --base-image 指定）" % base)
    out_tar = os.path.join(os.path.dirname(ROOT), "musicdl-web-%s.tar" % new)
    print("\n构建镜像 %s ..." % out_tar)
    run([sys.executable, os.path.join(ROOT, "scripts", "build-image.py"),
         "--base", base, "--output", out_tar,
         "--tag", "musicdl-web:%s" % new,
         "--source", os.path.join(ROOT, "app", "web"), "--target-dir", "app/web"])

    print("\n校验镜像 ...")
    run([sys.executable, os.path.join(ROOT, "scripts", "verify-image.py"), out_tar])

    print("\n完成：%s → %s，镜像 %s" % (old, new, out_tar))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
