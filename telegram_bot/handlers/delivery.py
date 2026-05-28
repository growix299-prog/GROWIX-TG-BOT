import re
import logging
import html
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from backend.services.supabase_service import get_db, create_ott_request, get_unused_credential, mark_credential_used, update_order_completed, create_review
from backend.services.resend_service import send_delivery_email, send_game_credential_email

logger = logging.getLogger(__name__)

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Captures text messages from users.
    If the user has a pending OTT manual delivery, this captures their email.
    Otherwise, prompts the main menu.
    """
    message = update.message
    user = update.effective_user
    text = message.text.strip()
    supabase = get_db()

    # 1. Check if user is writing a review
    if context.user_data.get('awaiting_review'):
        create_review(user.id, user.username, user.first_name, text)
        context.user_data['awaiting_review'] = False
        await message.reply_text("✅ <b>Thank you!</b>\nYour review has been submitted successfully.", parse_mode="HTML")
        return

    # 2. Look for a completed order for this user that needs manual activation (OTT)
    try:
        response = supabase.table("orders").select("*, products(*)").eq("telegram_id", user.id).eq("status", "COMPLETED").in_("delivery_status", ["MANUAL_PROCESSING", "AWAITING_EMAIL_GAMES"]).order("created_at", desc=True).execute()
        pending_orders = response.data
    except Exception as e:
        logger.error(f"Error checking pending orders: {str(e)}")
        pending_orders = []

    active_order = None
    if pending_orders:
        for order in pending_orders:
            if order["delivery_status"] == "AWAITING_EMAIL_GAMES":
                active_order = order
                break

    if active_order:
        # The user is prompted to submit their email
            product = active_order["products"]
            
            # Simple regex validation for email
            if not re.match(EMAIL_REGEX, text):
                await message.reply_text(
                    "❌ <b>Invalid Email Address</b>\n\n"
                    "Please send a valid email format (e.g., <code>alex@gmail.com</code>) to register your OTT subscription.",
                    parse_mode="HTML"
                )
                return

            # Email is valid! Create the OTT activation request
            email = text.lower()
            
            if active_order["delivery_status"] == "AWAITING_EMAIL_GAMES":
                # Fetch credentials immediately
                await message.reply_text(f"⏳ <i>Fetching your {product['category'].lower()} credentials, please wait...</i>", parse_mode="HTML")
                
                credential = get_unused_credential(product["id"])
                if credential:
                    mark_credential_used(credential["id"])
                    update_order_completed(active_order["id"], "DELIVERED")
                    
                    subscription_text = ""
                    if product.get('category') == 'OTT' and credential.get('subscription_months'):
                        try:
                            # created_at might have 'Z' or offset
                            created_str = credential['created_at'].replace('Z', '+00:00')
                            # Handle postgres timestamp
                            if '.' in created_str:
                                created_str = created_str.split('+')[0] + '+00:00'
                            created = datetime.fromisoformat(created_str)
                            now = datetime.now(timezone.utc)
                            months = int(credential['subscription_months'])
                            
                            total_valid_days = months * 30
                            days_passed = (now - created).days
                            days_left = total_valid_days - days_passed
                            
                            if days_left > 0:
                                subscription_text = f"⏳ <b>Time Remaining:</b> {days_left} Days\n\n"
                            else:
                                subscription_text = f"⏳ <b>Time Remaining:</b> EXPIRED\n\n"
                        except Exception as e:
                            logger.error(f"Date parsing error: {e}")
                            subscription_text = ""
                            
                    # Send credentials via Telegram
                    msg = (
                        f"<blockquote>"
                        f"🎉 <b>PAYMENT SUCCESSFUL!</b> 🎉\n\n"
                        f"✨ Your login ID and password for <b>{product['name']}</b> are ready! 🚀\n\n"
                        f"🔑 <b>LOGIN DETAILS:</b>\n"
                        f"👤 <b>Username/Email:</b> <code>{credential['email_or_username']}</code>\n"
                        f"🔒 <b>Password:</b> <code>{credential['password']}</code>\n\n"
                        f"{subscription_text}"
                        f"📧 <i>We have also sent your login credentials to your email <b>{email}</b>.</i>\n\n"
                        f"⚠️ <i>Please change the credentials after logging in to secure your account. Enjoy!</i>\n\n"
                        f"🙏 <b>Thank you {html.escape(user.first_name)} for shopping with us!</b>\n"
                        f"We'd love to hear your feedback. Please write a review for us!"
                        f"</blockquote>"
                    )
                    
                    # Send credentials via email
                    await send_game_credential_email(
                        to_email=email,
                        product_name=product["name"],
                        order_id=active_order["id"],
                        username=credential['email_or_username'],
                        password=credential['password']
                    )
                    
                    keyboard = [
                        [InlineKeyboardButton("✍️ Write a Review", callback_data="write_review", style="primary")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                        [InlineKeyboardButton("🛍️ Buy More", callback_data="main_menu", style="primary")],
                        [InlineKeyboardButton("📜 Order History", callback_data="view_history")]
                    ]
                    await message.reply_text(
                        text=msg,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                    logger.info(f"Credential delivered to telegram_id {user.id} and email {email}")
                else:
                    # Out of stock
                    update_order_completed(active_order["id"], "MANUAL_PROCESSING")
                    msg = (
                        f"⚠️ <b>Thank you for your email!</b> ⚠️\n\n"
                        f"Unfortunately, we are currently <b>out of stock</b> of accounts for <b>{product['name']}</b>.\n\n"
                        f"Our admin team has been notified and will manually send your credentials shortly via this chat and to your email: {email}."
                    )
                    await message.reply_text(msg, parse_mode="HTML")
                    logger.warning(f"No credentials available for product: {product['name']}")
                return

    # Handle ReplyKeyboardMarkup selections
    if text == "🛍️ Products":
        keyboard = [
            [InlineKeyboardButton("📺 OTT Subscriptions", callback_data="cat_OTT")],
            [InlineKeyboardButton("🎮 Game Accounts", callback_data="cat_Games")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await message.reply_text(
            text="<blockquote>🛒 <b>CATEGORIES</b>\n\nPlease select a product category below:</blockquote>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    elif text in ["🎁 Redeem Code", "👛 Wallet", "👤 My Profile"]:
        await message.reply_text("⏳ This feature is coming soon!")
        return
        
    elif text == "📝 Purchase History":
        # Simulate history click
        response = supabase.table("orders").select("*, products(*)").eq("telegram_id", user.id).order("created_at", desc=True).execute()
        orders = response.data or []
        if not orders:
            await message.reply_text("<blockquote>📜 <b>ORDER HISTORY</b>\n\nYou haven't made any purchases yet. Start shopping to access premium products!</blockquote>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]), parse_mode="HTML")
            return
        history_text = "<blockquote>📜 <b>YOUR RECENT ORDERS:</b>\n\n"
        for idx, order in enumerate(orders[:10], 1):
            prod = order.get("products") or {}
            history_text += f"{idx}. <b>{prod.get('name', 'Product')}</b>\n   💰 ₹{float(order.get('amount', 0)):.2f} | 📅 {order.get('created_at', '')[:10]}\n   🚚 Status: {order.get('status')}\n\n"
        history_text += "</blockquote>"
        await message.reply_text(text=history_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]), parse_mode="HTML")
        return
        
    elif text == "💬 Support":
        support_text = "<blockquote>ℹ️ <b>PREMIUM CUSTOMER SUPPORT</b> ℹ️\n\n👤 <b>Admin Contact:</b> @ur_aurexia222\n\n<i>Please provide your Order Reference ID when reaching out for the fastest resolution.</i></blockquote>"
        await message.reply_text(text=support_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Chat with Admin", url="https://t.me/ur_aurexia222")]]), parse_mode="HTML")
        return

    # Default fallback: If no OTT registration is pending, show main menu keyboard
    fallback_text = (
        "💡 <b>Need assistance?</b>\n\n"
        "Please select an option from the menu below, or use the buttons:"
    )
    from telegram_bot.handlers.menu import get_main_menu_keyboard
    await message.reply_text(
        text=fallback_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
