"""术语归一化测试

重点是回归测试：这些 bug 都不报错、不崩溃，只是悄悄少替换或替换错。
"""
import pytest

from cutmap import subclean


class TestWordBoundary:
    """\\b 在中英混排下失效 —— 本项目踩过的最隐蔽的 bug

    中文字符在 Python 正则里同属 \\w，"用grock测试" 中 用/g 之间不存在
    单词边界，\\bgrock\\b 永远匹配不到。术语表必须用 ASCII 前后瞻。
    """

    @pytest.mark.parametrize("raw,expected", [
        ("用grock测试", "用Grok测试"),
        ("跑openai的模型", "跑OpenAI的模型"),
        ("装了mcp之后", "装了MCP之后"),
        ("买了个iphone", "买了个iPhone"),
        ("DeepSeek和gemini", "DeepSeek和Gemini"),
    ])
    def test_replaces_when_adjacent_to_cjk(self, raw, expected):
        assert subclean.normalize(raw) == expected

    def test_replaces_at_string_edges(self):
        assert subclean.normalize("grock") == "Grok"

    def test_does_not_replace_inside_longer_word(self):
        # 不应把 "grocker" 里的 grock 换掉
        assert "Grok" not in subclean.normalize("grocker")


class TestVariants:
    """同一术语的多种 ASR 变体都要覆盖"""

    # 只收录实际在 ASR 输出里观测到的变体。
    # 不为了凑测试而放宽正则 —— 例如让结尾的 k 变可选会误伤英文词 "sic"。
    @pytest.mark.parametrize("raw", [
        "deep sk", "deep sick", "deep seek", "deepseek",
    ])
    def test_deepseek_variants(self, raw):
        assert subclean.normalize(f"关于{raw}的讨论") == "关于DeepSeek的讨论"

    @pytest.mark.parametrize("raw", ["詹姆", "詹姆乃", "詹姆奶", "詹姆a", "gemini"])
    def test_gemini_variants(self, raw):
        assert subclean.normalize(raw) == "Gemini"


class TestDeliberateNonReplacements:
    """有歧义或属说话人本人用词的，必须保持原样"""

    def test_keeps_speaker_slang(self):
        # 小龙虾是某些 UP 主对 OpenClaw 的戏称，是本人措辞
        assert "小龙虾" in subclean.normalize("我用小龙虾干活")

    def test_keeps_ambiguous_cloud(self):
        # 单独的 cloud 可能指云服务，规则无法区分
        assert subclean.normalize("上传到cloud") == "上传到cloud"


class TestCondense:
    def test_removes_trailing_particle(self):
        assert subclean.condense("这个呢，很重要") == "这个，很重要"

    def test_collapses_stutter(self):
        assert subclean.condense("这个这个方案") == "这个方案"

    def test_idempotent(self):
        once = subclean.clean("用grock测试呢")
        assert subclean.clean(once) == once


class TestTermsFile:
    def test_custom_table_replaces_default(self, tmp_path):
        f = tmp_path / "t.txt"
        f.write_text("# 注释\nfoo => BAR\n", encoding="utf-8")
        assert subclean.normalize("say foo", terms_path=str(f)) == "say BAR"
        # 自定义表完全取代默认表
        assert subclean.normalize("grock", terms_path=str(f)) == "grock"

    def test_rejects_invalid_regex(self, tmp_path):
        f = tmp_path / "bad.txt"
        f.write_text("[unclosed => X\n", encoding="utf-8")
        with pytest.raises(ValueError, match="正则无效"):
            subclean.load_terms(str(f))

    def test_ignores_comments_and_blanks(self, tmp_path):
        f = tmp_path / "t.txt"
        f.write_text("\n# c\n\nfoo => BAR\n没有箭头的行\n", encoding="utf-8")
        assert len(subclean.load_terms(str(f))) == 1
