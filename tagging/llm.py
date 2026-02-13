"""LLM-based article tagger using Claude for relevance scoring and narrative tagging."""

import json
import logging
import time
from typing import Any

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a trading analyst assistant. For each article, you must:

1. Rate its **relevance_score** (1-5) for an active multi-market trader:
   - 5: Directly actionable — earnings surprise, policy change, major breakout
   - 4: High relevance — sector trend, significant macro data, important KOL thesis
   - 3: Moderate — general market commentary, industry news
   - 2: Low — tangentially related to markets
   - 1: Noise — not useful for trading decisions

2. Generate **narrative_tags** — short descriptive phrases (2-4 words each) capturing the article's trading-relevant narrative. Examples: "nvidia-earnings-beat", "fed-rate-pause", "btc-etf-inflows", "china-stimulus-hope".

Respond with a JSON array. Each element must have:
- "id": the article id (integer)
- "relevance_score": integer 1-5
- "narrative_tags": list of 1-3 short narrative tag strings

Example response:
[
  {"id": 1, "relevance_score": 4, "narrative_tags": ["nvidia-earnings-beat", "ai-capex-growth"]},
  {"id": 2, "relevance_score": 2, "narrative_tags": ["general-market-commentary"]}
]

Respond ONLY with the JSON array, no other text."""

# Rate limit: 40 RPM → 1.5s between calls
_MIN_INTERVAL = 1.5


class LLMTagger:
    """Batch LLM tagger using Claude Sonnet."""

    def __init__(self, batch_size: int = 10, daily_budget: float = 5.0) -> None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.batch_size = batch_size
        self.daily_budget = daily_budget
        self._last_call = 0.0
        self._session_cost = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        self._last_call = time.time()

    def tag_batch(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Tag a batch of articles. Each dict needs 'id', 'title', 'content'.

        Returns list of {"id": int, "relevance_score": int, "narrative_tags": list[str]}.
        """
        if not articles:
            return []

        if self._session_cost >= self.daily_budget:
            logger.warning("Daily budget ($%.2f) reached, skipping batch", self.daily_budget)
            return []

        # Build user message with articles
        parts = []
        for a in articles:
            title = a.get("title") or "(no title)"
            content = (a.get("content") or "")[:1000]
            source = a.get("source", "unknown")
            parts.append(f"[Article ID={a['id']}, source={source}]\nTitle: {title}\nContent: {content}\n")

        user_msg = "\n---\n".join(parts)

        self._rate_limit()
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )

            # Track cost estimate (Sonnet: ~$3/M input, ~$15/M output)
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens * 3 + output_tokens * 15) / 1_000_000
            self._session_cost += cost
            logger.debug("Batch cost: $%.4f (session total: $%.4f)", cost, self._session_cost)

            # Parse response
            text = response.content[0].text.strip()
            # Handle markdown code blocks
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            results = json.loads(text)

            # Validate
            valid = []
            for r in results:
                if isinstance(r, dict) and "id" in r and "relevance_score" in r:
                    score = r["relevance_score"]
                    if isinstance(score, int) and 1 <= score <= 5:
                        tags = r.get("narrative_tags", [])
                        if isinstance(tags, list):
                            valid.append({
                                "id": r["id"],
                                "relevance_score": score,
                                "narrative_tags": [str(t) for t in tags[:5]],
                            })
            return valid

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response: %s", e)
            return []
        except Exception as e:
            logger.error("LLM API call failed: %s", e)
            return []

    @property
    def session_cost(self) -> float:
        return self._session_cost
