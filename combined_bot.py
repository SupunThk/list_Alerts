"""
combined_bot.py — Runs BOTH bots simultaneously in parallel threads.

  Thread 1 — Market Watcher  (bot.py)
    → Polls Upbit live API every 30s
    → Alerts the SECOND a new market goes live

  Thread 2 — News Scraper    (news_bot.py)
    → Scrapes Upbit notice board every 60s
    → Uses NVIDIA NIM (Llama 3.3 70B) to classify notices
    → Alerts 30–90 min BEFORE trading opens

Both threads send to the same Telegram bot/chat.
"""

import threading
import logging
import sys
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

import bot
import news_bot


def run_market_watcher():
    try:
        bot.main()
    except Exception as e:
        log.critical(f"Market watcher crashed: {e}")
        sys.exit(1)


def run_news_scraper():
    try:
        news_bot.main()
    except Exception as e:
        log.critical(f"News scraper crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    log.info("=" * 55)
    log.info("  Upbit Combined Bot starting...")
    log.info("  Thread 1 → Market Watcher  (API, every 30s)")
    log.info("  Thread 2 → News Scraper    (NIM, every 60s)")
    log.info("=" * 55)

    t1 = threading.Thread(target=run_market_watcher, name="MarketWatcher", daemon=True)
    t2 = threading.Thread(target=run_news_scraper,   name="NewsScraper",   daemon=True)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
