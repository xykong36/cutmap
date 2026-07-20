"""把视频切成 B-roll 片段，用于研究剪辑手法

分类靠三条纯规则，不需要模型：
  1. 主镜头(A-roll) = 贯穿全片反复出现的高度相似画面簇（固定机位）
  2. 转场卡        = 亮度均值极低/极高的纯色帧
  3. B-roll        = 其余
"""
from __future__ import annotations

import json
import os
import subprocess

from PIL import Image, ImageStat

from . import util
from .frames import dhash, hamming

CLUSTER_TH = 12        # 聚类相似度阈值（汉明距离）
AROLL_SPAN = 0.5       # 簇的时间跨度占全片比例超过此值，才可能是固定机位
AROLL_MIN_FRAMES = 8
SEG_MAX = 45           # 单段上限（秒）


def is_flat(path: str) -> bool:
    """黑场 / 白场转场卡

    不能用标准差判定：这类卡上常烧录着字幕，标准差被文字拉到 23~33，
    远高于"纯色"阈值。改用亮度均值——实测真黑场卡均值 <8。
    阈值也不能放太松：均值 <25 会把偏暗的正常内容误判成转场
    （某片实测 290s vs 实际 20s）。
    """
    st = ImageStat.Stat(Image.open(path).convert("L"))
    return st.mean[0] < 8 or st.mean[0] > 245


def classify(index: dict, root: str, seg_max: float = SEG_MAX) -> tuple[list, float]:
    frames = index["frames"]
    total = frames[-1]["time"] + frames[-1]["span"]

    hs = []
    for f in frames:
        p = os.path.join(root, f["frame"])
        hs.append((f, dhash(p), is_flat(p)))

    clusters: list[dict] = []
    for f, h, flat in hs:
        for c in clusters:
            if hamming(h, c["h"]) < CLUSTER_TH:
                c["items"].append(f)
                break
        else:
            clusters.append({"h": h, "items": [f], "flat": flat})

    flat_ids = {id(f) for f, _, flat in hs if flat}
    aroll_ids: set[int] = set()
    for c in clusters:
        if len(c["items"]) < AROLL_MIN_FRAMES or c["flat"]:
            continue
        ts = [x["time"] for x in c["items"]]
        if (max(ts) - min(ts)) / total >= AROLL_SPAN:
            aroll_ids |= {id(x) for x in c["items"]}

    def kind(f):
        if id(f) in flat_ids:
            return "转场"
        return "主镜头" if id(f) in aroll_ids else "B-roll"

    segs, cur = [], None
    for f in frames:
        k = kind(f)
        # 同类连续帧合并，但超过 seg_max 强制断开：
        # 全程屏幕演示、没有主镜头作分隔的视频，否则会并成一整坨
        # （实测 390s 的视频被切出单个 280s 的"片段"）
        too_long = cur is not None and (f["time"] + f["span"] - cur["start"]) > seg_max
        if cur and cur["kind"] == k and not too_long:
            cur["frames"].append(f)
            cur["end"] = f["time"] + f["span"]
        else:
            if cur:
                segs.append(cur)
            cur = {"kind": k, "frames": [f], "start": f["time"],
                   "end": f["time"] + f["span"]}
    if cur:
        segs.append(cur)
    return segs, total


def _cut(video: str, start: float, dur: float, out: str, fmt: str) -> None:
    ff = util.ffmpeg()
    common = [ff, "-v", "error", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", video]
    if fmt == "mp4":
        cmd = common + ["-an", "-vf", "scale=480:-1", "-c:v", "libx264", "-crf", "28",
                        "-preset", "veryfast", "-movflags", "+faststart", "-y", out]
    elif fmt == "webp":
        cmd = common + ["-vf", "fps=12,scale=480:-1", "-loop", "0", "-q:v", "70", "-y", out]
    else:  # gif —— 体积约为 mp4 的 24 倍且只有 256 色，仅在需要贴进聊天/笔记时用
        cmd = common + ["-vf", "fps=10,scale=480:-1,split[a][b];[a]palettegen[p];"
                              "[b][p]paletteuse", "-y", out]
    subprocess.run(cmd, check=False)


def extract(outdir: str, *, fmt: str = "mp4", min_duration: float = 1.5,
            seg_max: float = SEG_MAX, log=print) -> dict:
    """从已有的 index.json 切 B-roll，写入 outdir/broll/"""
    index = json.load(open(os.path.join(outdir, "index.json"), encoding="utf-8"))
    video = index["source"]
    segs, total = classify(index, outdir, seg_max)

    stat: dict[str, list] = {}
    for s in segs:
        e = stat.setdefault(s["kind"], [0, 0.0])
        e[0] += 1
        e[1] += s["end"] - s["start"]
    for k, (n, t) in sorted(stat.items(), key=lambda x: -x[1][1]):
        log(f"  {k:>7}: {n:3d} 段, 累计 {t:5.0f}s ({t/total*100:4.1f}%)")

    picks = [s for s in segs
             if s["kind"] == "B-roll" and s["end"] - s["start"] >= min_duration]
    bdir = os.path.join(outdir, "broll")
    os.makedirs(bdir, exist_ok=True)
    log(f"  导出 {len(picks)} 个 B-roll 片段 ({fmt}) ...")

    meta = []
    for i, s in enumerate(picks, 1):
        dur = s["end"] - s["start"]
        name = (f"{i:03d}_{int(s['start']//60):02d}-{int(s['start']%60):02d}"
                f"_{dur:.0f}s.{fmt}")
        _cut(video, s["start"], dur, os.path.join(bdir, name), fmt)
        # 用独占字段拼接（相邻帧窗口不重叠），并去掉连续重复句作为兜底
        parts, prev = [], None
        for f in s["frames"]:
            t = f.get("subtitle_own") or ""
            if t and t != prev:
                parts.append(t)
                prev = t
        meta.append({
            "idx": i, "file": name, "start": round(s["start"], 2),
            "timecode": util.hhmmss(s["start"]), "duration": round(dur, 2),
            "frames": len(s["frames"]), "subtitle": "".join(parts),
        })

    data = {"video": index["video"], "format": fmt, "count": len(meta), "segments": meta}
    json.dump(data, open(os.path.join(bdir, "broll.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    size = sum(os.path.getsize(os.path.join(bdir, m["file"])) for m in meta)
    log(f"  ✓ {len(meta)} 个片段, 合计 {size/1048576:.1f} MB")
    return data
