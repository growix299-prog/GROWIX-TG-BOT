import os
import hmac
import hashlib
import logging
import time
from collections import defaultdict
import httpx
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import html
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
    create_ott_request,
    add_wallet_balance,
    get_wallet_balance
)
from backend.services.resend_service import send_delivery_email, send_credential_email, send_game_credential_email

# Set up Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TG Bot Digital Delivery Backend", docs_url=None, redoc_url=None)

# Restrict CORS to only your admin dashboard origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://nexautomate-oxsd.vercel.app,http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
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
        
        # Fallback 2: Check via Razorpay Notes for Payment Links
        if not order:
            notes = raw_payload.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {})
            tg_id = notes.get("telegram_id")
            prod_id = notes.get("product_id")
            if tg_id and prod_id:
                from backend.services.supabase_service import get_pending_order_by_user_and_product
                order = get_pending_order_by_user_and_product(int(tg_id), prod_id)
                if order:
                    logger.info(f"Order found via notes fallback for telegram_id: {tg_id}")

    if not order:
        logger.error(f"Order not found for ID: {order_id} or Payment: {payment_id}")
        return

    # Idempotency check: Don't process if already processed
    if order.get("status") != "PENDING":
        logger.info(f"Order {order_id} already processed. Skipping duplicate webhook.")
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

    if category in ("Games", "OTT"):
        # Ask for any message before Automated Credential Dispatch
        update_order_completed(order["id"], "AWAITING_EMAIL_GAMES")
        msg = (
            f"🎉 <b>PAYMENT SUCCESSFUL!</b> 🎉\n\n"
            f"Thank you for purchasing <b>{product_name}</b>!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 <b>NEXT STEP — GET YOUR CREDENTIALS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"To receive your {category.lower()} credentials securely, "
            f"please type <b>anything</b> (e.g., <code>hi</code>) in this chat right now.\n\n"
            f"Your login ID and password will be delivered here instantly! 🚀"
        )
        await send_telegram_message(telegram_id, msg)
        logger.info(f"{category} order set to AWAITING_EMAIL_GAMES, awaiting email from telegram_id {telegram_id}")

    # 4. Notify Admin
    await notify_admin_on_sale(product_name, amount, category, order["id"])

async def process_wallet_deposit(notes: Dict[str, Any], payment_id: str, amount: float, raw_payload: Dict[str, Any]):
    """Processes a wallet deposit after Razorpay confirms payment."""
    telegram_id = int(notes.get("telegram_id", 0))
    if not telegram_id:
        logger.error(f"Wallet deposit webhook missing telegram_id in notes: {notes}")
        return

    logger.info(f"Processing wallet deposit of ₹{amount} for telegram_id {telegram_id}")

    # Log payment record
    create_payment_record(payment_id, payment_id, amount, True, raw_payload)

    # Credit the wallet
    success = add_wallet_balance(
        telegram_id=telegram_id,
        amount=amount,
        reference_id=payment_id,
        description=f"Razorpay deposit of ₹{amount:.2f}"
    )

    if success:
        new_balance = get_wallet_balance(telegram_id)
        msg = (
            f"✅ <b>WALLET DEPOSIT SUCCESSFUL!</b> ✅\n\n"
            f"💰 <b>Amount Deposited:</b> ₹{amount:.2f}\n"
            f"👛 <b>New Balance:</b> ₹{new_balance:.2f}\n\n"
            f"Your wallet has been credited. You can now use it for instant purchases! 🚀"
        )
        keyboard = {
            "inline_keyboard": [
                [{"text": "👛 View Wallet", "callback_data": "view_wallet"}],
                [{"text": "🛍️ Browse Products", "callback_data": "view_products"}]
            ]
        }
        await send_telegram_message(telegram_id, msg, reply_markup=keyboard)
        logger.info(f"Wallet deposit of ₹{amount} credited to telegram_id {telegram_id}. New balance: ₹{new_balance}")
    else:
        logger.error(f"Failed to credit wallet for telegram_id {telegram_id}")
        await send_telegram_message(telegram_id, "❌ There was an error crediting your wallet. Please contact support with your payment ID.")

    # Notify admin
    if ADMIN_TELEGRAM_ID:
        admin_msg = (
            f"🔔 <b>WALLET DEPOSIT</b> 🔔\n\n"
            f"👤 <b>User:</b> {telegram_id}\n"
            f"💰 <b>Amount:</b> ₹{amount:.2f}\n"
            f"🆔 <b>Payment ID:</b> <code>{payment_id}</code>"
        )
        await send_telegram_message(int(ADMIN_TELEGRAM_ID), admin_msg)

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
        
        # Check if this is a wallet deposit
        notes = payment_entity.get("notes", {})
        if notes.get("type") == "wallet_deposit":
            # Process wallet deposit
            background_tasks.add_task(
                process_wallet_deposit,
                notes,
                payment_id,
                amount,
                payload
            )
        else:
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
            f"🙏 <b>Thank you {html.escape(user_name)} for shopping with us!</b>\n"
            f"We'd love to hear your feedback. Please write a review for us!"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "✍️ Write a Review", "callback_data": "write_review", "style": "primary"}],
                [{"text": "🏠 Main Menu", "callback_data": "main_menu"}],
                [{"text": "🛍️ Buy More", "callback_data": "main_menu", "style": "primary"}],
                [{"text": "📜 Order History", "callback_data": "view_history"}]
            ]
        }
        await send_telegram_message(payload.telegram_id, msg, reply_markup=keyboard)
        
    return {"status": "ok", "message": "Credentials sent successfully"}

# ==========================================
# ADMIN USER & WALLET MANAGEMENT ENDPOINTS
# ==========================================

class WalletActionPayload(BaseModel):
    amount: float
    description: Optional[str] = None

@app.get("/api/admin/users")
async def admin_list_users(
    request: Request,
    _auth: bool = Depends(verify_admin_api_key)
):
    """List all users with wallet balances and order counts."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, max_requests=30, window_seconds=60)
    
    db = get_db()
    try:
        # Fetch all users
        users_resp = db.table("users").select("*").order("created_at", desc=True).execute()
        users = users_resp.data or []
        
        # Fetch order counts per user
        for user in users:
            try:
                orders_resp = db.table("orders").select("id, amount, status, delivery_status, created_at, products(name, category)").eq("telegram_id", user["telegram_id"]).order("created_at", desc=True).execute()
                user["orders"] = orders_resp.data or []
                user["total_orders"] = len(user["orders"])
                user["total_spent"] = sum(float(o.get("amount", 0)) for o in user["orders"] if o.get("status") == "COMPLETED")
            except:
                user["orders"] = []
                user["total_orders"] = 0
                user["total_spent"] = 0
            
            try:
                txn_resp = db.table("wallet_transactions").select("*").eq("telegram_id", user["telegram_id"]).order("created_at", desc=True).execute()
                user["wallet_transactions"] = txn_resp.data or []
            except:
                user["wallet_transactions"] = []
        
        return {"users": users}
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/users/{telegram_id}/deduct-funds")
async def admin_deduct_funds(
    telegram_id: int,
    payload: WalletActionPayload,
    request: Request,
    _auth: bool = Depends(verify_admin_api_key)
):
    """Admin manually deducts funds from user's wallet."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, max_requests=10, window_seconds=60)
    
    from backend.services.supabase_service import deduct_wallet_balance
    success = deduct_wallet_balance(
        telegram_id=telegram_id,
        amount=payload.amount,
        reference_id="ADMIN_DEDUCT",
        description=payload.description or f"Admin deduction of ₹{payload.amount:.2f}"
    )
    
    if success:
        new_balance = get_wallet_balance(telegram_id)
        # Notify user via Telegram
        msg = (
            f"📉 <b>WALLET BALANCE UPDATED</b>\n\n"
            f"₹{payload.amount:.2f} has been deducted from your wallet by the admin.\n"
            f"👛 <b>New Balance:</b> ₹{new_balance:.2f}"
        )
        await send_telegram_message(telegram_id, msg)
        return {"status": "ok", "new_balance": new_balance}
    else:
        raise HTTPException(status_code=500, detail="Failed to deduct funds. Insufficient balance?")

@app.post("/api/admin/users/{telegram_id}/add-funds")
async def admin_add_funds(
    telegram_id: int,
    payload: WalletActionPayload,
    request: Request,
    _auth: bool = Depends(verify_admin_api_key)
):
    """Admin manually adds funds to user's wallet."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, max_requests=10, window_seconds=60)
    
    success = add_wallet_balance(
        telegram_id=telegram_id,
        amount=payload.amount,
        reference_id="ADMIN_CREDIT",
        description=payload.description or f"Admin credit of ₹{payload.amount:.2f}"
    )
    
    if success:
        new_balance = get_wallet_balance(telegram_id)
        msg = (
            f"💰 <b>WALLET CREDIT</b>\n\n"
            f"₹{payload.amount:.2f} has been added to your wallet by the admin.\n"
            f"👛 <b>New Balance:</b> ₹{new_balance:.2f}"
        )
        await send_telegram_message(telegram_id, msg)
        return {"status": "ok", "new_balance": new_balance}
    else:
        raise HTTPException(status_code=500, detail="Failed to add funds")

@app.delete("/api/admin/users/{telegram_id}")
async def admin_delete_user(
    telegram_id: int,
    request: Request,
    _auth: bool = Depends(verify_admin_api_key)
):
    """Delete a user and all related data."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, max_requests=5, window_seconds=60)
    
    db = get_db()
    try:
        # Delete wallet transactions
        db.table("wallet_transactions").delete().eq("telegram_id", telegram_id).execute()
        # Delete reviews
        db.table("reviews").delete().eq("telegram_id", telegram_id).execute()
        # Delete orders (and related ott_requests via cascade)
        db.table("orders").delete().eq("telegram_id", telegram_id).execute()
        # Delete user
        db.table("users").delete().eq("telegram_id", telegram_id).execute()
        
        return {"status": "ok", "message": f"User {telegram_id} and all related data deleted."}
    except Exception as e:
        logger.error(f"Error deleting user {telegram_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# BROADCAST STOCK ALERT ENDPOINT
# ==========================================

class BroadcastStockPayload(BaseModel):
    product_id: str
    stock_added: int
    custom_message: Optional[str] = None

@app.post("/api/admin/broadcast-stock")
async def admin_broadcast_stock(
    request: Request,
    payload: BroadcastStockPayload,
    background_tasks: BackgroundTasks,
    _auth: bool = Depends(verify_admin_api_key)
):
    """Broadcasts a stock alert to ALL registered bot users via Telegram."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip, max_requests=5, window_seconds=60)
    
    db = get_db()
    
    # 1. Fetch product details
    try:
        prod_resp = db.table("products").select("*").eq("id", payload.product_id).execute()
        product = prod_resp.data[0] if prod_resp.data else None
    except Exception as e:
        logger.error(f"Broadcast: Error fetching product: {str(e)}")
        raise HTTPException(status_code=404, detail="Product not found")
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 2. Fetch total available stock (UNUSED credentials)
    try:
        stock_resp = db.table("credentials").select("id").eq("product_id", payload.product_id).eq("status", "UNUSED").execute()
        total_stock = len(stock_resp.data) if stock_resp.data else 0
    except Exception:
        total_stock = 0
    
    # 3. Fetch all users
    try:
        users_resp = db.table("users").select("telegram_id").execute()
        users = users_resp.data or []
    except Exception as e:
        logger.error(f"Broadcast: Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")
    
    if not users:
        return {"status": "ok", "sent": 0, "total_users": 0, "message": "No users found"}
    
    # 4. Build the broadcast message
    product_name = product["name"]
    category = product["category"]
    price = float(product["price"])
    
    from telegram_bot.handlers.menu import get_product_emoji
    emoji = get_product_emoji(product_name)
    
    broadcast_msg = (
        f"🔔 <b>NEW STOCK ALERT!</b> 🔔\n"
        f"▬▬▬▬▬▬▬▬▬▬▬\n\n"
        f"{emoji} <b>Product:</b> {product_name}\n"
        f"🗂️ <b>Category:</b> {category}\n"
        f"💰 <b>Price:</b> ₹{price:.2f}\n\n"
        f"📦 <b>Stock Added:</b> {payload.stock_added} accounts\n"
        f"📊 <b>Total Available:</b> {total_stock} accounts\n\n"
    )
    
    if payload.custom_message:
        broadcast_msg += f"💬 {payload.custom_message}\n\n"
    
    broadcast_msg += (
        f"▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🛒 <i>Grab yours before it's gone!</i>"
    )
    
    keyboard = {
        "inline_keyboard": [
            [{"text": f"🛒 Buy {product_name} Now", "callback_data": f"prod_{product['id']}"}],
            [{"text": "🛍️ Browse All Products", "callback_data": "view_products"}]
        ]
    }
    
    # 5. Send broadcast in background
    async def send_broadcast():
        import asyncio
        sent_count = 0
        failed_count = 0
        for user in users:
            try:
                await send_telegram_message(user["telegram_id"], broadcast_msg, reply_markup=keyboard)
                sent_count += 1
            except Exception as e:
                logger.error(f"Broadcast failed for {user['telegram_id']}: {str(e)}")
                failed_count += 1
            # Small delay to avoid Telegram rate limits (30 msgs/sec)
            await asyncio.sleep(0.05)
        logger.info(f"Broadcast complete: {sent_count} sent, {failed_count} failed out of {len(users)} users")
    
    background_tasks.add_task(send_broadcast)
    
    return {
        "status": "ok",
        "total_users": len(users),
        "product": product_name,
        "stock_added": payload.stock_added,
        "total_stock": total_stock,
        "message": f"Broadcasting to {len(users)} users in background"
    }

