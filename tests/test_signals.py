"""Tests for the /api/articles/signals endpoint."""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from db.database import get_engine, get_session, init_db
from db.models import Article, Base
from main import app


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    db_path = tmp_path / "test.db"
    # Patch in both config and db.database (which imports by value)
    monkeypatch.setattr("config.DB_PATH", db_path)
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    monkeypatch.setattr("db.database.DB_PATH", db_path)
    monkeypatch.setattr("db.database.DATA_DIR", tmp_path)

    # Reset engine/session so they use the new path
    import db.database as db_mod
    db_mod._engine = None
    db_mod._SessionFactory = None

    init_db()

    # Seed test data
    session = get_session()
    now = datetime.utcnow()
    articles = [
        Article(
            source="twitter",
            source_id="test_1",
            title="Bitcoin hits new ATH",
            content="BTC surges past 100k today",
            tags=json.dumps(["crypto"]),
            score=100,
            relevance_score=5,
            narrative_tags=json.dumps(["btc-new-ath"]),
            collected_at=now - timedelta(hours=1),
            published_at=now - timedelta(hours=1),
        ),
        Article(
            source="hackernews",
            source_id="test_2",
            title="OpenAI raises $10B",
            content="AI company secures massive funding round",
            tags=json.dumps(["ai"]),
            score=200,
            relevance_score=4,
            narrative_tags=json.dumps(["openai-fundraise"]),
            collected_at=now - timedelta(hours=2),
            published_at=now - timedelta(hours=2),
        ),
        Article(
            source="twitter",
            source_id="test_3",
            title="Random tweet",
            content="Nothing market related here",
            tags=json.dumps([]),
            score=5,
            relevance_score=1,
            narrative_tags=json.dumps([]),
            collected_at=now - timedelta(hours=3),
            published_at=now - timedelta(hours=3),
        ),
        # Previous period article
        Article(
            source="twitter",
            source_id="test_4",
            title="Old crypto news",
            content="Bitcoin was discussed yesterday",
            tags=json.dumps(["crypto"]),
            score=50,
            relevance_score=3,
            narrative_tags=json.dumps(["btc-consolidation"]),
            collected_at=now - timedelta(hours=30),
            published_at=now - timedelta(hours=30),
        ),
    ]
    for a in articles:
        session.add(a)
    session.commit()
    session.close()

    yield

    db_mod._engine = None
    db_mod._SessionFactory = None


@pytest.fixture
def client():
    return TestClient(app)


def test_signals_basic_structure(client):
    resp = client.get("/api/articles/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "article_count" in data
    assert "high_relevance_count" in data
    assert "topic_heat" in data
    assert "narrative_momentum" in data
    assert "relevance_distribution" in data
    assert "source_activity" in data
    assert "top_articles" in data


def test_signals_article_count(client):
    resp = client.get("/api/articles/signals?hours=24")
    data = resp.json()
    assert data["article_count"] == 3  # 3 articles in last 24h


def test_signals_high_relevance(client):
    resp = client.get("/api/articles/signals?hours=24")
    data = resp.json()
    assert data["high_relevance_count"] == 2  # score 4 and 5


def test_signals_topic_heat(client):
    resp = client.get("/api/articles/signals?hours=24&compare_hours=24")
    data = resp.json()
    heat_tags = {h["tag"] for h in data["topic_heat"]}
    assert "crypto" in heat_tags
    assert "ai" in heat_tags


def test_signals_relevance_distribution(client):
    resp = client.get("/api/articles/signals?hours=24")
    data = resp.json()
    dist = data["relevance_distribution"]
    assert dist["5"] == 1
    assert dist["4"] == 1
    assert dist["1"] == 1
    assert dist["unscored"] == 0


def test_signals_source_filter(client):
    resp = client.get("/api/articles/signals?hours=24&source=hackernews")
    data = resp.json()
    assert data["article_count"] == 1
    assert data["source_activity"][0]["source"] == "hackernews"


def test_signals_narrative_momentum(client):
    resp = client.get("/api/articles/signals?hours=24")
    data = resp.json()
    narratives = {n["narrative_tag"] for n in data["narrative_momentum"]}
    assert "btc-new-ath" in narratives
    assert "openai-fundraise" in narratives


def test_signals_top_articles_ordered(client):
    resp = client.get("/api/articles/signals?hours=24&min_relevance=3")
    data = resp.json()
    top = data["top_articles"]
    assert len(top) == 2  # only relevance >= 3
    assert top[0]["relevance_score"] >= top[1]["relevance_score"]


def test_latest_has_new_fields(client):
    resp = client.get("/api/articles/latest?limit=1")
    data = resp.json()
    assert len(data) == 1
    assert "relevance_score" in data[0]
    assert "narrative_tags" in data[0]


def test_latest_min_relevance_filter(client):
    resp = client.get("/api/articles/latest?min_relevance=4")
    data = resp.json()
    assert all(a["relevance_score"] >= 4 for a in data)
