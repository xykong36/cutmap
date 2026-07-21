"""生成单页浏览器：分镜画面 + B-roll 片段，Tab 切换

产物是单个 HTML，内联全部 CSS/JS，只依赖同目录的图片和视频文件。
"""
from __future__ import annotations

import html
import json
import os
import urllib.parse

from . import subclean
from ._assets import CSS, JS

CLIP = 48  # 字幕折叠阈值（字符数）


def _q(p: str) -> str:
    return html.escape(urllib.parse.quote(p))


def _card_frames(data: dict, terms: str | None) -> list[str]:
    out = []
    for f in data["frames"]:
        sub = subclean.clean(f.get("subtitle", ""), terms_path=terms)
        out.append(
            f'<div class="card">'
            f'<img src="{_q(f["frame"])}" loading="lazy" data-t="{f["time"]}" alt="#{f["idx"]}">'
            f'<div class="body"><div class="tc">'
            f'<button class="seek" data-t="{f["time"]}">{f["timecode"]}</button>'
            f'<span class="tag">#{f["idx"]} · 停留 {f["span"]}s</span></div>'
            f'<div class="sub" data-clip="{CLIP}" data-raw="{html.escape(sub, quote=True)}"></div>'
            f'</div></div>\n')
    return out


def _card_broll(bdata: dict, terms: str | None) -> list[str]:
    out = []
    for s in bdata["segments"]:
        sub = subclean.clean(s.get("subtitle", ""), terms_path=terms)
        out.append(
            f'<div class="card">'
            f'<video class="clip" src="broll/{_q(s["file"])}" loop muted playsinline '
            f'preload="metadata" data-t="{s["start"]}"></video>'
            f'<div class="body"><div class="tc">'
            f'<button class="seek" data-t="{s["start"]}">{s["timecode"]}</button>'
            f'<span class="tag">#{s["idx"]} · {s["duration"]:.0f}s · '
            f'{s["frames"]}个画面</span></div>'
            f'<div class="sub" data-clip="{CLIP}" data-raw="{html.escape(sub, quote=True)}"></div>'
            f'</div></div>\n')
    return out


def build(outdir: str, terms: str | None = None, log=print) -> str:
    data = json.load(open(os.path.join(outdir, "index.json"), encoding="utf-8"))
    name = data["video"]

    bpath = os.path.join(outdir, "broll", "broll.json")
    bdata = json.load(open(bpath, encoding="utf-8")) if os.path.exists(bpath) else None

    fcards = _card_frames(data, terms)
    bcards = _card_broll(bdata, terms) if bdata else []

    meta = (f'{data["frame_count"]} 个画面 · 采样 {data["fps"]}fps · '
            f'去重阈值 {data["hash_threshold"]}')
    if bdata:
        meta += f' · B-roll {bdata["count"]} 段'

    tabs = ('<button class="tab active" data-pane="frames">分镜画面'
            f'<span class="n">{len(fcards)}</span></button>')
    if bcards:
        tabs += ('<button class="tab" data-pane="broll">B-roll 片段'
                 f'<span class="n">{len(bcards)}</span></button>')

    broll_pane = (f'<main id="pane-broll" class="pane">\n{"".join(bcards)}</main>'
                  if bcards else
                  '<main id="pane-broll" class="pane">'
                  '<div class="empty">无 B-roll 片段</div></main>')

    src_rel = urllib.parse.quote(os.path.relpath(data["source"], outdir))
    page = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(name)}</title><style>{CSS}</style></head><body>
<header>
  <div class="top">
    <video id="player" src="{src_rel}" controls preload="metadata"></video>
    <div class="info">
      <h1>{html.escape(name)}</h1>
      <div class="meta">{html.escape(meta)}</div>
      <div class="tools">
        <input type="search" id="q" placeholder="搜索字幕…" autocomplete="off">
        <button id="auto" class="on hidden">自动播放：开</button>
        <span class="count" id="count"></span>
      </div>
    </div>
  </div>
  <div class="tabs">{tabs}</div>
</header>
<main id="pane-frames" class="pane active">
{"".join(fcards)}</main>
{broll_pane}
<script>{JS}</script></body></html>
"""
    out = os.path.join(outdir, "browse.html")
    open(out, "w", encoding="utf-8").write(page)
    log(f"  ✓ browse.html ({os.path.getsize(out)//1024} KB, "
        f"分镜 {len(fcards)} + B-roll {len(bcards)})")
    return out
