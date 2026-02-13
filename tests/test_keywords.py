"""Tests for keyword-based article tagger."""

from tagging.keywords import tag_article


def test_crypto_tags():
    tags = tag_article("Bitcoin hits 100k", "BTC surges past all-time high")
    assert "crypto" in tags


def test_ai_tags():
    tags = tag_article("OpenAI releases GPT-5", "The new LLM model...")
    assert "ai" in tags


def test_macro_tags():
    tags = tag_article("Fed cuts rates by 25bp", "Interest rate decision")
    assert "macro" in tags


def test_chinese_keywords():
    tags = tag_article("美联储降息25基点", "利率决议后美股大涨")
    assert "macro" in tags
    assert "us-market" in tags


def test_chinese_ai():
    tags = tag_article("大模型最新进展", "人工智能在金融领域的应用")
    assert "ai" in tags


def test_multi_tag():
    tags = tag_article("NVIDIA earnings beat", "GPU demand fueled by AI training")
    assert "sector/tech" in tags
    assert "ai" in tags


def test_empty_content():
    tags = tag_article("", "")
    assert tags == []


def test_none_inputs():
    tags = tag_article(None, None)
    assert tags == []


def test_max_tags_limit():
    # Article touching many topics
    title = "Bitcoin AI chip semiconductor earnings gold trading"
    content = "crypto blockchain fed interest rate nvidia gpu bank fintech oil solar"
    tags = tag_article(title, content)
    assert len(tags) <= 5


def test_title_weighted_higher():
    # "crypto" in title should rank it higher than tags only in content
    tags = tag_article("Bitcoin crash", "The market had some AI news and semiconductor updates")
    assert tags[0] == "crypto"


def test_geopolitics():
    tags = tag_article("US imposes new sanctions", "Trade war escalates with new tariffs")
    assert "geopolitics" in tags


def test_china_market():
    tags = tag_article("A股大涨", "沪深300指数上涨3%，北向资金净流入50亿")
    assert "china-market" in tags


def test_earnings():
    tags = tag_article("财报季来了", "营收超预期，净利润增长30%")
    assert "earnings" in tags
