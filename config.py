"""park-intel configuration."""

from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "park_intel.db"

# --- API ---
API_HOST = "127.0.0.1"
API_PORT = 8001

# --- Collector: Twitter ---
TWITTER_ACCOUNTS: list[str] = [
    "xiaomucrypto",
    "coolish",
    "ohxiyu",
    "billtheinvestor",
]
TWITTER_MAX_TWEETS_PER_ACCOUNT: int = 20

# --- Collector: Hacker News ---
HN_API_BASE = "https://hn.algolia.com/api/v1"
HN_MIN_SCORE: int = 50
HN_HITS_PER_PAGE: int = 50
HN_SEARCH_KEYWORDS: list[str] = ["crypto", "AI", "trading"]

# --- Collector: Substack ---
SUBSTACK_FEEDS: dict[str, str] = {
    "The Pomp Letter": "https://pomp.substack.com/feed",
    "Doomberg": "https://doomberg.substack.com/feed",
    "One Useful Thing": "https://www.oneusefulthing.org/feed",
    "AI Supremacy": "https://www.ai-supremacy.com/feed",
    "Interconnects": "https://www.interconnects.ai/feed",
    "Dwarkesh Patel": "https://www.dwarkeshpatel.com/feed",
    "SemiAnalysis": "https://semianalysis.substack.com/feed",
}
