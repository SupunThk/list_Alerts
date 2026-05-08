import os
import time
import requests
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load .env file if it exists (for local development)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
POLL_INTERVAL      = int(os.getenv("MARKET_POLL_INTERVAL", "30"))
STORAGE_FILE       = "known_markets.json"

UPBIT_MARKETS_URL  = "https://api.upbit.com/v1/market/all?isDetails=false"
UPBIT_TRADE_URL    = "https://upbit.com/exchange?code=CRIX.UPBIT.{market}"
HEADERS            = {"Accept": "application/json"}


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Telegram error: {e}")


def fetch_markets() -> list[dict]:
    try:
        r = requests.get(UPBIT_MARKETS_URL, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Failed to fetch markets: {e}")
        return []


def load_known_markets() -> set:
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE) as f:
            return set(json.load(f))
    return set()


def save_known_markets(markets: set):
    with open(STORAGE_FILE, "w") as f:
        json.dump(list(markets), f)


def build_alert(market_info: dict) -> str:
    market   = market_info["market"]
    eng_name = market_info.get("english_name", "Unknown")
    kor_name = market_info.get("korean_name", "")
    _, base  = market.split("-", 1)
    now      = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"🚨 <b>NEW UPBIT LISTING DETECTED!</b>\n\n"
        f"🪙 <b>Token:</b> {base} ({eng_name})\n"
        f"🇰🇷 Korean name: {kor_name}\n"
        f"📊 <b>Pair:</b> {market}\n"
        f"🕒 <b>Detected at:</b> {now}\n\n"
        f"👉 <a href='{UPBIT_TRADE_URL.format(market=market)}'>Trade on Upbit</a>"
    )


def main():
    log.info("🚨 Market watcher starting...")
    known = load_known_markets()

    if not known:
        log.info("Seeding market list...")
        data = fetch_markets()
        if data:
            known = {m["market"] for m in data}
            save_known_markets(known)
            log.info(f"Seeded {len(known)} markets.")
            send_telegram(
                f"✅ <b>Market Watcher is LIVE!</b>\n"
                f"Tracking <b>{len(known)}</b> markets. "
                f"Polling every <b>{POLL_INTERVAL}s</b>. 🚀"
            )
    else:
        log.info(f"Loaded {len(known)} known markets.")

    while True:
        time.sleep(POLL_INTERVAL)
        data = fetch_markets()
        if not data:
            log.warning("Empty response — skipping cycle.")
            continue

        current      = {m["market"]: m for m in data}
        new_listings = set(current.keys()) - known

        if new_listings:
            log.info(f"🎉 {len(new_listings)} new listing(s): {new_listings}")
            for key in sorted(new_listings):
                send_telegram(build_alert(current[key]))
            known = set(current.keys())
            save_known_markets(known)
        else:
            log.info(f"No new listings. Tracking {len(known)} markets.")


if __name__ == "__main__":
    main()
