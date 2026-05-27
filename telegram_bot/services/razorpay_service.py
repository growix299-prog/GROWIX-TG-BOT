import os
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

async def create_payment_link(
    amount: float, 
    product_name: str, 
    telegram_id: int, 
    product_id: str,
    first_name: str
) -> Dict[str, Any]:
    """
    Creates a dynamic Razorpay payment link using LIVE keys.
    """
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        logger.error("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not configured!")
        return {"success": False, "error": "Payment system not configured. Contact admin."}

    amount_in_paise = int(amount * 100)

    url = "https://api.razorpay.com/v1/payment_links"
    
    # Payload format according to Razorpay API specs
    payload = {
        "amount": amount_in_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Purchase of {product_name} via Telegram Bot",
        "customer": {
            "name": first_name,
            "contact": "+919876543210" # Default placeholder for TG bot flow
        },
        "notify": {
            "sms": False,
            "email": False
        },
        "notes": {
            "telegram_id": str(telegram_id),
            "product_id": product_id
        },
        "callback_url": f"https://t.me/{os.getenv('TELEGRAM_BOT_USERNAME', 'FlashKeysS_Bot')}",
        "callback_method": "get"
    }

    try:
        # Construct Basic Auth
        auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, auth=auth, json=payload, timeout=12.0)
            
            if response.status_code in (200, 201):
                res_data = response.json()
                logger.info(f"Razorpay Payment Link generated: {res_data.get('id')}")
                return {
                    "success": True,
                    "payment_link_id": res_data.get("id"),
                    "short_url": res_data.get("short_url"),
                    "mock": False
                }
            else:
                logger.error(f"Razorpay API Error: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
    except Exception as e:
        logger.error(f"Exception while contacting Razorpay API: {str(e)}")
        return {"success": False, "error": str(e)}
