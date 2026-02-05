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


@router.get("/articles/digest")
def get_digest(
    hours: int = Query(default=24, ge=1, le=168),
    limit_per_source: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """Get a digest of articles grouped by source, sorted by score/recency.
    Designed for Morning analyst consumption."""
    session = get_session()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        articles = (
            session.query(Article)
            .filter(Article.collected_at >= cutoff)
            .all()
        )

        # Group by source
        by_source: dict[str, list[Article]] = {}
        for a in articles:
            by_source.setdefault(a.source, []).append(a)

        sources_out: dict[str, Any] = {}
        all_tags: list[str] = []

        for source, source_articles in by_source.items():
            # Sort: hackernews by score desc, others by published_at desc
            if source == "hackernews":
                source_articles.sort(key=lambda a: a.score or 0, reverse=True)
            else:
                source_articles.sort(
                    key=lambda a: a.published_at or datetime.min, reverse=True
                )

            limited = source_articles[:limit_per_source]
            serialized = [_serialize(a) for a in limited]
            sources_out[source] = {
                "count": len(serialized),
                "articles": serialized,
            }

            # Collect tags from ALL articles in the period (not just limited)
            for a in source_articles:
                tags = a.tags
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except (json.JSONDecodeError, TypeError):
                        tags = []
                if isinstance(tags, list):
                    all_tags.extend(str(t).lower().strip() for t in tags if t)

        # Count tag frequency
        tag_counts: dict[str, int] = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = sorted(
            [{"tag": tag, "count": count} for tag, count in tag_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:30]

        return {
            "period": f"last {hours}h",
            "generated_at": datetime.utcnow().isoformat(),
            "sources": sources_out,
            "top_tags": top_tags,
        }
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
