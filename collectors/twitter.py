"""Twitter collector using the bird CLI."""

import json
import logging
import shutil
import subprocess
from datetime import datetime
from typing import Any

from collectors.base import BaseCollector
from config import TWITTER_ACCOUNTS, TWITTER_MAX_TWEETS_PER_ACCOUNT

logger = logging.getLogger(__name__)


class TwitterCollector(BaseCollector):
    """Collect tweets using the bird CLI tool."""

    source = "twitter"

    def __init__(self) -> None:
        super().__init__()
        self._bird_path = shutil.which("bird")
        if not self._bird_path:
            logger.warning("bird CLI not found — Twitter collector will return empty results")

    def _fetch_via_bird(self, account: str) -> list[dict[str, Any]]:
        """Fetch tweets for a single account using bird CLI."""
        try:
            result = subprocess.run(
                [self._bird_path, "search", f"from:{account}", "--count", str(TWITTER_MAX_TWEETS_PER_ACCOUNT), "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("bird CLI failed for @%s: %s", account, result.stderr.strip())
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
                    "tags": [],
                    "score": tweet.get("favorite_count", tweet.get("like_count", 0)) or 0,
                    "published_at": published_at,
                })
            return articles

        except subprocess.TimeoutExpired:
            logger.warning("bird CLI timed out for @%s", account)
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse bird output for @%s: %s", account, e)
            return []

    def collect(self) -> list[dict[str, Any]]:
        """Collect tweets from all configured accounts."""
        if not self._bird_path:
            logger.info("bird CLI not available — skipping Twitter collection")
            return []

        all_articles: list[dict[str, Any]] = []
        for account in TWITTER_ACCOUNTS:
            logger.info("Fetching tweets from @%s", account)
            articles = self._fetch_via_bird(account)
            all_articles.extend(articles)
            logger.info("Got %d tweets from @%s", len(articles), account)

        return all_articles
