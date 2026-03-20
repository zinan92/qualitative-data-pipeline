#!/usr/bin/env python3
"""
Qualitative synthesis script.
Fetches scored articles from park-intel, runs Opus analysis, sends to Telegram.

Pipeline: prefilter.py → run_llm_tagger.py → synthesis.py
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime

PARK_INTEL_BASE = "http://127.0.0.1:8001"
TELEGRAM_BOT_TOKEN = "8536226541:AAEqVQowK9RaE0Z9Mj46xPO5-VjCXWxNkdw"
TELEGRAM_CHAT_ID = "-1003709460418"
TELEGRAM_THREAD_ID = "1446"
OBSIDIAN_DIR = os.path.expanduser("~/knowledge-base/trading/daily")
QUALITATIVE_PROMPT_PATH = os.path.expanduser(
    "~/work/dev-co/wendy/prompts/QUALITATIVE_PROMPT.md"
)
TRADING_DAY_SCRIPT = os.path.expanduser(
    "~/work/trading-co/ashare/scripts/is_trading_day.py"
)


def fetch(path):
    url = f"{PARK_INTEL_BASE}{path}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "message_thread_id": int(TELEGRAM_THREAD_ID),
        "text": text,
    }).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def run_claude(prompt, model="claude-opus-4-6"):
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", model],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")
    return result.stdout.strip()


def main():
    # Check trading day
    r = subprocess.run(["python3", TRADING_DAY_SCRIPT], capture_output=True)
    if r.returncode != 0:
        print("非交易日，跳过")
        sys.exit(0)

    # Load QUALITATIVE_PROMPT.md framework
    with open(QUALITATIVE_PROMPT_PATH) as f:
        qual_framework = f.read()

    # Fetch data
    print("Fetching signals...")
    signals = fetch("/api/articles/signals")

    print("Fetching articles...")
    all_articles = fetch("/api/articles/latest?limit=200")

    # Filter by relevance_score if available, else use all
    scored = [a for a in all_articles if (a.get("relevance_score") or 0) >= 2]
    if len(scored) < 10:
        # Tagger hasn't run yet — fall back to all articles
        print(f"Warning: only {len(scored)} scored articles, using all {len(all_articles)}")
        articles = all_articles[:100]
        has_scores = False
    else:
        articles = scored
        has_scores = True

    # Build article summary for prompt
    high = []   # score >= 4
    mid = []    # score 2-3
    unscored = []

    for a in articles:
        score = a.get("relevance_score") or 0
        title = a.get("title", "")
        source = a.get("source", "")
        content = (a.get("content") or "")[:300]
        tags = ", ".join(a.get("tags") or [])
        ntags = ", ".join(a.get("narrative_tags") or [])
        line = f"[{source}][score={score}] {title} | tags: {tags} | narrative: {ntags} | {content}"

        if score >= 4:
            high.append(line)
        elif score >= 2:
            mid.append(line)
        else:
            unscored.append(line)

    # Topic heat
    heat_lines = []
    for t in (signals.get("topic_heat") or [])[:15]:
        heat_lines.append(f"  {t['tag']}: {t['current_count']} ({t['momentum_label']})")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    hour = datetime.now().hour
    if hour < 10:
        slot = "早间"
    elif hour < 15:
        slot = "午间"
    else:
        slot = "晚间"

    scored_note = f"（已打分，{len(high)} 篇高分 + {len(mid)} 篇中分）" if has_scores else f"（未打分，共 {len(unscored)} 篇原始文章）"

    article_block = ""
    if high:
        article_block += "\n=== 高分文章（score ≥4）===\n" + "\n".join(high[:30])
    if mid:
        article_block += "\n\n=== 中分文章（score 2-3）===\n" + "\n".join(mid[:40])
    if not high and not mid:
        article_block = "\n=== 文章（未打分）===\n" + "\n".join(unscored[:60])

    prompt = f"""你是一位专注于 A 股和宏观市场的 narrative 分析师。
时间：{now} {slot}
文章数量：{scored_note}

请严格按照以下框架做分析：

=== 分析框架 ===
{qual_framework}

=== Topic Heat（过去24h）===
{chr(10).join(heat_lines)}

{article_block}

请按框架中的 Output Template 输出，中文，纯文本（不要 markdown 代码块）。
如果无高分信号，输出"本轮无 A+ 信号。"
"""

    print(f"Running Opus analysis ({len(articles)} articles)...")
    analysis = run_claude(prompt, model="claude-opus-4-6")

    # Send to Telegram (split at 4000 chars)
    MAX_LEN = 4000
    if len(analysis) <= MAX_LEN:
        send_telegram(analysis)
    else:
        chunks = []
        current = ""
        for line in analysis.split("\n"):
            if len(current) + len(line) + 1 > MAX_LEN:
                chunks.append(current)
                current = line
            else:
                current += ("\n" if current else "") + line
        if current:
            chunks.append(current)
        for chunk in chunks:
            send_telegram(chunk)

    print(f"Sent to Telegram ({len(analysis)} chars)")

    # Save to Obsidian
    os.makedirs(OBSIDIAN_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    obs_path = os.path.join(OBSIDIAN_DIR, f"{date_str}.md")
    header = f"\n\n## {datetime.now().strftime('%H:%M')} {slot}合成\n\n"
    with open(obs_path, "a") as f:
        f.write(header + analysis + "\n")
    print(f"Saved to {obs_path}")


if __name__ == "__main__":
    main()
