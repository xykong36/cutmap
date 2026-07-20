"""B-roll 分类测试"""
import pytest
from PIL import Image, ImageDraw

from cutmap import broll


@pytest.fixture
def frame(tmp_path):
    def make(name, level, subtitle_text=False):
        """level: 0-255 灰度；subtitle_text=True 时叠一行白字（模拟烧录字幕）"""
        im = Image.new("RGB", (160, 90), (level, level, level))
        if subtitle_text:
            ImageDraw.Draw(im).text((20, 60), "SUBTITLE LINE", fill=(255, 255, 255))
        p = tmp_path / name
        im.save(p)
        return str(p)
    return make


class TestIsFlat:
    """黑场卡不能用标准差判定 —— 卡上烧着白字幕会把标准差拉到 23~33"""

    def test_pure_black_is_flat(self, frame):
        assert broll.is_flat(frame("a.png", 0))

    def test_black_with_burned_in_subtitle_is_still_flat(self, frame):
        # 这条是核心回归：用标准差判定会漏掉它
        assert broll.is_flat(frame("b.png", 3, subtitle_text=True))

    def test_pure_white_is_flat(self, frame):
        assert broll.is_flat(frame("c.png", 255))

    def test_merely_dark_footage_is_not_flat(self, frame):
        """阈值放松到 <25 会把偏暗的正常画面误判成转场
        （某片实测 290s 转场 vs 实际 20s）"""
        assert not broll.is_flat(frame("d.png", 20))
        assert not broll.is_flat(frame("e.png", 30))

    def test_midtone_is_not_flat(self, frame):
        assert not broll.is_flat(frame("f.png", 128))


def _index(frames_meta):
    return {"frames": frames_meta}


class TestSegmentation:
    def _mk(self, tmp_path, n, span=1.0, level=128):
        """生成 n 个同样画面的帧记录 + 实际图片"""
        meta = []
        for i in range(n):
            im = Image.new("RGB", (160, 90), (level, level, level))
            rel = f"f{i}.png"
            im.save(tmp_path / rel)
            meta.append({"idx": i + 1, "time": i * span, "span": span,
                         "frame": rel, "subtitle": "", "subtitle_own": ""})
        return meta

    def test_splits_long_run_at_seg_max(self, tmp_path):
        """没有主镜头作分隔的视频（纯屏幕录制）会把几百秒并成一段。
        实测某 390s 视频出现过单个 280s 的"片段"。"""
        meta = self._mk(tmp_path, 100, span=1.0)
        segs, total = broll.classify(_index(meta), str(tmp_path), seg_max=20)
        assert total == pytest.approx(100.0)
        assert all(s["end"] - s["start"] <= 20.5 for s in segs)
        assert len(segs) >= 5

    def test_no_split_when_under_seg_max(self, tmp_path):
        meta = self._mk(tmp_path, 5, span=1.0)
        segs, _ = broll.classify(_index(meta), str(tmp_path), seg_max=45)
        assert len(segs) == 1

    def test_transition_cards_form_own_segments(self, tmp_path):
        meta = self._mk(tmp_path, 3, level=128)
        # 中间插一张纯黑
        Image.new("RGB", (160, 90), (0, 0, 0)).save(tmp_path / "black.png")
        meta.insert(1, {"idx": 99, "time": 0.5, "span": 0.5, "frame": "black.png",
                        "subtitle": "", "subtitle_own": ""})
        segs, _ = broll.classify(_index(meta), str(tmp_path), seg_max=45)
        assert any(s["kind"] == "转场" for s in segs)

    def test_segments_are_contiguous(self, tmp_path):
        meta = self._mk(tmp_path, 20, span=1.0)
        segs, _ = broll.classify(_index(meta), str(tmp_path), seg_max=5)
        for a, b in zip(segs, segs[1:]):
            assert a["end"] == pytest.approx(b["start"])
