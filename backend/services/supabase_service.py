import os
import logging
from typing import Dict, Any, Optional, List
from supabase import create_client, Client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Fallback to SUPABASE_KEY if SUPABASE_SERVICE_ROLE is missing (e.g., on Render environment)
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
    logger.error("SUPABASE_URL or SUPABASE_KEY is not set in environment variables.")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE) if SUPABASE_URL and SUPABASE_SERVICE_ROLE else None

def get_db():
    return supabase

def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    try:
        response = supabase.table("products").select("*").eq("id", product_id).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {str(e)}")
    return None

def create_user_if_not_exists(telegram_id: int, username: str, first_name: str) -> Dict[str, Any]:
    try:
        # Check if user exists
        response = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data[0]

        # Insert new user
        insert_response = supabase.table("users").insert({
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name
        }).execute()
        
        if insert_response.data:
            return insert_response.data[0]
    except Exception as e:
        logger.error(f"Error creating user {telegram_id}: {str(e)}")
    return {}

def create_order(telegram_id: int, product_id: str, payment_id: str, amount: float, quantity: int = 1, subscription_months: int = 0) -> Optional[Dict[str, Any]]:
    try:
        # Fetch internal user_id first
        user_response = supabase.table("users").select("id").eq("telegram_id", telegram_id).execute()
        user_id = user_response.data[0]["id"] if user_response.data else None

        insert_response = supabase.table("orders").insert({
            "user_id": user_id,
            "telegram_id": telegram_id,
            "product_id": product_id,
            "payment_id": payment_id,
            "amount": amount,
            "status": "PENDING",
            "quantity": quantity,
            "subscription_months": subscription_months,
            "delivery_status": "PENDING"
        }).execute()

        if insert_response.data:
            return insert_response.data[0]
    except Exception as e:
        logger.error(f"Error creating order for user {telegram_id}: {str(e)}")
    return None

def get_order_by_payment(payment_id: str) -> Optional[Dict[str, Any]]:
    try:
        # Check by payment_id (which could be Razorpay Order ID or Payment ID)
        response = supabase.table("orders").select("*, products(*)").eq("payment_id", payment_id).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error fetching order by payment_id {payment_id}: {str(e)}")
    return None

def get_pending_order_by_user_and_product(telegram_id: int, product_id: str) -> Optional[Dict[str, Any]]:
    try:
        response = supabase.table("orders").select("*, products(*)").eq("telegram_id", telegram_id).eq("product_id", product_id).eq("status", "PENDING").order("created_at", desc=True).limit(1).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error fetching pending order for tg {telegram_id}, prod {product_id}: {str(e)}")
    return None

def update_order_completed(order_id: str, delivery_status: str) -> bool:
    try:
        supabase.table("orders").update({
            "status": "COMPLETED",
            "delivery_status": delivery_status
        }).eq("id", order_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating order status for {order_id}: {str(e)}")
        return False

def get_unused_credential(product_id: str, duration: int = 0) -> Optional[Dict[str, Any]]:
    try:
        # Fetch one unused credential for the product
        query = supabase.table("credentials").select("*").eq("product_id", product_id).eq("status", "UNUSED")
        if duration > 0:
            query = query.eq("subscription_months", duration)
            
        response = query.limit(1).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error fetching credential for product {product_id}: {str(e)}")
    return None

def mark_credential_used(credential_id: str) -> bool:
    try:
        supabase.table("credentials").update({
            "status": "USED"
        }).eq("id", credential_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error marking credential {credential_id} as USED: {str(e)}")
        return False

def create_ott_request(order_id: str, customer_email: str) -> Optional[Dict[str, Any]]:
    try:
        response = supabase.table("ott_requests").insert({
            "order_id": order_id,
            "customer_email": customer_email,
            "status": "PENDING"
        }).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error creating OTT request for order {order_id}: {str(e)}")
    return None

def create_payment_record(razorpay_order_id: str, razorpay_payment_id: str, amount: float, verified: bool, payload: Dict[str, Any]) -> bool:
    try:
        supabase.table("payments").insert({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "amount": amount,
            "verified": verified,
            "payload": payload
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Error logging payment record: {str(e)}")
        return False

def create_review(telegram_id: int, username: str, first_name: str, review_text: str) -> bool:
    try:
        supabase.table("reviews").insert({
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "review_text": review_text
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Error creating review for {telegram_id}: {str(e)}")
        return False

# ==========================================
# WALLET SYSTEM FUNCTIONS
# ==========================================

def get_wallet_balance(telegram_id: int) -> float:
    """Get the current wallet balance for a user."""
    try:
        response = supabase.table("users").select("wallet_balance").eq("telegram_id", telegram_id).execute()
        if response.data:
            return float(response.data[0].get("wallet_balance", 0) or 0)
    except Exception as e:
        logger.error(f"Error fetching wallet balance for {telegram_id}: {str(e)}")
    return 0.0

def add_wallet_balance(telegram_id: int, amount: float, reference_id: str = None, description: str = None) -> bool:
    """Add funds to a user's wallet (deposit or refund)."""
    try:
        current = get_wallet_balance(telegram_id)
        new_balance = current + amount
        supabase.table("users").update({
            "wallet_balance": new_balance
        }).eq("telegram_id", telegram_id).execute()
        
        # Log the transaction
        supabase.table("wallet_transactions").insert({
            "telegram_id": telegram_id,
            "amount": amount,
            "transaction_type": "DEPOSIT",
            "reference_id": reference_id,
            "description": description or f"Wallet deposit of ₹{amount:.2f}"
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Error adding wallet balance for {telegram_id}: {str(e)}")
        return False

def deduct_wallet_balance(telegram_id: int, amount: float, reference_id: str = None, description: str = None) -> bool:
    """Deduct funds from a user's wallet for a purchase."""
    try:
        current = get_wallet_balance(telegram_id)
        if current < amount:
            logger.warning(f"Insufficient wallet balance for {telegram_id}: has ₹{current}, needs ₹{amount}")
            return False
        new_balance = current - amount
        supabase.table("users").update({
            "wallet_balance": new_balance
        }).eq("telegram_id", telegram_id).execute()
        
        # Log the transaction
        supabase.table("wallet_transactions").insert({
            "telegram_id": telegram_id,
            "amount": amount,
            "transaction_type": "PURCHASE",
            "reference_id": reference_id,
            "description": description or f"Product purchase of ₹{amount:.2f}"
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Error deducting wallet balance for {telegram_id}: {str(e)}")
        return False

def refund_wallet_balance(telegram_id: int, amount: float, reference_id: str = None, description: str = None) -> bool:
    """Refund funds back to a user's wallet."""
    try:
        current = get_wallet_balance(telegram_id)
        new_balance = current + amount
        supabase.table("users").update({
            "wallet_balance": new_balance
        }).eq("telegram_id", telegram_id).execute()
        
        # Log the refund transaction
        supabase.table("wallet_transactions").insert({
            "telegram_id": telegram_id,
            "amount": amount,
            "transaction_type": "REFUND",
            "reference_id": reference_id,
            "description": description or f"Refund of ₹{amount:.2f}"
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Error refunding wallet for {telegram_id}: {str(e)}")
        return False

def get_wallet_transactions(telegram_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent wallet transactions for a user."""
    try:
        response = supabase.table("wallet_transactions").select("*").eq("telegram_id", telegram_id).order("created_at", desc=True).limit(limit).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error fetching wallet transactions for {telegram_id}: {str(e)}")
        return []

