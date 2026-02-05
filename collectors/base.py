"""Base collector with common dedup and save logic."""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from db.database import get_session, init_db
from db.models import Article

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base for all collectors."""

    source: str  # Must be set by subclasses

    def __init__(self) -> None:
        init_db()

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        """Fetch articles from the source. Returns list of article dicts."""
        ...

    def save(self, articles: list[dict[str, Any]]) -> int:
        """Save articles to DB with dedup. Returns count of new articles saved."""
        session = get_session()
        saved = 0
        try:
            for data in articles:
                article = Article(
                    source=data.get("source", self.source),
                    source_id=data.get("source_id"),
                    author=data.get("author"),
                    title=data.get("title"),
                    content=data.get("content"),
                    url=data.get("url"),
                    tags=json.dumps(data["tags"]) if isinstance(data.get("tags"), list) else data.get("tags"),
                    score=data.get("score", 0),
                    published_at=data.get("published_at"),
                    collected_at=datetime.utcnow(),
                )
                session.add(article)
                try:
                    session.flush()
                    saved += 1
                except IntegrityError:
                    session.rollback()
                    logger.debug("Duplicate skipped: %s", data.get("source_id"))
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Error saving articles for %s", self.source)
            raise
        finally:
            session.close()

        logger.info("[%s] Saved %d new articles (of %d fetched)", self.source, saved, len(articles))
        return saved

    def run(self) -> int:
        """Collect and save. Returns count of new articles."""
        articles = self.collect()
        if not articles:
            logger.info("[%s] No articles collected", self.source)
            return 0
        return self.save(articles)
