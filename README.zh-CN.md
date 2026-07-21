<div align="center">

# cutmap

**像读文档一样读视频。**
几分钟扫读一个长视频快速学习 —— 或者逐帧拉片,看清它到底是怎么剪的。

[![English](https://img.shields.io/badge/lang-English-lightgrey?style=flat-square)](README.md)
[![简体中文](https://img.shields.io/badge/lang-简体中文-2b7489?style=flat-square)](README.zh-CN.md)
[![PyPI](https://img.shields.io/pypi/v/cutmap?style=flat-square&color=3775a9)](https://pypi.org/project/cutmap/)
[![CI](https://github.com/xykong36/cutmap/actions/workflows/ci.yml/badge.svg)](https://github.com/xykong36/cutmap/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![无需大模型](https://img.shields.io/badge/大模型-不需要-success?style=flat-square)](#)

</div>

看视频又慢又线性 —— 没法像读文章那样一眼扫过,也没法 Ctrl-F 定位到某一刻。cutmap 就是来解决这个的。
给它一个视频(有字幕更好),它生成一个能真正**读**的单页 HTML:每一个不同的画面按顺序铺开,
每张配着当时说的话。点任意画面,播放器跳到那一刻;搜字幕,定位到对应画面。

![分镜浏览](examples/storyboard.png)

<sub>演示素材：[@林亦LYi](https://www.youtube.com/@lyi) [《一个视频搞懂 DeepSeek V4！》](https://www.youtube.com/watch?v=WDQjRzVcX-A)，版权归原作者所有</sub>

两种常见用法:

- 📖 **快速学习。** 把一小时的演讲/教程变成一页,滚几分钟就扫完。一眼看清整体结构,搜字幕定位重点,
  只播你真正需要的那几段。
- 🎬 **拉片研究剪辑。** 如果你做视频,可以看清别人是怎么剪的 —— 每一次镜头切换、每一段 B-roll、
  每一个屏幕图形,全部铺成一张分镜表。

全程本地运行。**不调模型、不要 API key、不联网。**

---

## 快速上手

### 最省事 —— 直接吩咐 AI agent

cutmap 自带一个 [Claude Code](https://claude.com/claude-code) skill。装一次,之后用大白话说需求就行 ——
agent 会自动下载视频、跑 cutmap、读结果、然后回答你:

```bash
pip install cutmap yt-dlp          # cutmap + 视频下载器
brew install ffmpeg                # 视频引擎（Linux: apt install ffmpeg）

# 安装自带的 Claude Code skill
git clone https://github.com/xykong36/cutmap
cp -r cutmap/skills/cutmap ~/.claude/skills/
```

然后直接说：

> **下载** `https://youtu.be/…` **并用 cutmap 处理,帮我总结讲了什么**
>
> **用 cutmap 分析** `lecture.mp4`**,分成几段、每段讲什么**
>
> **这个视频 3:41 画面是什么?**（先用 cutmap 处理）

下载、参数、读画面这些 agent 全包了 —— 你一行命令都不用敲。

### 手动方式 —— 命令行

```bash
pip install cutmap
brew install ffmpeg                # macOS（Linux: apt install ffmpeg）

cutmap video.mp4 --srt subtitle.srt  # 或直接 cutmap video.mp4（自动找同名 .srt）
open 视频/browse.html              # ← 用浏览器打开这个
```

就这样,你要的一切都在视频同名的文件夹里。

---

## 产物

产物落在与视频同名的目录里：

```
视频名/
├── browse.html        ← 打开这个：交互式分镜页
├── frames/            每个不同画面一张，带 #序号 时间码 秒数 标注
├── sheet_01~NN.jpg    4×4 图墙，适合几张图扫完整片
├── index.json         画面时间戳 + 对齐字幕（可供其他程序消费）
└── broll/             切出的 B-roll 片段 + broll.json
```

### 浏览页

单个自包含 HTML，CSS 和 JS 全部内联。两个 Tab：

**分镜画面** —— 每个不同画面配当时的字幕
**B-roll 片段** —— 自动循环播放的片段（观感等同 GIF 墙）

![B-roll 片段自动循环播放](examples/broll-demo.gif)

<sub>B-roll 标签页的实际效果：片段自动循环播放，观感等同 GIF 墙，但底层是 MP4（体积仅为 GIF 的 1/24）</sub>

在页面上能做的：

- **点任意画面或时间码**，内嵌播放器跳到那一刻（本地文件，不联网）
- **搜字幕** —— 匹配的是*归一化后*的文本，所以搜 `DeepSeek` 也能命中 ASR 写成 `deep sick` 的画面
- 超长字幕折叠为 `…展开`
- 跟随系统深色 / 浅色模式

图墙也单独输出，适合用几张图扫完整片：

![图墙](examples/contact-sheet.jpg)

---

## 原理

真正有意思的是它**留哪些帧**。固定间隔采样既冗余又漏内容：口播段落 30 秒画面不动,会截出十张一样的图；
快剪蒙太奇 3 秒切 5 个镜头,只截到 1 张。

cutmap 换了个问法 —— 不问「隔多久截一张」,而是问**「哪些画面彼此不同」**：

```
密集采样  →  逐帧算感知哈希  →  与上一张保留帧比差异
                             →  差异够大才留
```

静止段落自动坍缩成一张，画面一变就留一张。

<details>
<summary><b>为什么不用 ffmpeg 自带的场景检测？</b></summary>

<br>

`select='gt(scene,0.3)'` 只识别**硬切**，两类内容它抓不到：

1. **低对比度切换** —— 白底 PPT 切白底网页。整体亮度结构相近，差异分永远够不到阈值。
2. **镜头内的内容演进** —— 文字逐行出现、图表动画增长、表格高亮移动。
   按任何定义都不算「切镜头」，但视觉上确实是不同画面。

实测同一个 16 分钟视频：场景检测得 **104** 个画面，感知去重得 **608** 个。
其中一段 25 秒被场景检测判为「单个镜头」，实际包含 3 个完全不同的页面。

</details>

<details>
<summary><b>算法的一个盲区</b></summary>

<br>

dHash 比较的是**相邻像素之间的明暗关系**，衡量的是空间结构而非颜色。
两张不同的纯色图会产生完全相同（全 0）的指纹，无法区分。
因此大面积纯色或接近全黑的素材，去重会比预期更激进。（转场卡的识别之所以走亮度均值而不是哈希，也是这个原因。）

</details>

---

## 参数

多数人用不上这些 —— 默认值是为幻灯片、录屏、演讲调好的。只有当抽出来的帧太密或太疏时才需要动。

| 参数 | 说明 |
|---|---|
| `--threshold N` | 画面密度，**越小帧越多**：`6` 密 / `10` 默认 / `14` 疏 / `24` 只看大结构 |
| `--fps N` | 密集采样帧率（默认 2，即最细能分辨 0.5 秒） |
| `--seg-max N` | B-roll 单段上限秒数（默认 45） |
| `--clip-format` | `mp4`（默认）/ `gif` / `webp` |
| `--no-broll` | 跳过 B-roll 切片（快很多） |
| `--no-frames` | 只留图墙，不留单帧 |
| `--cols/--rows` | 图墙行列（默认 4×4） |
| `--thumb-width` | 缩略图宽度 px（默认 480） |
| `--terms FILE` | 自定义字幕术语表 |

**密度经验法则：** 录屏、幻灯片 → 用默认 `10`；真人实拍 / vlog / 访谈 / 手持 → 起手 `--threshold 20`
（否则镜头轻微抖动会让每一帧都算「不同」）。

<details>
<summary><b>密度实测曲线</b></summary>

<br>

969 秒视频，2fps 采样得 1936 帧：

| 阈值 | 保留帧 | 平均间隔 | 适合 |
|---|---|---|---|
| 6 | 892 | 1.1s | 完整还原每一步视觉变化（教程复盘） |
| **10** | **597** | **1.6s** | **默认**，兼顾覆盖与可读 |
| 14 | 463 | 2.1s | 风格研究、快速浏览 |
| 24 | 241 | 4.0s | 只看大结构，接近传统分镜表 |

曲线是平缓的，没有天然分界点 —— 这是审美选择，不是能算出最优解的技术参数。

</details>

---

## B-roll 自动识别

三条纯规则把画面分成三类，不需要模型：

| 类别 | 判据 |
|---|---|
| **主镜头** | 跨度超过全片 50% 且反复出现的高度相似画面簇 —— 即固定机位 |
| **转场卡** | 亮度均值低于 8（纯黑）或高于 245（纯白） |
| **B-roll** | 其余 |

纯屏幕录制、没有口播机位的视频会优雅降级 —— 找不到主镜头，全部归为 B-roll，靠 `--seg-max` 保证不会糊成一整坨。

片段默认 **MP4**（`loop muted`），页面里观感与 GIF 无异，但体积约为 1/24（9 秒片段 0.08 MB vs 1.96 MB）。
只有要贴进聊天软件或笔记工具时，才需要 `--clip-format gif`。

---

## 字幕术语归一化

ASR 对专有名词的识别经常面目全非。内置术语表做归一化：

```
大家对deep sick新模型的期待值   →   大家对DeepSeek新模型的期待值
用grock测试                    →   用Grok测试
```

真正的价值在**搜索**：搜 `DeepSeek` 能命中所有被转写成 `deep sick` 的画面。默认表面向 AI / 科技类内容，
可自带词表 `--terms 我的词表.txt`（每行一条 `正则 => 替换`，见
[`src/cutmap/terms.txt`](src/cutmap/terms.txt)）。

这是术语归一化，不是校对 —— 它修不了断句、语法和低频错词。

---

## 手动获取素材

如果你不用 agent skill，cutmap 本身不做下载，只处理本地文件。YouTube / B 站可用
[yt-dlp](https://github.com/yt-dlp/yt-dlp) 把视频和字幕一起抓下来：

```bash
yt-dlp --write-auto-subs --sub-langs "zh-Hans,zh,en" --convert-subs srt \
       -f "bv*[height<=720]+ba/b" -o "%(id)s.%(ext)s" "<URL>"
cutmap <id>.mp4
```

请遵守素材来源平台的服务条款与著作权法律，下载内容仅用于个人学习研究。

---

<details>
<summary><b>踩过的坑 —— 开发时遇到的问题</b></summary>

<br>

多数**不报错、不崩溃，只是悄悄产出错误结果**：

**正则 `\b` 在中英混排下失效。** 中文字符在 Python 里同属 `\w`，`用grock测试` 中 `用` 和 `g` 之间不存在单词边界，
`\bgrock\b` 永远匹配不到。术语表统一改用 `(?<![A-Za-z0-9])…(?![A-Za-z0-9])`。

**纯色帧不能用标准差判定。** 黑场转场卡上通常烧录着白色字幕，标准差被拉到 23~33。应改用亮度均值，
且阈值要收紧（`<8`）—— 放宽到 `<25` 会把偏暗的正常画面也误判成转场。

**取字幕的时间窗口不能重叠。** 若为避免空字幕而加「向前回看」，相邻帧会认领同一条字幕。故拆成两个字段：
`subtitle`（显示用，允许重复）与 `subtitle_own`（拼接用，严格半开区间）。

**ffmpeg concat 的相对路径按列表文件所在目录解析** —— 拼图墙的文件列表里必须写绝对路径。

**`-v error` 会吞掉 `showinfo` 的输出** —— 用 ffmpeg 做统计时若带了它，结果会静默全为 0。

**多线程下载在 exFAT 上会写坏文件。** 预分配后在多个偏移并发写，在 exFAT + USB 上产出「大小正确、内容错误」
的文件，表现为 `moov atom not found`。先下到本机磁盘再搬运即可。

</details>

---

## 致谢

基于 [ffmpeg](https://ffmpeg.org) 与 [Pillow](https://python-pillow.org) 构建。

特别感谢 UP 主 **[@林亦LYi](https://www.youtube.com/@lyi)**。本项目最初就是为了研究他视频里的剪辑手法而写的 ——
密集的画面切换、穿插的信息图与演示动画，正是"每隔 N 秒截一张"这种笨办法处理不了的素材。README 里的演示截图取自他的
**[《一个视频搞懂 DeepSeek V4！》](https://www.youtube.com/watch?v=WDQjRzVcX-A)**，仅用于展示本工具的输出效果，
版权归原作者所有。若原作者希望移除，请提 issue，我会立即替换。

| | |
|---|---|
| 素材视频 | <https://www.youtube.com/watch?v=WDQjRzVcX-A> |
| 作者频道 | YouTube <https://www.youtube.com/@lyi> · 哔哩哔哩 <https://space.bilibili.com/4401694> |

## License

MIT
