---
name: cutmap
description: 看视频内容时使用 —— 用户给了视频链接（YouTube / B站 / bilibili）或本地 mp4，想知道讲了什么、分几段、某个时刻画面是什么、提取里面的 PPT 或分镜。Use when the user shares a video URL or local video file and wants it summarized, described, searched for a moment, or broken into shots. 不适用于纯音频、直播流、以及只需要文字转录的场景。
---

# 用 cutmap 看视频

你读不了 mp4。cutmap 在本地把视频拆成「去重后的画面 jpg + 对齐的字幕 json」，
这两样你都能读 —— 于是你就能真的看见视频内容。全程本地 ffmpeg，不联网、不调模型。

## 流程

```
链接 → yt-dlp 下载 → cutmap 分析 → 读 index.json → 读图墙 jpg → 回答
      （本地文件跳过第一步）
```

前置：`cutmap`、`ffmpeg` 必须已安装，下载还需要 `yt-dlp`。
缺哪个就告诉用户装哪个（`pip install cutmap` / `brew install ffmpeg` / `pip install yt-dlp`），不要试图绕开。

---

## 1. 拿到本地文件

cutmap 只处理本地文件，不下载。给的是链接就你来下：

```bash
yt-dlp --write-auto-subs --sub-langs "zh-Hans,zh,en" --convert-subs srt \
       -f "bv*[height<=720]+ba/b" -o "%(id)s.%(ext)s" "<URL>"
```

三个参数别省，都是踩过的坑：

- `-o "%(id)s.%(ext)s"` —— 用视频 id 当文件名。默认标题名常含中文、空格、`|`、emoji，
  后面每条命令都要转义，极易出错。
- `height<=720` —— 看内容 720p 足够，1080p 只是让下载和抽帧更慢。
- `--convert-subs srt` —— cutmap 只认 srt，不认 vtt。

下完把字幕改成和视频同名，后面命令能少一个参数：

```bash
ls                              # 看真实文件名
mv "abc123.zh-Hans.srt" "abc123.srt"
```

**没抓到字幕不是问题，继续跑。** 纯画面分析依然能得出结构、风格、
界面流程、幻灯片内容 —— 实测无字幕视频也能准确描述分段。
只需在最终回答里说明一句「这个视频没有字幕，以下基于画面」，不必停下来问用户。

---

## 2. 分析

```bash
cutmap abc123.mp4 --no-broll
```

`--no-broll` 一定要加：B-roll 是切视频片段给人看的，你用不上，而且是全流程最慢的一步。
加了之后一个 90 秒视频约 3 秒跑完，16 分钟视频约 1 分钟。

字幕没改成同名的话显式传：`--srt abc123.zh-Hans.srt`

**看命令输出里的 `保留 N 帧`，这个数字决定下一步花多少 token，先看它再决定怎么读。**

---

## 3. 读结果

产物在与视频同名的目录里。**只读两样东西：**

| 文件 | 内容 | 何时读 |
|---|---|---|
| `index.json` | 每个画面的时间戳 + 那一刻的字幕 | 先读，拿全局结构 |
| `sheet_01.jpg`… | 16 格图墙，一张顶 16 帧 | 再读，真正「看」画面 |

**绝对不要读 `浏览.html`** —— 图片全部内联在里面，读进来直接撑爆 context。
CLI 结尾打印的 `open '浏览.html'` 是说给用户的，不是给你的。

**不要遍历 `frames/` 里的单帧**，只在需要看清某个具体时刻的细节时单独读。

### 先算账再读图

一张图墙约 **3000 token**。图墙数量 = 帧数 ÷ 16。

| 帧数 | 图墙 | 全读约 |
|---|---|---|
| 50 | 4 张 | 1.2 万 token |
| 200 | 13 张 | 4 万 |
| 600 | 38 张 | **11 万** |

所以默认策略：

1. 读 `index.json`，看 `frame_count` 和字幕时间线 —— 先有整体判断
2. **只读前 3–5 张图墙**，摸清风格和节奏，很多问题到这一步就能答
3. 用户问到具体时刻，用 `index.json` 定位时间戳，再单独读那几张 `frames/*.jpg`

**帧数超过 200 时**，先把预估开销告诉用户，让他决定要不要全看。
用户明确说「完整分析」「全部看一遍」才全读。

### 图上有坐标，直接引用

每帧左上角烧了黄色标签 `#12  00:03:41  221.0s`，缩进图墙后依然清晰可读。
引用画面时用这个时间戳 —— 说「03:41 这一页换成了架构图」，
不要说「第三张图第二行第四格」，用户看不懂后者。

---

## 帧数不合适时

抽出来的画面太少（漏内容）或太多（大量重复），调 `--threshold` 重跑：

| 值 | 效果 | 场景 |
|---|---|---|
| `6` | 密 | 教程类，要还原每一步操作 |
| `10` | 默认 | |
| `14` | 疏 | 只看大结构和风格 |
| `24` | 很疏 | 超长视频先探底 |

**数字越小画面越多** —— 方向容易记反，改之前确认一遍。

超过 20 分钟的视频，建议先用 `--threshold 14` 跑一遍看结构，
确认值得细看再用默认值重跑。

---

## 完整例子

```bash
# 1. 下载
yt-dlp --write-auto-subs --sub-langs "zh-Hans,zh,en" --convert-subs srt \
       -f "bv*[height<=720]+ba/b" -o "%(id)s.%(ext)s" "https://..."
ls                                    # 确认文件名
mv dQw4w9WgXcQ.zh-Hans.srt dQw4w9WgXcQ.srt

# 2. 分析
cutmap dQw4w9WgXcQ.mp4 --no-broll     # 看输出里的「保留 N 帧」

# 3. 读（Read 工具）
#    dQw4w9WgXcQ/index.json
#    dQw4w9WgXcQ/sheet_01.jpg  … 先读前几张
```
