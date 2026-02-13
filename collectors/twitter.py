"""Twitter collector using the bird CLI — account-based (38 followed accounts only)."""

import json
import logging
import shutil
import subprocess
from datetime import datetime
from typing import Any

from collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Followed accounts — ONLY these 38 accounts, no timeline
FOLLOWED_ACCOUNTS = [
    # Global KOL
    "elonmusk",
    "realDonaldTrump",
    "sama",
    "pmarca",
    "naval",
    "VitalikButerin",
    "CathieDWood",
    "chamath",
    "balajis",
    "APompliano",
    "raydalio",
    "garrytan",
    # Original 4
    "xiaomucrypto",
    "coolish",
    "ohxiyu",
    "billtheinvestor",
    # Obsidian people (relevance-scored)
    "zhixianio",
    "steipete",
    "vista8",
    "RohOnChain",
    "wshuyi",
    "canghe",
    "dontbesilent12",
    "xmayeth",
    "thedankoe",
    # Obsidian article URLs (high frequency)
    "Voxyz_ai",
    "oran_ge",
    "lyzdenda",
    "seekjourney",
    "Roland_WayneOZ",
    "Mikocrypto11",
    "DavidOndrej1",
    "Bitturing",
    "yan5xu",
    "Jason_Young1231",
    "Khazix0918",
    "xxx111god",
    "w9Pe0jaVWltmZEM",
]
TWEETS_PER_ACCOUNT = 10


class TwitterCollector(BaseCollector):
    """Collect tweets from X home timeline using bird CLI."""

    source = "twitter"

    def __init__(self) -> None:
        super().__init__()
        self._bird_path = shutil.which("bird") or shutil.which("bird", path="/opt/homebrew/bin:/usr/local/bin")
        if not self._bird_path:
            logger.warning("bird CLI not found — Twitter collector will return empty results")

    def _fetch_timeline(self) -> list[dict[str, Any]]:
        """Fetch For You timeline via bird home."""
        try:
            result = subprocess.run(
                [self._bird_path, "home", "-n", str(TIMELINE_COUNT), "--json"],
                capture_output=True,
                timeout=120,
            )
            result.stdout = result.stdout.decode("utf-8", errors="replace")
            result.stderr = result.stderr.decode("utf-8", errors="replace")
            if result.returncode != 0:
                logger.warning("bird home failed: %s", result.stderr.strip())
                return []

            tweets = json.loads(result.stdout) if result.stdout.strip() else []
            if isinstance(tweets, dict):
                tweets = tweets.get("data", tweets.get("tweets", [tweets]))

            articles: list[dict[str, Any]] = []
            for tweet in tweets:
                tweet_id = str(tweet.get("id", tweet.get("id_str", "")))
                text = tweet.get("text", tweet.get("full_text", ""))
                author = (
                    tweet.get("author", {}).get("username")
                    or tweet.get("user", {}).get("screen_name")
                    or tweet.get("username", "unknown")
                )
                created = tweet.get("created_at")

                published_at = None
                if created:
                    try:
                        published_at = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
                    except (ValueError, TypeError):
                        try:
                            published_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass

                articles.append({
                    "source": self.source,
                    "source_id": f"tweet_{tweet_id}",
                    "author": author,
                    "title": None,
                    "content": text,
                    "url": f"https://x.com/{author}/status/{tweet_id}",
                    "tags": [],
                    "score": tweet.get("favorite_count", tweet.get("like_count", 0)) or 0,
                    "published_at": published_at,
                })

            return articles

        except subprocess.TimeoutExpired:
            logger.warning("bird home timed out")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse bird home output: %s", e)
            return []

    def _fetch_account(self, account: str) -> list[dict[str, Any]]:
        """Fetch latest tweets from a specific account."""
        try:
            result = subprocess.run(
                [self._bird_path, "user-tweets", account, "-n", str(TWEETS_PER_ACCOUNT), "--json"],
                capture_output=True,
                timeout=30,
            )
            result.stdout = result.stdout.decode("utf-8", errors="replace")
            result.stderr = result.stderr.decode("utf-8", errors="replace")
            if result.returncode != 0:
                logger.warning("bird user-tweets failed for @%s: %s", account, result.stderr.strip())
                return []

            tweets = json.loads(result.stdout) if result.stdout.strip() else []
            if isinstance(tweets, dict):
                tweets = tweets.get("data", tweets.get("tweets", [tweets]))

            articles: list[dict[str, Any]] = []
            for tweet in tweets:
                tweet_id = str(tweet.get("id", tweet.get("id_str", "")))
                text = tweet.get("text", tweet.get("full_text", ""))
                created = tweet.get("created_at")

                published_at = None
                if created:
                    try:
                        published_at = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
                    except (ValueError, TypeError):
                        try:
                            published_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass

                articles.append({
                    "source": self.source,
                    "source_id": f"tweet_{tweet_id}",
                    "author": account,
                    "title": None,
                    "content": text,
                    "url": f"https://x.com/{account}/status/{tweet_id}",
                    "tags": ["pinned"],
                    "score": tweet.get("favorite_count", tweet.get("like_count", 0)) or 0,
                    "published_at": published_at,
                })
            return articles

        except subprocess.TimeoutExpired:
            logger.warning("bird user-tweets timed out for @%s", account)
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse bird output for @%s: %s", account, e)
            return []

    def collect(self) -> list[dict[str, Any]]:
        """Collect tweets from followed accounts only (no timeline)."""
        if not self._bird_path:
            logger.info("bird CLI not available — skipping Twitter collection")
            return []

        all_articles: list[dict[str, Any]] = []

        for account in FOLLOWED_ACCOUNTS:
            logger.info("Fetching @%s", account)
            articles = self._fetch_account(account)
            all_articles.extend(articles)
            logger.info("Got %d tweets from @%s", len(articles), account)

        return all_articles
