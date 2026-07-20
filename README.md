<div align="center">

# cutmap

**Turn any video into a browsable, searchable storyboard — and auto-extract its B-roll.**

[![English](https://img.shields.io/badge/lang-English-2b7489?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-lightgrey?style=flat-square)](README.zh-CN.md)
[![CI](https://github.com/xykong36/cutmap/actions/workflows/ci.yml/badge.svg)](https://github.com/xykong36/cutmap/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![No LLM](https://img.shields.io/badge/LLM-not%20required-success?style=flat-square)](#)

</div>

Give it a video and a subtitle file. Get back a single HTML page: the source player on
the left, every distinct frame on the right, each captioned with what was being said.
Click any frame to jump the player to that moment. Search the subtitles to locate a shot.

```bash
cutmap video.mp4 --srt video.srt
open video/浏览.html
```

Everything runs locally through `ffmpeg` + `Pillow`. **No model calls, no API keys, no network.**

![storyboard](examples/storyboard.png)

---

## Why not just screenshot every N seconds

Interval sampling is both redundant and lossy. A 30-second talking-head passage yields
ten identical stills; a fast montage cutting five shots in three seconds yields one.

cutmap asks a different question — not *"how often should I sample"* but
**"which frames actually differ"**:

```
dense sample  →  perceptual hash each frame  →  compare against last kept frame
                                             →  keep only if different enough
```

Static passages collapse to a single frame. Every visual change gets one.

### Why not ffmpeg's built-in scene detection

`select='gt(scene,0.3)'` only catches **hard cuts**. Two things slip past it:

1. **Low-contrast transitions** — white slide to white webpage. Similar overall
   luminance structure, so the difference score never crosses the threshold.
2. **Intra-shot evolution** — text appearing line by line, charts animating,
   table rows highlighting. Not a "cut" by any definition, but visually distinct.

Measured on one 16-minute video: scene detection found **104** frames,
perceptual dedup found **608**. One 25-second stretch that scene detection called
a single shot actually contained three completely different pages.

---

## Install

```bash
pip install cutmap
```

Requires **ffmpeg** on your `PATH`:

```bash
brew install ffmpeg          # macOS
apt install ffmpeg           # Debian / Ubuntu
```

---

## Usage

```bash
cutmap video.mp4                      # looks for video.srt alongside
cutmap video.mp4 --srt subs.srt
cutmap ./material-dir/                # dir containing 源片.mp4 + 字幕.srt
```

Output lands in a directory named after the video:

```
video/
├── frames/            every distinct frame, labelled #index timecode seconds
├── sheet_01..NN.jpg   4×4 contact sheets for scanning at a glance
├── index.json         frame timestamps + aligned subtitles (machine readable)
├── broll/             extracted B-roll clips + broll.json
└── 浏览.html          ← open this
```

### Options

| Flag | Meaning |
|---|---|
| `--threshold N` | Frame density. Lower = denser. `6` dense / `10` default / `14` sparse |
| `--fps N` | Dense sampling rate (default 2 — finest resolvable gap is 0.5s) |
| `--cols/--rows` | Contact sheet grid (default 4×4) |
| `--thumb-width` | Thumbnail width in px (default 480) |
| `--seg-max N` | Max seconds per B-roll segment (default 45) |
| `--clip-format` | `mp4` (default) / `gif` / `webp` |
| `--no-broll` | Skip B-roll extraction |
| `--no-frames` | Keep only contact sheets, drop individual frames |
| `--terms FILE` | Custom subtitle term-normalisation table |

### Picking a density

Measured on a 969-second video (2 fps sampling → 1936 raw frames):

| Threshold | Kept | Avg gap | Good for |
|---|---|---|---|
| 6 | 892 | 1.1s | Reconstructing every visual step (tutorial walkthroughs) |
| **10** | **597** | **1.6s** | **Default** — balances coverage and readability |
| 14 | 463 | 2.1s | Style study, quick scanning |
| 24 | 241 | 4.0s | Structure only, close to a traditional shot list |

The curve is smooth — there is no natural breakpoint. This is an **aesthetic choice,
not a parameter with a computable optimum.**

---

## The browse page

One self-contained HTML file. All CSS and JS inlined; only depends on the images and
clips sitting next to it. Two tabs:

**Storyboard** — every distinct frame with its caption
**B-roll** — auto-looping clips (reads like a GIF wall)

![b-roll](examples/broll.png)

Shared behaviour:

- Embedded source player up top — **click any timecode or frame to seek there**
  (local file, no network)
- Live subtitle search, matching against the **normalised** text
  (searching `DeepSeek` finds frames whose ASR wrote `deep sick`)
- Long captions collapse behind `…expand`
- B-roll clips play only while in viewport (IntersectionObserver) — dozens of
  simultaneously decoding videos will freeze a browser
- Follows system light / dark mode

Contact sheets are written separately, for scanning a whole video in a few images:

![contact sheet](examples/contact-sheet.jpg)

---

## B-roll detection

Frames are sorted into three buckets by three plain rules — no model involved:

| Bucket | Rule |
|---|---|
| **Main shot** | A cluster of near-identical frames recurring across >50% of the runtime — i.e. a locked-off camera |
| **Transition card** | Mean luminance below 8 (black) or above 245 (white) |
| **B-roll** | Everything else |

Measured on one episode: B-roll 49 segments / 731s (75.5%),
main shot 39 / 217s (22.4%), transitions 16 / 20s (2.1%).

Screencast-style videos with no talking head degrade gracefully — no main shot is
found, everything becomes B-roll, and `--seg-max` keeps it segmented.

### Clip format

Same nine-second segment:

| Format | Size | Note |
|---|---|---|
| GIF 10fps | 1.96 MB | 256 colours; visible banding on gradients |
| WebP | 0.39 MB | Middle ground |
| **MP4** | **0.08 MB** | **Default** — 24× smaller than GIF, better quality |

MP4 with `loop muted` is visually indistinguishable from a GIF in the page.
Reach for `--clip-format gif` only when pasting into chat apps or note tools.

---

## Subtitle term normalisation

ASR mangles proper nouns. A built-in table normalises them:

```
大家对deep sick新模型的期待值   →   大家对DeepSeek新模型的期待值
用grock测试                    →   用Grok测试
```

The real payoff is **search**: querying `DeepSeek` finds every frame whose subtitle
was transcribed as `deep sick`.

The default table targets AI / tech content. Bring your own:

```bash
cutmap video.mp4 --terms my_terms.txt
```

Format is one `regex => replacement` per line — see
[`src/cutmap/terms.txt`](src/cutmap/terms.txt).

**This is term normalisation, not proofreading.** It will not fix segmentation,
grammar, or one-off errors — those need a language model, which is out of scope here.

---

## Troubleshooting

Bugs hit while building this. Most of them **never raised an error** — they just
quietly produced wrong output:

**`\b` word boundaries fail in mixed CJK/Latin text**
CJK characters are `\w` in Python, so in `用grock测试` there is no boundary between
`用` and `g`. `\bgrock\b` never matches. The term table uses
`(?<![A-Za-z0-9])…(?![A-Za-z0-9])` instead.

**Flat frames can't be detected by standard deviation**
Black transition cards usually have burned-in white subtitles, pushing stddev to
23–33 — far above any "flat colour" threshold. Use mean luminance, and keep it tight
(`<8`): loosening to `<25` misclassifies merely-dark footage as transitions.

**Subtitle time windows must not overlap**
Adding a look-back to avoid empty captions makes adjacent frames claim the same cue,
producing duplicated sentences when concatenated. Hence two fields:
`subtitle` (display, may repeat) and `subtitle_own` (concatenation, strict half-open).

**ffmpeg concat resolves relative paths against the list file's directory**
Contact sheet file lists must contain absolute paths.

**`-v error` suppresses `showinfo` output**
Any ffmpeg-based statistics gathered with `-v error` silently come back as zero.

**Multi-threaded downloads corrupt files on exFAT** (if you fetch footage yourself)
Pre-allocating and writing at multiple offsets over exFAT-on-USB yields files with
the right size and wrong contents — `moov atom not found`. Download to local disk,
then move.

---

## Getting footage

cutmap does not download anything — it works on local files.

For Bilibili, [BBDown](https://github.com/nilaoda/BBDown) muxes subtitles into the mp4;
pull them out and hand both to cutmap:

```bash
BBDown <BV-id> --skip-ai false
ffmpeg -i video.mp4 -map 0:m:language:chi subs.srt
cutmap video.mp4 --srt subs.srt
```

Respect the terms of service and copyright of wherever your footage comes from.
Use downloaded material for personal study and research only.

---

## Credits

Built on [ffmpeg](https://ffmpeg.org) and [Pillow](https://python-pillow.org).
Demo footage from [@林亦LYi](https://space.bilibili.com/4401694) on Bilibili.

## License

MIT
