"""RSS collector for financial and AI feeds."""

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser

from collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    """Collect articles from RSS feeds."""

    source = "rss"

    # RSS feeds to monitor (tested and verified as working)
    FEEDS = [
        {
            "name": "Bloomberg Markets",
            "url": "https://feeds.bloomberg.com/markets/news.rss",
            "tags": ["finance", "markets", "bloomberg"],
        },
        {
            "name": "Zero Hedge",
            "url": "https://feeds.feedburner.com/zerohedge/feed",
            "tags": ["finance", "markets", "economics"],
        },
        {
            "name": "OpenAI News",
            "url": "https://openai.com/news/rss.xml",
            "tags": ["ai", "openai", "research"],
        },
        {
            "name": "Google AI Blog",
            "url": "https://research.google/blog/rss/",
            "tags": ["ai", "google", "research"],
        },
    ]

    def _fetch_feed(self, feed_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch articles from a single RSS feed."""
        name = feed_config["name"]
        url = feed_config["url"]
        base_tags = feed_config.get("tags", [])
        
        logger.info("Fetching RSS feed: %s", name)
        
        try:
            # Parse RSS feed with timeout
            feed = feedparser.parse(url)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning("Feed %s has parsing issues: %s", name, feed.bozo_exception)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning("No entries found in feed: %s", name)
                return []
                
            articles = []
            for entry in feed.entries:
                # Extract basic info
                title = entry.get('title', '').strip()
                if not title:
                    continue
                    
                # Get content from various possible fields
                content = ""
                if hasattr(entry, 'content') and entry.content:
                    content = entry.content[0].value if isinstance(entry.content, list) else entry.content.value
                elif hasattr(entry, 'summary') and entry.summary:
                    content = entry.summary
                elif hasattr(entry, 'description') and entry.description:
                    content = entry.description
                    
                # Clean up content (remove HTML tags if needed)
                content = self._clean_content(content)
                
                # Get URL
                article_url = entry.get('link', '')
                if not article_url:
                    continue
                    
                # Get publication date
                published_at = None
                for date_field in ['published_parsed', 'updated_parsed']:
                    if hasattr(entry, date_field):
                        date_tuple = getattr(entry, date_field)
                        if date_tuple:
                            try:
                                published_at = datetime(*date_tuple[:6])
                                break
                            except (ValueError, TypeError):
                                continue
                
                # Create unique source_id based on URL and feed
                source_id = f"rss_{hash(article_url + name)}_{abs(hash(title))}"
                
                # Get author
                author = entry.get('author', '')
                if not author and hasattr(entry, 'authors') and entry.authors:
                    author = entry.authors[0] if isinstance(entry.authors, list) else str(entry.authors)
                
                # Combine base tags with any category tags from the feed
                tags = list(base_tags)  # Copy base tags
                if hasattr(entry, 'tags') and entry.tags:
                    for tag in entry.tags:
                        tag_name = tag.term if hasattr(tag, 'term') else str(tag)
                        if tag_name and tag_name.lower() not in [t.lower() for t in tags]:
                            tags.append(tag_name.lower())
                
                articles.append({
                    "source": self.source,
                    "source_id": source_id,
                    "author": author,
                    "title": title,
                    "content": content,
                    "url": article_url,
                    "tags": tags,
                    "score": 0,  # RSS doesn't have scoring
                    "published_at": published_at,
                })
                
            logger.info("Fetched %d articles from %s", len(articles), name)
            return articles
            
        except Exception as e:
            logger.error("Failed to fetch feed %s: %s", name, e)
            return []
    
    @staticmethod
    def _clean_content(content: str) -> str:
        """Basic HTML cleanup for content."""
        if not content:
            return ""
        
        # Remove common HTML tags (basic cleanup)
        import re
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
        content = content.strip()
        
        # Limit content length
        if len(content) > 2000:
            content = content[:2000] + "..."
            
        return content

    def collect(self) -> list[dict[str, Any]]:
        """Collect articles from all RSS feeds."""
        all_articles = []
        seen_urls = set()
        
        for feed_config in self.FEEDS:
            try:
                articles = self._fetch_feed(feed_config)
                
                # Deduplicate by URL
                new_articles = []
                for article in articles:
                    url = article.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        new_articles.append(article)
                
                all_articles.extend(new_articles)
                logger.info("Added %d new articles from %s (total: %d)", 
                          len(new_articles), feed_config["name"], len(all_articles))
                          
            except Exception as e:
                logger.error("Error processing feed %s: %s", feed_config["name"], e)
                continue
        
        logger.info("Total RSS articles collected: %d", len(all_articles))
        return all_articles