import os
import requests
from dotenv import load_dotenv

# Explicitly load .env file and check if it exists
env_found = load_dotenv()

def test_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found.")
        if not env_found:
            print("   👉 No .env file detected. Please create one based on .env.example")
        else:
            print("   👉 Check if they are correctly defined in your .env file.")
        return False

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        print(f"✅ Bot connected: {r.json()['result']['username']}")
        
        # Test sending a message
        msg_url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(msg_url, json={
            "chat_id": chat_id,
            "text": "🛠️ <b>Test Message</b>: Your bot environment is set up correctly!",
            "parse_mode": "HTML"
        })
        r.raise_for_status()
        print("✅ Test message sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False

def test_nvidia():
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("⚠️ Warning: NVIDIA_API_KEY not found. news_bot.py will use keyword fallback.")
        return True
    
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Say 'OK'"}],
        "max_tokens": 5
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        print("✅ NVIDIA NIM connection successful!")
        return True
    except Exception as e:
        print(f"❌ NVIDIA NIM Error: {e}")
        return False

if __name__ == "__main__":
    print("--- 🔍 Environment Check ---")
    tel_ok = test_telegram()
    nv_ok = test_nvidia()
    
    if tel_ok and nv_ok:
        print("\n🚀 All systems ready! You can run 'python combined_bot.py' now.")
    else:
        print("\n⚠️ Please fix the issues above before running the bot.")
