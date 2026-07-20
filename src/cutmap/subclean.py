"""字幕术语归一化 + 口水词精简（纯规则，零 LLM 调用）

这不是语义校对。只修高频、无歧义的固定错误：
真正的语法 / 断句 / 低频错词需要过模型。
"""
from __future__ import annotations

import os
import re
from functools import lru_cache

DEFAULT_TERMS = os.path.join(os.path.dirname(__file__), "terms.txt")

# 句中语气助词，删掉不影响语义
FILLERS = [
    (r"呢(?=[，。、）]|$)", ""),        # 句末的"呢"
    (r"(?<=[了的是在])呢", ""),          # 助词后的"呢"
    (r"^(那|然后|就是说|其实呢|那么)", ""),
    (r"这个这个", "这个"),
    (r"就是就是", "就是"),
    (r"我们我们", "我们"),
]


@lru_cache(maxsize=8)
def load_terms(path: str | None = None) -> tuple[tuple[str, str], ...]:
    """读术语表。优先级：显式参数 > CUTMAP_TERMS 环境变量 > 内置表"""
    path = path or os.environ.get("CUTMAP_TERMS") or DEFAULT_TERMS
    rules = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=>" not in line:
                continue
            pat, rep = line.split("=>", 1)
            pat, rep = pat.strip(), rep.strip()
            try:
                re.compile(pat)
            except re.error as e:
                raise ValueError(f"{path}:{lineno} 正则无效: {pat} ({e})") from e
            rules.append((pat, rep))
    return tuple(rules)


def normalize(text: str, terms_path: str | None = None) -> str:
    for pat, rep in load_terms(terms_path):
        text = re.sub(pat, rep, text, flags=re.I)
    return text


def condense(text: str) -> str:
    for pat, rep in FILLERS:
        text = re.sub(pat, rep, text)
    return re.sub(r"\s{2,}", " ", text).strip()


def clean(text: str, fillers: bool = True, terms_path: str | None = None) -> str:
    t = normalize(text, terms_path)
    return condense(t) if fillers else t
