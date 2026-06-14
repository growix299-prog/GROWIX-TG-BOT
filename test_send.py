import os
import sys
import asyncio
import logging

# Setup path so we can import backend packages
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load .env file from root directory
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

import httpx

BOT_TOKEN = os.getenv("BOT_TOKEN")
chat_id = 8043402764

async def main():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Let's test sending the exact message structure
    msg = (
        f"🎉 <b>WALLET PAYMENT SUCCESSFUL!</b> 🎉\n\n"
        f"Thank you for purchasing <b>1x YouTube Premium (1 Month)</b>!\n"
        f"💰 <b>Amount Paid:</b> ₹15.00 (from Wallet)\n"
        f"👛 <b>Remaining Balance:</b> ₹100.00\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"✨ <b>YOUR LOGIN CREDENTIALS</b> <tg-emoji emoji-id=\"5343553259971822765\">🚀</tg-emoji>\n\n"
        f"<b>ACCOUNT 1</b> <tg-emoji emoji-id=\"5427009714745517609\">🔑</tg-emoji>\n"
        f"👤 <b>Username:</b> <code>test_user</code>\n"
        f"🔒 <b>Password:</b> <code>test_pass</code>\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"<tg-emoji emoji-id=\"5463139369978174548\">⚠️</tg-emoji> <i>Please change the credentials after logging in to secure your accounts. Enjoy!</i>\n\n"
        f"📧 <b>Want credentials on Email?</b>\n"
        f"<i>Type your email address in this chat right now to receive them via email, or tap Skip!</i>\n"
    )
    
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "⏭️ Skip — No Email Needed", "callback_data": "skip_email"}],
                [{"text": "🏠 Main Menu", "callback_data": "main_menu"}]
            ]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10.0)
        print("Status code:", response.status_code)
        print("Response:", response.text)

if __name__ == "__main__":
    asyncio.run(main())
