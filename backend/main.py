import os
import hmac
import hashlib
import logging
import time
from collections import defaultdict
import httpx
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Load .env file from root directory
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from backend.services.supabase_service import (
    get_db,
    get_order_by_payment,
    update_order_completed,
    get_unused_credential,
    mark_credential_used,
    create_payment_record,
    create_ott_request
)
from backend.services.resend_service import send_delivery_email, send_credential_email, send_game_credential_email

# Set up Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TG Bot Digital Delivery Backend", docs_url=None, redoc_url=None)

# Restrict CORS to only your admin dashboard origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Razorpay-Signature", "X-Admin-API-Key"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
ADMIN_API_SECRET = os.getenv("ADMIN_API_SECRET", "nexus_admin_secret_key_2026_ultra_secure")

# Admin Telegram ID to notify on successful sales
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")

# ==========================================
# RATE LIMITING — Prevents brute force & DDoS
# ==========================================
rate_limit_store: Dict[str, list] = defaultdict(list)

def check_rate_limit(client_ip: str, max_requests: int = 30, window_seconds: int = 60):
    """Simple IP-based rate limiter. Raises 429 if limit exceeded."""
    now = time.time()
    # Clean old entries
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if now - t < window_seconds
    ]
    if len(rate_limit_store[client_ip]) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    rate_limit_store[client_ip].append(now)

def verify_admin_api_key(x_admin_api_key: Optional[str] = Header(None)):
    """Validates the admin API key from request headers."""
    if not x_admin_api_key or x_admin_api_key != ADMIN_API_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid or missing admin API key.")
    return True

async def send_telegram_message(chat_id: int, text: str, reply_markup: Optional[Dict] = None):
    """Utility to send telegram message to user using HTTP POST"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not configured. Cannot send Telegram message.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code != 200:
                logger.error(f"Failed to send Telegram message to {chat_id}: {response.text}")
    except Exception as e:
        logger.error(f"Error sending Telegram message to {chat_id}: {str(e)}")

async def notify_admin_on_sale(product_name: str, amount: float, category: str, order_id: str):
    """Notifies admin on Telegram about a new sale"""
    if ADMIN_TELEGRAM_ID:
        msg = (
            f"🔔 <b>NEW SALE NOTIFICATION</b> 🔔\n\n"
            f"📦 <b>Product:</b> {product_name}\n"
            f"🗂️ <b>Category:</b> {category}\n"
            f"💰 <b>Amount:</b> ₹{amount}\n"
            f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n\n"
            f"🚀 <i>The digital delivery system is processing the order.</i>"
        )
        await send_telegram_message(int(ADMIN_TELEGRAM_ID), msg)

async def process_digital_delivery(order_id: str, payment_id: str, amount: float, raw_payload: Dict[str, Any]):
    """Processes automated delivery based on product category"""
    logger.info(f"Initiating delivery process for order: {order_id}")
    
    # 1. Fetch Order details
    order = get_order_by_payment(order_id)
    if not order:
        # Fallback to check if order_id was sent as standard payment_id
        order = get_order_by_payment(payment_id)
        if not order:
            logger.error(f"Order not found for ID: {order_id} or Payment: {payment_id}")
            return
            
    product = order["products"]
    product_id = product["id"]
    product_name = product["name"]
    category = product["category"]
    telegram_id = order["telegram_id"]
    
    # 2. Log Raw Payment Record as verified
    create_payment_record(order_id, payment_id, amount, True, raw_payload)
    
    # 3. Dynamic Delivery
    # Extract customer email from Razorpay payment payload (if available)
    customer_email = None
    try:
        customer_email = raw_payload.get("payload", {}).get("payment", {}).get("entity", {}).get("email")
    except Exception:
        pass

    if category == "Games":
        # Ask for email before Automated Credential Dispatch
        update_order_completed(order["id"], "AWAITING_EMAIL_GAMES")
        msg = (
            f"🎉 <b>PAYMENT SUCCESSFUL!</b> 🎉\n\n"
            f"Thank you for purchasing <b>{product_name}</b>!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 <b>NEXT STEP — SEND YOUR EMAIL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"To receive your game credentials securely, "
            f"please <b>type and send your email address</b> in this chat right now.\n\n"
            f"Your login ID and password will be delivered here instantly and also sent to your email! 🚀"
        )
        await send_telegram_message(telegram_id, msg)
        logger.info(f"Games order set to AWAITING_EMAIL_GAMES, awaiting email from telegram_id {telegram_id}")
            
    elif category == "OTT":
        # OTT Manual Activation Flow — Always ask for email
        # Admin will activate from dashboard, then credentials are emailed to user
        update_order_completed(order["id"], "MANUAL_PROCESSING")
        msg = (
            f"🎉 <b>PAYMENT SUCCESSFUL!</b> 🎉\n\n"
            f"Thank you for purchasing <b>{product_name}</b>!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 <b>NEXT STEP — SEND YOUR EMAIL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"To activate your <b>{product_name}</b> subscription, "
            f"please <b>type and send your email address</b> in this chat right now.\n\n"
            f"This email will be used to set up your premium access.\n\n"
            f"⏱️ <i>Your subscription will be activated within 1-2 hours after email submission.</i>"
        )
        await send_telegram_message(telegram_id, msg)
        
        # Notify Admin about new OTT order
        if ADMIN_TELEGRAM_ID:
            await send_telegram_message(
                int(ADMIN_TELEGRAM_ID),
                f"📦 <b>NEW OTT ORDER</b> 📦\n\nOrder <code>{order['id']}</code> for <b>{product_name}</b>.\nWaiting for customer to submit their email. You will activate from the dashboard once email is received."
            )
        logger.info(f"OTT order set to MANUAL_PROCESSING, awaiting email from telegram_id {telegram_id}")

    # 4. Notify Admin
    await notify_admin_on_sale(product_name, amount, category, order["id"])

@app.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: Optional[str] = Header(None)
):
    """
    Handles payment confirmation webhooks from Razorpay.
    Verifies the cryptographic signature before processing the order.
    """
    # Rate limit webhook endpoint
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, max_requests=30, window_seconds=60)
    raw_body = await request.body()
    
    # Verify signature
    if not x_razorpay_signature:
        logger.warning("Missing X-Razorpay-Signature header.")
        raise HTTPException(status_code=400, detail="Missing signature header.")
        
    if RAZORPAY_WEBHOOK_SECRET:
        # Cryptographic verification
        expected = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected, x_razorpay_signature):
            logger.error("Invalid Razorpay webhook signature verification failed.")
            raise HTTPException(status_code=401, detail="Invalid signature.")
    else:
        logger.warning("RAZORPAY_WEBHOOK_SECRET not set. Skipping signature verification in development.")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    event = payload.get("event")
    logger.info(f"Received Razorpay Webhook Event: {event}")

    # Razorpay event: payment.captured or order.paid
    if event in ("payment.captured", "order.paid"):
        payment_entity = payload["payload"]["payment"]["entity"]
        
        payment_id = payment_entity["id"]
        order_id = payment_entity.get("order_id") or payment_id # Order ID or fallback to Payment ID
        amount = payment_entity["amount"] / 100.0 # Convert from paise to rupees
        
        # Process order completion in background tasks
        background_tasks.add_task(
            process_digital_delivery,
            order_id,
            payment_id,
            amount,
            payload
        )
        
    return {"status": "ok"}

@app.get("/")
def root():
    return {"status": "alive", "service": "NexAutomate Backend"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "digital_delivery_backend"}

class OttCredentialPayload(BaseModel):
    order_id: str
    product_name: str
    customer_email: str
    telegram_id: Optional[int] = None
    username: str
    password: str

@app.post("/api/admin/send-ott-credentials")
async def admin_send_ott_credentials(
    request: Request,
    payload: OttCredentialPayload,
    _auth: bool = Depends(verify_admin_api_key)
):
    """Admin endpoint to send OTT credentials directly to customer email and notify them on Telegram.
    Protected by API key authentication via X-Admin-API-Key header."""
    # Rate limit admin endpoint
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, max_requests=10, window_seconds=60)
    # Send the email via Resend
    success = await send_credential_email(
        to_email=payload.customer_email,
        product_name=payload.product_name,
        order_id=payload.order_id,
        username=payload.username,
        password=payload.password
    )
    
    if not success:
        logger.error(f"Failed to send OTT credential email to {payload.customer_email}")
        raise HTTPException(status_code=500, detail="Failed to send credential email")

    # Send Telegram notification if ID provided
    if payload.telegram_id:
        from backend.services.supabase_service import supabase
        user_name = "User"
        try:
            res = supabase.table("users").select("first_name").eq("telegram_id", payload.telegram_id).execute()
            if res.data and res.data[0].get("first_name"):
                user_name = res.data[0]["first_name"]
        except Exception as e:
            logger.error(f"Could not fetch user name for telegram_id {payload.telegram_id}: {e}")

        msg = (
            f"🎉 <b>YOUR SUBSCRIPTION IS NOW ACTIVE!</b> 🎉\n\n"
            f"Your premium <b>{payload.product_name}</b> access has been activated successfully!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>Your {payload.product_name} Login Details:</b>\n\n"
            f"👤 <b>Username/Email:</b> <code>{payload.username}</code>\n"
            f"🔒 <b>Password:</b> <code>{payload.password}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📧 <i>We have also sent these credentials to your email <b>{payload.customer_email}</b>. Please check your email as well!</i>\n\n"
            f"⚠️ <i>Please change the password after logging in to secure your account. Enjoy your premium experience! 🚀</i>\n\n"
            f"🙏 <b>Thank you {user_name} for shopping with us!</b>\n"
            f"We'd love to hear your feedback. Please write a review for us!"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "✍️ Write a Review", "callback_data": "write_review"}],
                [{"text": "🏠 Main Menu", "callback_data": "main_menu"}],
                [{"text": "🛍️ Buy More", "callback_data": "main_menu"}],
                [{"text": "📜 Order History", "callback_data": "view_history"}]
            ]
        }
        await send_telegram_message(payload.telegram_id, msg, reply_markup=keyboard)
        
    return {"status": "ok", "message": "Credentials sent successfully"}
