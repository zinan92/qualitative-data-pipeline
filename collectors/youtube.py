"""YouTube collector using channel RSS feeds."""

import hashlib
import logging
from datetime import datetime
from time import mktime, struct_time
from typing import Any

import feedparser

from collectors.base import BaseCollector
from config import YOUTUBE_CHANNELS

logger = logging.getLogger(__name__)

# YouTube exposes RSS at this URL pattern (no API key needed)
_YT_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


class YouTubeCollector(BaseCollector):
    """Collect recent videos from YouTube channel RSS feeds."""

    source = "youtube"

    @staticmethod
    def _parse_published(entry: Any) -> datetime | None:
        for field in ("published_parsed", "updated_parsed"):
            val = getattr(entry, field, None)
            if isinstance(val, struct_time):
                try:
                    return datetime.fromtimestamp(mktime(val))
                except (ValueError, OverflowError):
                    pass
        for field in ("published", "updated"):
            raw = getattr(entry, field, None)
            if raw:
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _video_id_from_entry(entry: Any) -> str | None:
        """Extract YouTube video id from entry."""
        # yt:videoId tag
        vid = getattr(entry, "yt_videoid", None)
        if vid:
            return vid
        # Fallback: parse from link
        link = getattr(entry, "link", "") or ""
        if "watch?v=" in link:
            return link.split("watch?v=")[-1].split("&")[0]
        return hashlib.sha256(link.encode()).hexdigest()[:16] if link else None

    @staticmethod
    def _infer_tags(title: str, channel: str) -> list[str]:
        tags: list[str] = []
        title_lower = title.lower()

        channel_topics: dict[str, list[str]] = {
            "Alex Finn": ["ai"],
            "AI超元域": ["ai"],
            "Eric Tech": ["ai", "tech"],
            "Y Combinator": ["startups", "tech"],
            "AI LABS": ["ai"],
            "Peter Yang": ["ai", "tech"],
        }
        if channel in channel_topics:
            tags.extend(channel_topics[channel])

        keyword_tags = {
            "ai": ["ai", "artificial intelligence", "llm", "gpt", "claude", "gemini"],
            "crypto": ["crypto", "bitcoin", "ethereum", "web3"],
            "trading": ["trading", "market", "投资"],
        }
        for tag, keywords in keyword_tags.items():
            if any(kw in title_lower for kw in keywords) and tag not in tags:
                tags.append(tag)

        return tags

    def _fetch_channel(self, name: str, channel_id: str) -> list[dict[str, Any]]:
        url = _YT_RSS.format(channel_id=channel_id)
        logger.info("Fetching YouTube RSS: %s (%s)", name, channel_id)
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            logger.error("Failed to parse YouTube feed %s: %s", name, e)
            return []

        if feed.bozo and not feed.entries:
            logger.warning("YouTube feed %s bozo with no entries: %s", name, feed.bozo_exception)
            return []

        articles: list[dict[str, Any]] = []
        for entry in feed.entries:
            vid = self._video_id_from_entry(entry)
            if not vid:
                continue

            title = getattr(entry, "title", "") or ""
            # YouTube RSS gives media_description or summary
            description = ""
            if hasattr(entry, "media_group") and entry.media_group:
                for mg in entry.media_group:
                    if hasattr(mg, "media_description"):
                        description = mg.media_description
                        break
            if not description:
                description = getattr(entry, "summary", "") or ""

            articles.append({
                "source": self.source,
                "source_id": f"yt_{vid}",
                "author": name,
                "title": title,
                "content": description,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "tags": self._infer_tags(title, name),
                "score": 0,
                "published_at": self._parse_published(entry),
            })

        logger.info("Got %d videos from %s", len(articles), name)
        return articles

    def collect(self) -> list[dict[str, Any]]:
        all_articles: list[dict[str, Any]] = []
        for name, channel_id in YOUTUBE_CHANNELS.items():
            articles = self._fetch_channel(name, channel_id)
            all_articles.extend(articles)
        return all_articles
