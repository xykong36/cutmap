"""感知哈希与字幕对齐测试"""
import pytest
from PIL import Image

from cutmap import frames, util


@pytest.fixture
def img(tmp_path):
    def make(name, color=(0, 0, 0), size=(64, 36), noise=None):
        im = Image.new("RGB", size, color)
        if noise:
            for i, px in enumerate(noise):
                im.putpixel((i % size[0], i // size[0]), px)
        p = tmp_path / name
        im.save(p)
        return str(p)
    return make


class TestDHash:
    def test_identical_images_have_zero_distance(self, img):
        a, b = img("a.png", (30, 60, 90)), img("b.png", (30, 60, 90))
        assert frames.hamming(frames.dhash(a), frames.dhash(b)) == 0

    def test_returns_64_bits_for_size_8(self, img):
        h = frames.dhash(img("a.png", (128, 128, 128)))
        assert 0 <= h < 2 ** 64

    def test_different_images_differ(self, img):
        # 左黑右白 vs 左白右黑：每行相邻像素比较结果完全相反
        left = Image.new("RGB", (64, 36), (0, 0, 0))
        right = Image.new("RGB", (64, 36), (255, 255, 255))
        for x in range(32, 64):
            for y in range(36):
                left.putpixel((x, y), (255, 255, 255))
                right.putpixel((x, y), (0, 0, 0))
        import os
        import tempfile
        d = tempfile.mkdtemp()
        pa, pb = os.path.join(d, "l.png"), os.path.join(d, "r.png")
        left.save(pa)
        right.save(pb)
        assert frames.hamming(frames.dhash(pa), frames.dhash(pb)) > 0


class TestHamming:
    @pytest.mark.parametrize("a,b,d", [(0, 0, 0), (0b1010, 0b1010, 0),
                                       (0b1111, 0b0000, 4), (0b1010, 0b0101, 4)])
    def test_counts_differing_bits(self, a, b, d):
        assert frames.hamming(a, b) == d


CUES = [(0.0, 2.0, "第一句"), (2.0, 4.0, "第二句"), (5.0, 7.0, "第三句")]


class TestSubtitleAlignment:
    """两个函数语义不同，混用会导致 B-roll 拼接时整句重复"""

    def test_at_returns_active_cue(self):
        assert frames.subtitle_at(CUES, 1.0) == "第一句"
        assert frames.subtitle_at(CUES, 3.0) == "第二句"

    def test_at_returns_empty_in_gap(self):
        assert frames.subtitle_at(CUES, 4.5) == ""

    def test_at_may_repeat_across_adjacent_frames(self):
        # 显示用：相邻帧落在同一条 cue 内，返回相同文本是正确行为
        assert frames.subtitle_at(CUES, 0.5) == frames.subtitle_at(CUES, 1.5)

    def test_own_is_strictly_half_open(self):
        assert frames.subtitle_own(CUES, 0.0, 2.0) == "第一句"
        assert frames.subtitle_own(CUES, 2.0, 4.0) == "第二句"

    def test_own_never_double_counts(self):
        """相邻窗口拼接后，每条 cue 恰好出现一次 —— 这是防重复的核心保证"""
        windows = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 8)]
        joined = "".join(frames.subtitle_own(CUES, a, b) for a, b in windows)
        for _s, _e, text in CUES:
            assert joined.count(text) == 1

    def test_own_empty_when_no_cue_starts_inside(self):
        assert frames.subtitle_own(CUES, 0.5, 1.5) == ""


class TestParseSrt:
    def test_parses_basic(self, tmp_path):
        p = tmp_path / "a.srt"
        p.write_text("1\n00:00:01,500 --> 00:00:03,000\n你好\n\n"
                     "2\n00:00:03,000 --> 00:00:05,000\n世界\n", encoding="utf-8")
        cues = util.parse_srt(str(p))
        assert len(cues) == 2
        assert cues[0] == (1.5, 3.0, "你好")

    def test_missing_file_returns_empty(self):
        assert util.parse_srt("/nonexistent.srt") == []
        assert util.parse_srt(None) == []

    def test_handles_bom(self, tmp_path):
        p = tmp_path / "b.srt"
        p.write_bytes("﻿1\n00:00:00,000 --> 00:00:01,000\n甲\n".encode())
        assert util.parse_srt(str(p))[0][2] == "甲"

    def test_joins_multiline_text(self, tmp_path):
        p = tmp_path / "c.srt"
        p.write_text("1\n00:00:00,000 --> 00:00:01,000\n上\n下\n", encoding="utf-8")
        assert util.parse_srt(str(p))[0][2] == "上 下"

    def test_skips_empty_text_blocks(self, tmp_path):
        p = tmp_path / "d.srt"
        p.write_text("1\n00:00:00,000 --> 00:00:01,000\n\n\n"
                     "2\n00:00:01,000 --> 00:00:02,000\n有内容\n", encoding="utf-8")
        assert len(util.parse_srt(str(p))) == 1


class TestHhmmss:
    @pytest.mark.parametrize("sec,out", [(0, "00:00:00"), (61, "00:01:01"),
                                         (3661, "01:01:01"), (59.9, "00:00:59")])
    def test_formats(self, sec, out):
        assert util.hhmmss(sec) == out

    def test_custom_separator(self):
        assert util.hhmmss(61, "-") == "00-01-01"
