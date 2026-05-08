import os
import json
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials missing in .env")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        r.raise_for_status()
        print("✅ Telegram alert sent!")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def simulate_market_alert():
    print("\n--- 🟢 Simulating Market Watcher Alert (bot.py) ---")
    mock_market = {
        "market": "KRW-GEMINI",
        "korean_name": "제미니",
        "english_name": "Gemini"
    }
    
    from bot import build_alert
    alert_msg = build_alert(mock_market)
    print(f"Generated Message:\n{alert_msg}")
    
    send_telegram(alert_msg)

def simulate_news_alert():
    print("\n--- 🟢 Simulating News Scraper Alert (news_bot.py) ---")
    mock_notice = {
        "id": "9999",
        "title": "[Listing] New Digital Asset Support: Gemini (GEMINI)",
        "url": "https://upbit.com/service_center/notice?id=9999"
    }
    
    # We mock fetch_notice_detail to avoid actual scraping for this test
    from news_bot import build_alert
    import news_bot
    
    # Monkeypatch fetch_notice_detail for the test
    original_detail = news_bot.fetch_notice_detail
    news_bot.fetch_notice_detail = lambda x: "GEMINI will be added to KRW/BTC/USDT markets."
    
    try:
        alert_msg = build_alert(mock_notice)
        print(f"Generated Message:\n{alert_msg}")
        send_telegram(alert_msg)
    finally:
        news_bot.fetch_notice_detail = original_detail

if __name__ == "__main__":
    print("🚀 Starting Bot Simulation Tests...")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in .env")
        exit(1)

    simulate_market_alert()
    time.sleep(2)  # Avoid rate limiting
    simulate_news_alert()
    
    print("\n✅ Simulation complete. Check your Telegram chat!")
