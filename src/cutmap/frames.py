"""密集采样 + dHash 感知去重 → 分镜画面 + contact sheet + index.json

为什么不用 ffmpeg 的场景检测（select='gt(scene,X)'）：
它只识别硬切，抓不到
  ① 白底页面之间的低对比度切换（整体亮度结构相近，差异分低于阈值）
  ② 镜头内的内容演进（文字逐行出现、图表数值增长、表格高亮移动）
实测同一视频：场景检测得 104 个画面，感知去重得 608 个。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw

from . import util


def dhash(path: str, size: int = 8) -> int:
    """差值哈希：缩到 (size+1)×size 灰度，比较每行相邻像素亮度，得 size² 位指纹"""
    im = Image.open(path).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(im.getdata())
    bits = 0
    for r in range(size):
        row = r * (size + 1)
        for c in range(size):
            bits = (bits << 1) | (1 if px[row + c] > px[row + c + 1] else 0)
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def subtitle_own(cues, t0: float, t1: float) -> str:
    """起始于 [t0, t1) 的字幕 —— 每条只归属一帧，用于跨帧拼接

    严格半开区间、无回看。带回看会让相邻帧认领同一条字幕，
    拼接 B-roll 段落时出现整句重复。
    """
    return "".join(c[2] for c in cues if t0 <= c[0] < t1)


def subtitle_at(cues, t: float) -> str:
    """该时刻正在说的话 —— 用于单帧显示，允许与相邻帧相同"""
    for a, b, txt in cues:
        if a <= t < b:
            return txt
    return ""


def _label(path: str, idx: int, t: float) -> None:
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    font = util.load_font(max(14, int(im.width * 0.042)))
    txt = f"#{idx}  {util.hhmmss(t)}  {t:.1f}s"
    bb = d.textbbox((4, 4), txt, font=font)
    d.rectangle([bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2], fill=(0, 0, 0, 170))
    d.text((4, 4), txt, font=font, fill=(255, 235, 60))
    im.save(path, quality=92)


def _sheets(frames_dir: str, outdir: str, cols: int, rows: int, thumb_w: int) -> int:
    per = cols * rows
    names = sorted(os.listdir(frames_dir))
    n = 0
    for s in range(0, len(names), per):
        lst = os.path.join(outdir, f"_l{s}.txt")
        with open(lst, "w") as f:
            for c in names[s:s + per]:
                # concat 的相对路径按列表文件所在目录解析，故写绝对路径
                f.write(f"file '{os.path.abspath(os.path.join(frames_dir, c))}'\n")
        subprocess.run(
            [util.ffmpeg(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
             "-vf", f"scale={thumb_w}:-1,tile={cols}x{rows}:padding=5:margin=5:color=white",
             "-frames:v", "1", "-q:v", "3",
             os.path.join(outdir, f"sheet_{s//per + 1:02d}.jpg")],
            check=False)
        os.remove(lst)
        n += 1
    return n


def extract(video: str, outdir: str, srt: str | None = None, *,
            threshold: int = 10, fps: float = 2, cols: int = 4, rows: int = 4,
            thumb_width: int = 480, keep_frames: bool = True,
            log=print) -> dict:
    """抽分镜画面，写入 outdir，返回 index 数据"""
    cues = util.parse_srt(srt)
    frames_dir = os.path.join(outdir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    log(f"  字幕: {len(cues)} 条" if cues else "  字幕: 无")
    log(f"  密集采样 {fps}fps ...")

    # 临时目录放系统盘：几千个小文件写外置盘（exFAT 簇 1MB）既慢又浪费
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            [util.ffmpeg(), "-v", "error", "-i", video, "-vf",
             f"fps={fps},scale={thumb_width}:-1", "-q:v", "3",
             os.path.join(td, "%06d.jpg")], check=True)
        raw = sorted(os.listdir(td))
        if not raw:
            raise RuntimeError(f"未能从视频抽出任何帧: {video}")
        log(f"  {len(raw)} 帧 → dHash 去重 (阈值 {threshold}) ...")

        kept, last = [], None
        for i, f in enumerate(raw):
            p = os.path.join(td, f)
            h = dhash(p)
            if last is not None and hamming(h, last) < threshold:
                continue
            last = h
            kept.append((i / fps, p))
        log(f"  保留 {len(kept)} 帧 (压缩率 {len(kept)/len(raw)*100:.1f}%)")

        index = []
        for n, (t, src) in enumerate(kept, 1):
            nxt = kept[n][0] if n < len(kept) else t + 1 / fps
            dst = os.path.join(frames_dir, f"{n:04d}_{util.hhmmss(t,'-')}.jpg")
            shutil.copy(src, dst)
            _label(dst, n, t)
            index.append({
                "idx": n,
                "time": round(t, 2),
                "timecode": util.hhmmss(t),
                "span": round(nxt - t, 2),
                "frame": os.path.relpath(dst, outdir),
                "subtitle": subtitle_at(cues, t),
                "subtitle_own": subtitle_own(cues, t, nxt),
            })

    data = {
        "video": os.path.basename(outdir.rstrip("/")),
        # 存绝对路径：后续 broll 直接拿它喂 ffmpeg，
        # 存相对路径会导致换个 cwd 跑就找不到文件
        "source": os.path.abspath(video),
        "method": "dense-sample + dHash dedup",
        "fps": fps, "hash_threshold": threshold,
        "frame_count": len(index), "frames": index,
    }
    json.dump(data, open(os.path.join(outdir, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    log("  生成 contact sheet ...")
    n_sheets = _sheets(frames_dir, outdir, cols, rows, thumb_width)
    if not keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)

    spans = [x["span"] for x in index]
    log(f"  ✓ 画面 {len(index)} 个 / 图墙 {n_sheets} 张 / "
        f"平均间隔 {sum(spans)/len(spans):.1f}s")
    return data
