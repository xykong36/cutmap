"""共享工具：外部程序定位、跨平台字体、时间码、SRT 解析"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

# ---------------------------------------------------------------- 外部依赖


class MissingDependency(RuntimeError):
    pass


def find_exe(name: str, env_var: str, install_hint: str) -> str:
    """按 环境变量 → PATH 的顺序定位可执行文件"""
    p = os.environ.get(env_var)
    if p and os.path.isfile(p) and os.access(p, os.X_OK):
        return p
    p = shutil.which(name)
    if p:
        return p
    raise MissingDependency(
        f"找不到 {name}。\n{install_hint}\n"
        f"或设置环境变量 {env_var}=/path/to/{name}")


def ffmpeg() -> str:
    return find_exe("ffmpeg", "FFMPEG",
                    "安装： brew install ffmpeg  (macOS)\n"
                    "       apt install ffmpeg   (Debian/Ubuntu)")


def ffprobe() -> str:
    return find_exe("ffprobe", "FFPROBE", "ffprobe 随 ffmpeg 一起安装")


def bbdown() -> str:
    return find_exe(
        "BBDown", "BBDOWN",
        "BBDown 是 B 站下载器，需单独安装：\n"
        "  https://github.com/nilaoda/BBDown/releases\n"
        "下载后放进 PATH，或 brew install bbdown")


def run(cmd, capture=False, check=False):
    return subprocess.run(cmd, capture_output=capture, text=True, check=check)


def probe_duration(path: str) -> float:
    """时长（秒）；不可解码返回 0"""
    r = run([ffprobe(), "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path], capture=True)
    try:
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def valid_video(path: str, min_bytes: int = 100_000) -> bool:
    """能否解码。下载器产出损坏文件时未必返回非零退出码，必须实测"""
    if not os.path.exists(path) or os.path.getsize(path) < min_bytes:
        return False
    return probe_duration(path) > 1


# ---------------------------------------------------------------- 字体

_FONT_CANDIDATES = [
    # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    # Windows
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
]


def load_font(size: int):
    """跨平台加载一个粗体无衬线字体；全部失败则退回 PIL 内置位图字体"""
    from PIL import ImageFont

    override = os.environ.get("BILIKIT_FONT")
    paths = ([override] if override else []) + _FONT_CANDIDATES
    for p in paths:
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------- 时间与字幕


def hhmmss(t: float, sep: str = ":") -> str:
    return f"{int(t//3600):02d}{sep}{int(t%3600//60):02d}{sep}{int(t%60):02d}"


def parse_srt(path: str | None) -> list[tuple[float, float, str]]:
    """→ [(start, end, text), ...]；文件不存在返回空表"""
    if not path or not os.path.exists(path):
        return []
    cues = []
    raw = open(path, encoding="utf-8-sig").read()
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [l for l in block.strip().splitlines() if l.strip()]
        tc = next((l for l in lines if "-->" in l), None)
        if not tc:
            continue
        text = " ".join(lines[lines.index(tc) + 1:]).strip()
        if not text:
            continue
        try:
            a, b = [_sec(x) for x in tc.split("-->")]
        except ValueError:
            continue
        cues.append((a, b, text))
    return cues


def _sec(t: str) -> float:
    h, m, s = t.strip().replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def safe_name(name: str) -> str:
    """文件名净化"""
    return re.sub(r'[/\\:*?"<>|]', "_", name).strip()


def eprint(*a):
    print(*a, file=sys.stderr)
