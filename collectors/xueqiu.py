"""Xueqiu (雪球) collector — hot timeline + KOL feeds."""

import html
import logging
import re
import time
from datetime import datetime
from typing import Any

import requests

from collectors.base import BaseCollector
from config import XUEQIU_COOKIE, XUEQIU_KOL_IDS

logger = logging.getLogger(__name__)

_BASE_URL = "https://xueqiu.com"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://xueqiu.com/",
}

# Category IDs for public_timeline_by_category
_CATEGORIES = {
    "hot": 111,      # 热门
    "stocks": 114,   # 股票
}


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _ms_to_datetime(ms: int | None) -> datetime | None:
    """Convert millisecond timestamp to datetime."""
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000)
    except (ValueError, OSError):
        return None


class XueqiuCollector(BaseCollector):
    """Collect posts from Xueqiu (雪球)."""

    source = "xueqiu"

    def __init__(self) -> None:
        super().__init__()
        self._session = requests.Session()
        self._session.headers.update(_HEADERS)
        if XUEQIU_COOKIE:
            self._session.headers["Cookie"] = XUEQIU_COOKIE
        else:
            # Visit homepage to get session cookie
            try:
                self._session.get(_BASE_URL, timeout=10)
            except requests.RequestException:
                logger.warning("Failed to initialize Xueqiu session")

    def _fetch_timeline(self, category_id: int, count: int = 20) -> list[dict[str, Any]]:
        """Fetch public timeline by category."""
        url = f"{_BASE_URL}/v4/statuses/public_timeline_by_category.json"
        params = {"since_id": -1, "max_id": -1, "count": count, "category": category_id}

        try:
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Xueqiu timeline request failed: %s", e)
            return []
        except ValueError:
            logger.error("Xueqiu timeline returned non-JSON response")
            return []

        articles: list[dict[str, Any]] = []
        for item in data.get("list", []):
            article = self._parse_status(item)
            if article:
                articles.append(article)

        return articles

    def _fetch_user_timeline(
        self,
        user_id: str,
        count: int = 10,
        kol_tag: str | None = None,
        kol_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch a user's timeline."""
        url = f"{_BASE_URL}/v4/statuses/user_timeline.json"
        params = {"user_id": user_id, "page": 1, "count": count}

        try:
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error("Xueqiu user timeline failed for %s: %s", user_id, e)
            return []
        except ValueError:
            logger.error("Xueqiu user timeline returned non-JSON for %s", user_id)
            return []

        articles: list[dict[str, Any]] = []
        for item in data.get("statuses", data.get("list", [])):
            article = self._parse_status(item)
            if article:
                if kol_tag and kol_tag not in article["tags"]:
                    article["tags"].append(kol_tag)
                articles.append(article)

        return articles

    def _parse_status(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a Xueqiu status into an article dict."""
        post_id = item.get("id")
        if not post_id:
            return None

        user = item.get("user", {}) or {}
        author = user.get("screen_name", "")
        text = item.get("text", "") or ""
        text = _strip_html(text)

        if not text:
            return None

        title = item.get("title") or ""
        if not title:
            # Use first 100 chars of content as title
            title = text[:100]

        return {
            "source": self.source,
            "source_id": f"xueqiu_{post_id}",
            "author": author,
            "title": title,
            "content": text,
            "url": f"https://xueqiu.com/{user.get('id', '')}/{post_id}",
            "tags": [],
            "score": item.get("reply_count", 0) or 0,
            "published_at": _ms_to_datetime(item.get("created_at")),
        }

    def collect(self) -> list[dict[str, Any]]:
        """Collect from hot timelines + KOL feeds."""
        all_articles: list[dict[str, Any]] = []

        # 1. Hot timelines
        for name, cat_id in _CATEGORIES.items():
            logger.info("Fetching Xueqiu %s timeline", name)
            articles = self._fetch_timeline(cat_id)
            all_articles.extend(articles)
            logger.info("Got %d posts from Xueqiu %s", len(articles), name)
            time.sleep(1)  # Be polite

        # 2. KOL feeds
        for kol in XUEQIU_KOL_IDS:
            kol_id, kol_name, kol_tag = kol["id"], kol["name"], kol["tag"]
            logger.info("Fetching Xueqiu KOL %s (%s)", kol_name, kol_id)
            articles = self._fetch_user_timeline(kol_id, kol_tag=kol_tag, kol_name=kol_name)
            all_articles.extend(articles)
            logger.info("Got %d posts from KOL %s", len(articles), kol_name)
            time.sleep(2)

        return all_articles
