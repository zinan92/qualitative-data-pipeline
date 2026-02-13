"""Keyword-based article tagger for fast classification."""

import re

# Tag → list of (pattern, weight) tuples
# Patterns are compiled regexes for word-boundary matching
_TAG_RULES: dict[str, list[tuple[re.Pattern, int]]] = {}

_RAW_RULES: dict[str, list[str]] = {
    "ai": [
        "ai", "llm", "gpt", "openai", "anthropic", "deepseek", "claude",
        "gemini", "machine learning", "deep learning", "neural network",
        "transformer", "大模型", "人工智能", "chatgpt",
    ],
    "crypto": [
        "bitcoin", "btc", "ethereum", "eth", "blockchain", "web3",
        "defi", "nft", "solana", "加密", "比特币", "币圈", "crypto",
    ],
    "macro": [
        "fed", "federal reserve", "interest rate", "inflation", "gdp",
        "cpi", "ppi", "treasury", "yield curve", "recession",
        "宏观", "美联储", "利率", "通胀", "降息", "加息",
    ],
    "geopolitics": [
        "sanctions", "tariff", "trade war", "geopolitic",
        "制裁", "关税", "贸易战", "台海", "地缘",
    ],
    "china-market": [
        "a-share", "a股", "沪深", "港股", "北向资金", "中概",
        "上证", "深证", "恒生", "hsi", "hang seng",
    ],
    "us-market": [
        "s&p 500", "s&p500", "nasdaq", "dow jones", "美股",
        "纳斯达克", "标普", "wall street", "nyse",
    ],
    "sector/tech": [
        "semiconductor", "nvidia", "chip", "gpu", "tsmc", "asml",
        "芯片", "半导体", "台积电",
    ],
    "sector/finance": [
        "bank", "fintech", "insurance", "银行", "金融", "保险",
    ],
    "sector/energy": [
        "oil", "solar", "lithium", "ev ", "electric vehicle",
        "能源", "新能源", "电池", "光伏", "石油",
    ],
    "trading": [
        "trading", "quant", "options", "futures", "hedge fund",
        "交易", "量化", "期权", "期货", "对冲",
    ],
    "regulation": [
        "sec ", "compliance", "antitrust", "regulation",
        "监管", "合规", "反垄断",
    ],
    "earnings": [
        "earnings", "revenue", "eps", "quarterly results", "guidance",
        "财报", "营收", "业绩", "净利润",
    ],
    "commodities": [
        "gold", "silver", "copper", "iron ore", "crude oil",
        "黄金", "白银", "大宗商品", "原油",
    ],
}


def _compile_rules() -> None:
    """Compile keyword patterns into regexes (called once at import)."""
    for tag, keywords in _RAW_RULES.items():
        patterns = []
        for kw in keywords:
            # Chinese characters don't need word boundaries
            if any("\u4e00" <= ch <= "\u9fff" for ch in kw):
                patterns.append((re.compile(re.escape(kw), re.IGNORECASE), 1))
            else:
                patterns.append((re.compile(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", re.IGNORECASE), 1))
        _TAG_RULES[tag] = patterns


_compile_rules()


def tag_article(title: str | None, content: str | None, max_tags: int = 5) -> list[str]:
    """Score and return top tags for an article.

    Title matches are weighted 3x. Content is truncated to first 2000 chars.
    Returns up to max_tags sorted by score descending.
    """
    title = (title or "").strip()
    content = (content or "").strip()[:2000]

    scores: dict[str, int] = {}
    for tag, patterns in _TAG_RULES.items():
        total = 0
        for pattern, weight in patterns:
            title_matches = len(pattern.findall(title))
            content_matches = len(pattern.findall(content))
            total += (title_matches * 3 + content_matches) * weight
        if total > 0:
            scores[tag] = total

    sorted_tags = sorted(scores, key=lambda t: scores[t], reverse=True)
    return sorted_tags[:max_tags]
