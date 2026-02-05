"""Substack collector using RSS/feedparser."""

import hashlib
import logging
from datetime import datetime
from time import mktime, struct_time
from typing import Any

import feedparser

from collectors.base import BaseCollector
from config import SUBSTACK_FEEDS

logger = logging.getLogger(__name__)


class SubstackCollector(BaseCollector):
    """Collect articles from Substack RSS feeds."""

    source = "substack"

    @staticmethod
    def _parse_published(entry: Any) -> datetime | None:
        """Parse published date from feed entry."""
        for field in ("published_parsed", "updated_parsed"):
            val = getattr(entry, field, None)
            if isinstance(val, struct_time):
                try:
                    return datetime.fromtimestamp(mktime(val))
                except (ValueError, OverflowError):
                    pass
        # Fallback: try raw string
        for field in ("published", "updated"):
            raw = getattr(entry, field, None)
            if raw:
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _url_hash(url: str) -> str:
        """Create a short hash of a URL for dedup."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    @staticmethod
    def _extract_content(entry: Any) -> str | None:
        """Extract content/summary from a feed entry."""
        # Prefer content field
        if hasattr(entry, "content") and entry.content:
            for c in entry.content:
                if c.get("value"):
                    return c["value"]
        # Fallback to summary
        return getattr(entry, "summary", None)

    @staticmethod
    def _infer_tags(title: str, author: str) -> list[str]:
        """Infer tags from title and known author topics."""
        tags: list[str] = []
        title_lower = title.lower()

        author_topics: dict[str, list[str]] = {
            "The Pomp Letter": ["crypto", "macro"],
            "Doomberg": ["energy", "commodities"],
            "One Useful Thing": ["ai"],
            "AI Supremacy": ["ai"],
            "Interconnects": ["ai"],
            "Dwarkesh Patel": ["ai", "tech"],
            "SemiAnalysis": ["chips", "ai"],
        }
        if author in author_topics:
            tags.extend(author_topics[author])

        keyword_tags = {
            "ai": ["ai", "artificial intelligence", "llm", "gpt"],
            "crypto": ["crypto", "bitcoin", "ethereum"],
            "trading": ["trading", "market"],
        }
        for tag, keywords in keyword_tags.items():
            if any(kw in title_lower for kw in keywords) and tag not in tags:
                tags.append(tag)

        return tags

    def _fetch_feed(self, name: str, url: str) -> list[dict[str, Any]]:
        """Parse a single RSS feed and return article dicts."""
        logger.info("Fetching feed: %s", name)
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            logger.error("Failed to parse feed %s: %s", name, e)
            return []

        if feed.bozo and not feed.entries:
            logger.warning("Feed %s returned bozo with no entries: %s", name, feed.bozo_exception)
            return []

        articles: list[dict[str, Any]] = []
        for entry in feed.entries:
            entry_url = getattr(entry, "link", "") or ""
            if not entry_url:
                continue

            articles.append({
                "source": self.source,
                "source_id": f"substack_{self._url_hash(entry_url)}",
                "author": name,
                "title": getattr(entry, "title", None),
                "content": self._extract_content(entry),
                "url": entry_url,
                "tags": self._infer_tags(getattr(entry, "title", ""), name),
                "score": 0,
                "published_at": self._parse_published(entry),
            })

        logger.info("Got %d entries from %s", len(articles), name)
        return articles

    def collect(self) -> list[dict[str, Any]]:
        """Collect articles from all configured Substack feeds."""
        all_articles: list[dict[str, Any]] = []
        for name, url in SUBSTACK_FEEDS.items():
            articles = self._fetch_feed(name, url)
            all_articles.extend(articles)
        return all_articles
