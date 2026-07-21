<div align="center">

# cutmap

**Read a video like a document.**
Skim a long video in minutes to learn fast — or study it frame-by-frame to see exactly how it's cut.

[![English](https://img.shields.io/badge/lang-English-2b7489?style=flat-square)](https://github.com/xykong36/cutmap/blob/main/README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-lightgrey?style=flat-square)](https://github.com/xykong36/cutmap/blob/main/README.zh-CN.md)
[![PyPI](https://img.shields.io/pypi/v/cutmap?style=flat-square&color=3775a9)](https://pypi.org/project/cutmap/)
[![CI](https://github.com/xykong36/cutmap/actions/workflows/ci.yml/badge.svg)](https://github.com/xykong36/cutmap/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](https://github.com/xykong36/cutmap/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![No LLM](https://img.shields.io/badge/LLM-not%20required-success?style=flat-square)](#)

</div>

Watching a video is slow and linear — you can't skim it the way you skim an article,
and you can't Ctrl-F a moment. cutmap fixes that. Give it a video (and subtitles if you
have them) and it builds a single HTML page you can actually **read**: every visually
distinct frame laid out in order, each captioned with what was being said. Click a frame
to jump the player there; search the subtitles to find a moment.

![storyboard](https://raw.githubusercontent.com/xykong36/cutmap/main/examples/storyboard.png)

<sub>Demo footage: [@林亦LYi](https://www.youtube.com/@lyi) — [《一个视频搞懂 DeepSeek V4！》](https://www.youtube.com/watch?v=WDQjRzVcX-A), all rights reserved by the creator</sub>

Two things people use it for:

- 📖 **Learn faster.** Turn a one-hour talk or tutorial into a page you scroll in a few
  minutes. See the whole structure at a glance, search the transcript, and only play the
  parts you actually need.
- 🎬 **Study the edit ("拉片").** If you make videos, see exactly how someone cut theirs —
  every shot change, every B-roll insert, every on-screen graphic — laid out as one storyboard.

It runs entirely on your machine. **No LLM, no API key, no network.**

---

## Quick start

### The easy way — just ask your AI agent

cutmap ships with a [Claude Code](https://claude.com/claude-code) skill. Install it once,
then talk in plain language — the agent downloads the video, runs cutmap, reads the
result, and answers you:

```bash
pip install cutmap yt-dlp          # cutmap + video downloader
brew install ffmpeg                # the video engine  (Linux: apt install ffmpeg)

# install the bundled skill for Claude Code
git clone https://github.com/xykong36/cutmap
cp -r cutmap/skills/cutmap ~/.claude/skills/
```

Then just say things like:

> **Download** `https://youtu.be/…` **and use cutmap to summarize what it covers**
>
> **Use cutmap on** `lecture.mp4` **and give me the section-by-section breakdown**
>
> **What's on screen around 3:41 in that video?** (process it with cutmap first)

The agent handles the download, the flags, and reading the frames for you — you never
touch the command line.

### The manual way — command line

```bash
pip install cutmap
brew install ffmpeg                # macOS   (Linux: apt install ffmpeg)

cutmap video.mp4 --srt video.srt   # or just: cutmap video.mp4  (finds video.srt)
open video/browse.html             # ← open this in your browser
```

That's it. Everything you need is in the `video/` folder next to your file.

---

## What you get

Output lands in a directory named after the video:

```
video/
├── browse.html        ← open this: the interactive storyboard
├── frames/            every distinct frame, labelled #index timecode seconds
├── sheet_01..NN.jpg   4×4 contact sheets for scanning at a glance
├── index.json         frame timestamps + aligned subtitles (machine readable)
└── broll/             extracted B-roll clips + broll.json
```

### The browse page

One self-contained HTML file — all CSS and JS inlined. Two tabs:

**Storyboard** — every distinct frame with its caption
**B-roll** — auto-looping clips (reads like a GIF wall)

![B-roll clips auto-looping](https://raw.githubusercontent.com/xykong36/cutmap/main/examples/broll-demo.gif)

<sub>The B-roll tab in motion: clips auto-loop like a GIF wall, but they are MP4 under the hood — 1/24 the size of actual GIFs</sub>

What you can do on it:

- **Click any frame or timecode** to seek the embedded player there (local file, no network)
- **Search the subtitles** — matches the *normalised* text, so searching `DeepSeek` also
  finds frames where the auto-transcription wrote `deep sick`
- Long captions collapse behind `…expand`
- Follows your system light / dark mode

Contact sheets are also written on their own, for scanning a whole video in a few images:

![contact sheet](https://raw.githubusercontent.com/xykong36/cutmap/main/examples/contact-sheet.jpg)

---

## How it works

The interesting part is *which* frames it keeps. Sampling every N seconds is both
redundant and lossy: a 30-second talking-head passage gives you ten identical stills;
a fast montage cutting five shots in three seconds gives you one.

cutmap asks a different question — not *"how often should I sample"* but
**"which frames actually differ"**:

```
dense sample  →  perceptual hash each frame  →  compare against last kept frame
                                             →  keep only if different enough
```

Static passages collapse to a single frame. Every visual change gets one.

<details>
<summary><b>Why not ffmpeg's built-in scene detection?</b></summary>

<br>

`select='gt(scene,0.3)'` only catches **hard cuts**. Two things slip past it:

1. **Low-contrast transitions** — white slide to white webpage. Similar overall
   luminance structure, so the difference score never crosses the threshold.
2. **Intra-shot evolution** — text appearing line by line, charts animating,
   table rows highlighting. Not a "cut" by any definition, but visually distinct.

Measured on one 16-minute video: scene detection found **104** frames,
perceptual dedup found **608**. One 25-second stretch that scene detection called
a single shot actually contained three completely different pages.

</details>

<details>
<summary><b>The algorithm's blind spot</b></summary>

<br>

dHash compares **relative brightness between adjacent pixels**, so it measures spatial
structure, not colour. Two different flat colours produce an identical (all-zero)
fingerprint and cannot be told apart. Footage that is largely flat-coloured or
near-black will therefore dedup more aggressively than you might expect. (This is also
why transition cards are detected by mean luminance rather than by hash.)

</details>

---

## Options

Most people never need these — the defaults are tuned for slides, screencasts, and
talks. Reach for them when the frame count comes out too dense or too sparse.

| Flag | Meaning |
|---|---|
| `--threshold N` | Frame density. **Lower = more frames.** `6` dense / `10` default / `14` sparse / `24` structure-only |
| `--fps N` | Dense sampling rate (default 2 — finest resolvable gap is 0.5s) |
| `--seg-max N` | Max seconds per B-roll segment (default 45) |
| `--clip-format` | `mp4` (default) / `gif` / `webp` |
| `--no-broll` | Skip B-roll extraction (much faster) |
| `--no-frames` | Keep only contact sheets, drop individual frames |
| `--cols/--rows` | Contact sheet grid (default 4×4) |
| `--thumb-width` | Thumbnail width in px (default 480) |
| `--terms FILE` | Custom subtitle term-normalisation table |

**Rule of thumb for density:** screencasts and slides → keep the default `10`. Real
handheld / vlog / interview footage → start at `--threshold 20` (camera shake makes
every frame look "different" otherwise).

<details>
<summary><b>Density, measured</b></summary>

<br>

On a 969-second video (2 fps sampling → 1936 raw frames):

| Threshold | Kept | Avg gap | Good for |
|---|---|---|---|
| 6 | 892 | 1.1s | Reconstructing every visual step (tutorial walkthroughs) |
| **10** | **597** | **1.6s** | **Default** — balances coverage and readability |
| 14 | 463 | 2.1s | Style study, quick scanning |
| 24 | 241 | 4.0s | Structure only, close to a traditional shot list |

The curve is smooth — there is no natural breakpoint. This is an aesthetic choice,
not a parameter with a computable optimum.

</details>

---

## B-roll detection

Frames are sorted into three buckets by three plain rules — no model involved:

| Bucket | Rule |
|---|---|
| **Main shot** | A cluster of near-identical frames recurring across >50% of the runtime — i.e. a locked-off camera |
| **Transition card** | Mean luminance below 8 (black) or above 245 (white) |
| **B-roll** | Everything else |

Screencast-style videos with no talking head degrade gracefully — no main shot is
found, everything becomes B-roll, and `--seg-max` keeps it segmented.

Clips default to **MP4** (`loop muted`), which looks identical to a GIF in the page but
is ~24× smaller (0.08 MB vs 1.96 MB for a 9-second segment). Use `--clip-format gif`
only when pasting into chat apps or note tools.

---

## Subtitle term normalisation

Auto-transcription mangles proper nouns. A built-in table normalises them:

```
大家对deep sick新模型的期待值   →   大家对DeepSeek新模型的期待值
用grock测试                    →   用Grok测试
```

The real payoff is **search**: querying `DeepSeek` finds every frame whose subtitle
was transcribed as `deep sick`. The default table targets AI / tech content; bring your
own with `--terms my_terms.txt` (one `regex => replacement` per line, see
[`src/cutmap/terms.txt`](https://github.com/xykong36/cutmap/blob/main/src/cutmap/terms.txt)).

This is term normalisation, not proofreading — it will not fix grammar or one-off errors.

---

## Getting footage manually

If you're not using the agent skill, cutmap itself doesn't download anything — it works
on local files. For YouTube / Bilibili, grab the video and subtitles with
[yt-dlp](https://github.com/yt-dlp/yt-dlp):

```bash
yt-dlp --write-auto-subs --sub-langs "en,zh-Hans" --convert-subs srt \
       -f "bv*[height<=720]+ba/b" -o "%(id)s.%(ext)s" "<URL>"
cutmap <id>.mp4
```

Respect the terms of service and copyright of wherever your footage comes from; use
downloaded material for personal study and research only.

---

<details>
<summary><b>Troubleshooting — bugs I hit building this</b></summary>

<br>

Most of these **never raised an error** — they just quietly produced wrong output:

**`\b` word boundaries fail in mixed CJK/Latin text.** CJK characters are `\w` in Python,
so in `用grock测试` there is no boundary between `用` and `g`. `\bgrock\b` never matches.
The term table uses `(?<![A-Za-z0-9])…(?![A-Za-z0-9])` instead.

**Flat frames can't be detected by standard deviation.** Black transition cards usually
have burned-in white subtitles, pushing stddev to 23–33. Use mean luminance, kept tight
(`<8`): loosening to `<25` misclassifies merely-dark footage as transitions.

**Subtitle time windows must not overlap.** A look-back to avoid empty captions makes
adjacent frames claim the same cue. Hence two fields: `subtitle` (display, may repeat)
and `subtitle_own` (concatenation, strict half-open).

**ffmpeg concat resolves relative paths against the list file's directory** — contact
sheet file lists must contain absolute paths.

**`-v error` suppresses `showinfo` output** — any ffmpeg statistics gathered with it
silently come back as zero.

**Multi-threaded downloads corrupt files on exFAT.** Pre-allocating and writing at
multiple offsets over exFAT-on-USB yields files with the right size and wrong contents
(`moov atom not found`). Download to local disk, then move.

</details>

---

## Credits

Built on [ffmpeg](https://ffmpeg.org) and [Pillow](https://python-pillow.org).

Special thanks to **[@林亦LYi](https://www.youtube.com/@lyi)**. This project started as an
attempt to study the editing in his videos — dense cutting, interleaved infographics and
animated demos — exactly the material naive interval-screenshotting handles worst. The
screenshots in this README are from
**[《一个视频搞懂 DeepSeek V4！》](https://www.youtube.com/watch?v=WDQjRzVcX-A)**, used solely
to demonstrate this tool's output; all rights remain with the original creator. If he
would prefer them removed, please open an issue and they will be replaced immediately.

| | |
|---|---|
| Source video | <https://www.youtube.com/watch?v=WDQjRzVcX-A> |
| Creator | YouTube <https://www.youtube.com/@lyi> · Bilibili <https://space.bilibili.com/4401694> |

## License

MIT
