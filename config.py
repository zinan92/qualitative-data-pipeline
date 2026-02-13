"""park-intel configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# --- Paths ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "park_intel.db"

# --- API ---
API_HOST = "127.0.0.1"
API_PORT = 8001

# --- Collector: Twitter ---
# Now timeline-based (bird home), no fixed account list needed
TWITTER_TIMELINE_COUNT: int = 100

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

# --- Collector: YouTube ---
YOUTUBE_CHANNELS: dict[str, str] = {
    "Alex Finn": "UCfQNB91qRP_5ILeu_S_bSkg",
    "AI超元域": "UCIomFkAj4Vq_rGX2Jot7D8A",
    "Eric Tech": "UCOXRjenlq9PmlTqd_JhAbMQ",
    "Y Combinator": "UCcefcZRL2oaA_uBNeo5UOWg",
    "AI LABS": "UCelfWQr9sXVMTvBzviPGlFw",
    "Peter Yang": "UCnpBg7yqNauHtlNSpOl5-cg",
}

# --- Collector: Xueqiu ---
XUEQIU_COOKIE: str = os.getenv("XUEQIU_COOKIE", "")
XUEQIU_KOL_IDS: list[dict[str, str]] = [
    {"name": "不明真相的群众", "id": "1955602780", "tag": "macro"},
    {"name": "大道无形我有型", "id": "1247347556", "tag": "value"},
    {"name": "但斌", "id": "1102105103", "tag": "value"},
    {"name": "唐朝", "id": "8290096439", "tag": "value"},
    {"name": "DAVID自由之路", "id": "5819606767", "tag": "macro"},
    {"name": "释老毛", "id": "6146070786", "tag": "value"},
    {"name": "月风_投资笔记", "id": "8833808060", "tag": "macro"},
    {"name": "盛丰衍", "id": "2533840321", "tag": "trading"},
    {"name": "梁宏", "id": "9887656769", "tag": "value"},
    {"name": "坚信价值", "id": "4206051491", "tag": "value"},
    {"name": "望京博格", "id": "4579887327", "tag": "tech"},
    {"name": "呼伦少威", "id": "3755834159", "tag": "tech"},
    {"name": "ETF拯救世界", "id": "4776750571", "tag": "tech"},
    {"name": "紫葳侍郎", "id": "2289280338", "tag": "tech"},
    {"name": "超短线投机者", "id": "4792753218", "tag": "trading"},
    {"name": "追龙头", "id": "8425285191", "tag": "trading"},
    {"name": "陈达美股投资", "id": "9598793634", "tag": "us-stock"},
    {"name": "Ricky", "id": "6654628252", "tag": "us-stock"},
    {"name": "美股研究社", "id": "3582153332", "tag": "us-stock"},
    {"name": "仓又加错-刘成岗", "id": "1434679955", "tag": "us-stock"},
]

# --- LLM Tagging ---
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
