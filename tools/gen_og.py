#!/usr/bin/env python3
"""为每篇文章生成 1200x630 的 og:image 封面图。

写文件到 assets/og/<slug>.png；build.py 检测到文件存在就自动注入 og:image 标签。
绘图在 Windows 侧用 GDI+（tools/make_og.ps1），WSL 里没有 rsvg/imagemagick 也能出图。

用法：
    python3 tools/gen_og.py            # 只补缺失的
    python3 tools/gen_og.py --force    # 全部重画
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OG_DIR = os.path.join(ROOT, "assets", "og")
DOMAIN = "lvdi-profile.vercel.app"
BRAND = "吕迪"


def win_path(p):
    """/mnt/d/x → D:\\x；已在 Windows 侧的路径原样返回。"""
    m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", p)
    if m:
        return m.group(1).upper() + ":\\" + m.group(2).replace("/", "\\")
    return p


def parse_front_matter(raw):
    m = re.match(r"^---\r?\n(.*?)\r?\n---", raw, re.S)
    meta = {}
    if not m:
        return meta
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"')
    return meta


def collect(force):
    jobs = []
    posts_dir = os.path.join(ROOT, "content", "posts")
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        slug = fn[:-3]
        out = os.path.join(OG_DIR, slug + ".png")
        if os.path.exists(out) and not force:
            continue
        meta = parse_front_matter(open(os.path.join(posts_dir, fn), encoding="utf-8").read())
        tags = meta.get("tags", "[]").strip("[]")
        tags = " · ".join(t.strip().strip('"') for t in tags.split(",") if t.strip())
        jobs.append({
            "title": meta.get("title", slug),
            "kicker": meta.get("date", ""),
            "foot": meta.get("summary", "")[:34] + ("…" if len(meta.get("summary", "")) > 34 else ""),
            "tags": tags,
            "brand": BRAND,
            "domain": DOMAIN,
            "out": win_path(out),
        })
    # 首页也来一张
    home = os.path.join(OG_DIR, "home.png")
    if not os.path.exists(home) or force:
        jobs.append({
            "title": "Agentic RL · AI Infra",
            "kicker": "上海 · 写代码、折腾本地推理栈",
            "foot": "技术长文与项目笔记",
            "tags": "LVU Di · @Aression",
            "brand": BRAND,
            "domain": DOMAIN,
            "out": win_path(home),
        })
    return jobs


def ensure_bom(path):
    """Windows PowerShell 5.1 只有见到 BOM 才按 UTF-8 读 .ps1，否则中文全乱。"""
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"\xef\xbb\xbf"):
        with open(path, "wb") as f:
            f.write(b"\xef\xbb\xbf" + data)


def main():
    force = "--force" in sys.argv
    os.makedirs(OG_DIR, exist_ok=True)
    jobs = collect(force)
    if not jobs:
        print("封面图都已存在，跳过（要重画加 --force）")
        return
    ps = os.path.join(ROOT, "tools", "make_og.ps1")
    ensure_bom(ps)
    # 一张图一次进程：GDI+ 在同一进程里连续 Save 多张时会静默丢图，分开跑最稳。
    for j in jobs:
        job_file = os.path.join(OG_DIR, "_job.json")
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump([j], f, ensure_ascii=False, indent=1)
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", win_path(ps), "-Jobs", win_path(job_file)],
                capture_output=True, timeout=120)
            out = (proc.stdout or b"").decode("utf-8", "replace")
            err = (proc.stderr or b"").decode("gbk", "replace")
            if proc.returncode != 0 or "ok " not in out:
                print("! 生成失败:", j.get("title"), "|", err.strip()[:300] or out.strip()[:300])
            else:
                print(f"  ✓ {j['title'][:34]}")
        finally:
            if os.path.exists(job_file):
                os.remove(job_file)

    missing = [j for j in jobs
               if not os.path.exists(os.path.join(OG_DIR, os.path.basename(j["out"].replace("\\", "/"))))]
    if missing:
        print(f"! 仍有 {len(missing)} 张没落地：", [os.path.basename(m['out']) for m in missing])
    else:
        print(f"封面图齐了：{len(jobs)} 张 → assets/og/")


if __name__ == "__main__":
    main()
