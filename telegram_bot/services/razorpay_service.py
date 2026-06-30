import os
import httpx
import logging
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

def _get_razorpay_keys():
    """Get Razorpay keys at call time (not import time) to ensure .env is loaded."""
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    return key_id, key_secret

def clean_customer_name(name: str) -> str:
    """Remove emojis and special characters from the customer name for Razorpay."""
    if not name:
        return "User"
    # Encode to ASCII, ignoring unsupported characters, then decode back
    clean = name.encode("ascii", "ignore").decode("ascii").strip()
    return clean if clean else "Telegram User"

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
    RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET = _get_razorpay_keys()
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        logger.error(f"RAZORPAY keys not configured! KEY_ID present: {bool(RAZORPAY_KEY_ID)}, SECRET present: {bool(RAZORPAY_KEY_SECRET)}")
        return {"success": False, "error": "Payment system not configured. Contact admin."}

    amount_in_paise = int(amount * 100)
    clean_name = clean_customer_name(first_name)

    url = "https://api.razorpay.com/v1/payment_links"
    
    # Payload format according to Razorpay API specs
    payload = {
        "amount": amount_in_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Purchase of {product_name} via Telegram Bot",
        "customer": {
            "name": clean_name,
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

async def create_deposit_payment_link(
    amount: float,
    telegram_id: int,
    first_name: str
) -> Dict[str, Any]:
    """
    Creates a Razorpay payment link specifically for wallet deposits.
    Tags the notes with type=wallet_deposit so the webhook knows to credit the wallet.
    """
    RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET = _get_razorpay_keys()
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        logger.error(f"RAZORPAY keys not configured! KEY_ID present: {bool(RAZORPAY_KEY_ID)}, SECRET present: {bool(RAZORPAY_KEY_SECRET)}")
        return {"success": False, "error": "Payment system not configured. Contact admin."}

    amount_in_paise = int(amount * 100)
    clean_name = clean_customer_name(first_name)

    url = "https://api.razorpay.com/v1/payment_links"

    payload = {
        "amount": amount_in_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"Wallet Deposit of ₹{amount:.2f}",
        "customer": {
            "name": clean_name,
            "contact": "+919876543210"
        },
        "notify": {
            "sms": False,
            "email": False
        },
        "notes": {
            "type": "wallet_deposit",
            "telegram_id": str(telegram_id),
            "amount": str(amount)
        },
        "callback_url": f"https://t.me/{os.getenv('TELEGRAM_BOT_USERNAME', 'FlashKeysS_Bot')}",
        "callback_method": "get"
    }

    try:
        auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        async with httpx.AsyncClient() as client:
            response = await client.post(url, auth=auth, json=payload, timeout=12.0)

            if response.status_code in (200, 201):
                res_data = response.json()
                logger.info(f"Razorpay Wallet Deposit Link generated: {res_data.get('id')}")
                return {
                    "success": True,
                    "payment_link_id": res_data.get("id"),
                    "short_url": res_data.get("short_url")
                }
            else:
                logger.error(f"Razorpay API Error (deposit): {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}

    except Exception as e:
        logger.error(f"Exception while creating deposit link: {str(e)}")
        return {"success": False, "error": str(e)}
