"""bilikit 命令行入口"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

from . import broll as broll_mod
from . import frames as frames_mod
from . import render, util

# 下载能力是可选覆盖模块：公开发行版不包含 download.py。
# 缺失时 URL 输入会给出明确提示，本地文件分析不受影响。
try:
    from . import download as _dl
except ImportError:  # pragma: no cover
    _dl = None


def _step(n: int, total: int, msg: str) -> None:
    print(f"\n\033[1m[{n}/{total}] {msg}\033[0m", flush=True)


def resolve(target: str, srt_opt: str | None):
    """输入 → (视频路径, 字幕路径或None, 工作目录)"""
    if os.path.isdir(target):
        mp4 = os.path.join(target, "源片.mp4")
        if not os.path.exists(mp4):
            cand = glob.glob(os.path.join(target, "*.mp4"))
            if not cand:
                sys.exit(f"目录里没有 mp4: {target}")
            mp4 = max(cand, key=os.path.getsize)
        srt = srt_opt or os.path.join(target, "字幕.srt")
        return mp4, (srt if os.path.exists(srt) else None), target

    if os.path.isfile(target):
        stem = os.path.splitext(target)[0]
        srt = srt_opt or stem + ".srt"
        outdir = stem  # 与视频同名的目录
        os.makedirs(outdir, exist_ok=True)
        return target, (srt if os.path.exists(srt) else None), outdir

    return None, None, None


def build_parser() -> argparse.ArgumentParser:
    has_dl = _dl is not None
    desc = "视频分镜分析：抽画面 + 切 B-roll + 生成可浏览页面"
    if has_dl:
        desc = "B站视频分析：下载 + " + desc.split("：", 1)[1]
    p = argparse.ArgumentParser(prog="bilikit", description=desc)
    p.add_argument("target",
                   help="视频文件 / 素材目录" + ("/ B站 URL 或 BV号" if has_dl else ""))
    p.add_argument("--srt", help="字幕文件（默认在同目录按同名查找）")
    p.add_argument("--terms", help="自定义术语表（默认用内置 AI/科技词表）")
    p.add_argument("--threshold", type=int, default=10,
                   help="去重阈值，越小画面越密：6密 / 10默认 / 14疏")
    p.add_argument("--fps", type=float, default=2, help="密集采样帧率（默认2）")
    p.add_argument("--cols", type=int, default=4, help="图墙列数")
    p.add_argument("--rows", type=int, default=4, help="图墙行数")
    p.add_argument("--thumb-width", type=int, default=480, help="缩略图宽度 px")
    p.add_argument("--seg-max", type=float, default=45, help="B-roll 单段上限秒数")
    p.add_argument("--clip-format", default="mp4", choices=["mp4", "gif", "webp"],
                   help="片段格式；gif 体积约为 mp4 的 24 倍")
    p.add_argument("--no-broll", action="store_true", help="跳过 B-roll 切片")
    p.add_argument("--no-frames", action="store_true",
                   help="不保留单帧，只留图墙（省空间）")
    if has_dl:
        p.add_argument("--out", default=".", help="下载输出根目录（默认当前目录）")
        p.add_argument("--download-only", action="store_true", help="只下载不分析")
        p.add_argument("--redownload", action="store_true", help="强制重新下载")
        p.add_argument("-v", "--verbose", action="store_true", help="下载器完整输出")
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    target = a.target

    # ---- 可选：下载 ----
    if not os.path.exists(target):
        if _dl is None:
            sys.exit(
                f"找不到: {target}\n"
                "本版本不含下载功能，请传入本地视频文件或素材目录。\n"
                "B站视频可用 BBDown 自行下载：https://github.com/nilaoda/BBDown")
        try:
            got = _dl.acquire(target, a.out, a.redownload, a.verbose)
        except util.MissingDependency as e:
            sys.exit(f"\n✗ 缺少依赖：\n{e}")
        if not got:
            return 1
        target = got
        if a.download_only:
            print(f"\n\033[1m=== 仅下载，已完成 ===\033[0m\n{target}")
            return 0

    mp4, srt, outdir = resolve(target, a.srt)
    if mp4 is None:
        sys.exit(f"找不到: {target}")

    total = 3 if not a.no_broll else 2
    name = os.path.basename(outdir.rstrip("/"))
    print(f"\033[1m{name}\033[0m")
    print(f"  视频: {os.path.basename(mp4)} ({os.path.getsize(mp4)/1048576:.0f} MB)")
    print(f"  字幕: {'✓ ' + os.path.basename(srt) if srt else '⚠ 无（图文对照将为空）'}")

    try:
        _step(1, total, "抽画面 + 图墙")
        data = frames_mod.extract(
            mp4, outdir, srt, threshold=a.threshold, fps=a.fps,
            cols=a.cols, rows=a.rows, thumb_width=a.thumb_width,
            keep_frames=not a.no_frames)
        data["video"] = name
        json.dump(data, open(os.path.join(outdir, "index.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

        n = 2
        if not a.no_broll:
            _step(2, total, "切 B-roll 片段")
            if a.no_frames:
                print("  跳过：B-roll 分类需要单帧，不能与 --no-frames 同用")
            else:
                broll_mod.extract(outdir, fmt=a.clip_format, seg_max=a.seg_max)
            n = 3

        _step(n, total, "生成浏览页")
        page = render.build(outdir, a.terms)
    except util.MissingDependency as e:
        sys.exit(f"\n✗ 缺少依赖：\n{e}")

    print(f"\n\033[1m=== 完成 ===\033[0m\n{outdir}")
    print(f"\n打开:  open '{page}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
