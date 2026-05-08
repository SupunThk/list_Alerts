import os
import time
import json
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
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
NVIDIA_API_KEY     = os.environ["NVIDIA_API_KEY"]
POLL_INTERVAL      = int(os.getenv("NEWS_POLL_INTERVAL", "60"))
STORAGE_FILE       = "seen_notices.json"

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL    = "meta/llama-3.3-70b-instruct"

NOTICE_URL  = "https://upbit.com/service_center/notice?code=LIST"
NOTICE_BASE = "https://upbit.com/service_center/notice?id={id}"

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def load_seen() -> set:
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    with open(STORAGE_FILE, "w") as f:
        json.dump(list(seen), f)


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Telegram error: {e}")


def is_listing_notice(title: str) -> bool:
    prompt = f"""You are a crypto exchange notice classifier.

Upbit is a South Korean cryptocurrency exchange. They post notices for:
- New token listings (NEW trading support added)
- Delistings (trading support ending)
- Caution/warning notices
- System/policy updates

Classify this Upbit notice title. Reply with ONLY the word YES or NO.

YES = This notice is announcing a brand new token/coin being LISTED (added) for trading.
NO  = This is anything else (delisting, warning, system notice, policy change, etc.)

Notice title: "{title}"

Answer (YES or NO only):"""

    try:
        r = requests.post(
            f"{NIM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": NIM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 5,
                "temperature": 0,
            },
            timeout=15,
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"].strip().upper()
        log.info(f"NIM: '{title[:55]}...' → {answer}")
        return answer.startswith("YES")
    except Exception as e:
        log.error(f"NIM failed: {e} — using keyword fallback")
        return _keyword_fallback(title)


def _keyword_fallback(title: str) -> bool:
    lower = title.lower()
    bad  = ["delist", "termination", "caution", "warning", "suspend", "종료", "유의"]
    good = ["new listing", "listing support", "market support", "trading support",
            "거래 지원 안내", "신규 상장", "will be listed"]
    if any(b in lower for b in bad):
        return False
    return any(g in lower for g in good)


def fetch_notices() -> list[dict]:
    try:
        r = requests.get(NOTICE_URL, headers=SCRAPE_HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Failed to fetch notices: {e}")
        return []

    soup     = BeautifulSoup(r.text, "html.parser")
    notices  = []
    seen_ids = set()

    for tag in soup.select("a[href*='notice?id=']"):
        href = tag.get("href", "")
        if "id=" not in href:
            continue
        try:
            notice_id = href.split("id=")[1].split("&")[0].strip()
        except Exception:
            continue

        title = tag.get_text(separator=" ", strip=True)
        if not title or notice_id in seen_ids:
            continue

        seen_ids.add(notice_id)
        notices.append({
            "id": notice_id,
            "title": title,
            "url": NOTICE_BASE.format(id=notice_id),
        })

    return notices


def fetch_notice_detail(notice_id: str) -> str:
    try:
        r = requests.get(NOTICE_BASE.format(id=notice_id), headers=SCRAPE_HEADERS, timeout=10)
        r.raise_for_status()
        soup    = BeautifulSoup(r.text, "html.parser")
        content = soup.select_one(".notice-content, .board-content, article, .content")
        if content:
            text = content.get_text(separator=" ", strip=True)
            return text[:300].strip() + ("..." if len(text) > 300 else "")
    except Exception:
        pass
    return ""


def build_alert(notice: dict) -> str:
    detail = fetch_notice_detail(notice["id"])
    now    = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        f"📢 <b>UPBIT LISTING NOTICE DETECTED!</b>\n\n"
        f"📌 <b>{notice['title']}</b>\n\n"
        f"🕒 Detected at: {now}\n"
        f"🤖 Classified by: NVIDIA NIM ({NIM_MODEL})\n\n"
    )
    if detail:
        msg += f"📝 <i>{detail}</i>\n\n"
    msg += f"👉 <a href='{notice['url']}'>Read Full Notice on Upbit</a>"
    return msg


def main():
    log.info("📰 News scraper (NVIDIA NIM) starting...")
    seen = load_seen()

    if not seen:
        log.info("First run — seeding notices silently...")
        notices = fetch_notices()
        if notices:
            seen = {n["id"] for n in notices}
            save_seen(seen)
            log.info(f"Seeded {len(seen)} notices.")
            send_telegram(
                f"✅ <b>News Scraper is LIVE!</b>\n"
                f"🤖 Using NVIDIA NIM ({NIM_MODEL}).\n"
                f"Polling every <b>{POLL_INTERVAL}s</b>."
            )
        else:
            log.warning("Could not seed — will retry next cycle.")
    else:
        log.info(f"Loaded {len(seen)} seen notices.")

    while True:
        time.sleep(POLL_INTERVAL)
        log.info("Checking Upbit notice board...")

        notices   = fetch_notices()
        new_saved = False

        for notice in notices:
            if notice["id"] in seen:
                continue
            seen.add(notice["id"])
            if is_listing_notice(notice["title"]):
                log.info(f"🎉 Listing notice: {notice['title']}")
                send_telegram(build_alert(notice))
                new_saved = True
            else:
                log.info(f"Skipped: {notice['title'][:60]}")

        if new_saved:
            save_seen(seen)
        else:
            log.info("No new listing notices this cycle.")


if __name__ == "__main__":
    main()
