"""API routes for park-intel."""

import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func

from db.database import get_session
from db.models import Article

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    """Healthcheck endpoint."""
    return {"status": "ok", "service": "park-intel"}


@router.get("/articles/latest")
def get_latest_articles(
    limit: int = Query(default=20, ge=1, le=200),
    source: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    """Get latest articles, optionally filtered by source."""
    session = get_session()
    try:
        query = session.query(Article).order_by(Article.collected_at.desc())
        if source:
            query = query.filter(Article.source == source)
        articles = query.limit(limit).all()
        return [_serialize(a) for a in articles]
    finally:
        session.close()


@router.get("/articles/search")
def search_articles(
    q: str = Query(..., min_length=1),
    source: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Search articles by keyword in title/content."""
    session = get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = session.query(Article).filter(
            Article.collected_at >= cutoff,
            (Article.title.ilike(f"%{q}%")) | (Article.content.ilike(f"%{q}%")),
        )
        if source:
            query = query.filter(Article.source == source)
        articles = query.order_by(Article.collected_at.desc()).limit(limit).all()
        return [_serialize(a) for a in articles]
    finally:
        session.close()


@router.get("/articles/sources")
def get_sources() -> list[dict[str, Any]]:
    """List all sources with article counts."""
    session = get_session()
    try:
        results = (
            session.query(Article.source, func.count(Article.id))
            .group_by(Article.source)
            .all()
        )
        return [{"source": source, "count": count} for source, count in results]
    finally:
        session.close()


def _serialize(article: Article) -> dict[str, Any]:
    """Serialize an Article to a dict."""
    tags = article.tags
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []

    return {
        "id": article.id,
        "source": article.source,
        "source_id": article.source_id,
        "author": article.author,
        "title": article.title,
        "content": article.content[:500] if article.content else None,
        "url": article.url,
        "tags": tags,
        "score": article.score,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "collected_at": article.collected_at.isoformat() if article.collected_at else None,
    }
