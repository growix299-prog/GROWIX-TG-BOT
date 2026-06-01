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
    text = message.text or ""

    # --- CUSTOM EMOJI ID EXTRACTOR TOOL ---
    if message.entities:
        custom_emojis = [
            entity.custom_emoji_id 
            for entity in message.entities 
            if entity.type == 'custom_emoji' and hasattr(entity, 'custom_emoji_id')
        ]
        if custom_emojis:
            response = "🛠️ <b>Custom Emoji IDs Extracted:</b>\n\n"
            for e_id in custom_emojis:
                response += f"<code>{e_id}</code>\n"
            response += "\n<i>Copy these IDs and send them to the developer to use in the bot!</i>"
            await message.reply_text(response, parse_mode="HTML")
            return
    # --------------------------------------
    if text:
        text = text.strip()
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
            if order.get("delivery_status", "").startswith("AWAITING_EMAIL_GAMES"):
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
            
            # Extract quantity from delivery_status (e.g., AWAITING_EMAIL_GAMES_3)
            status_parts = active_order["delivery_status"].split("_")
            qty = int(status_parts[-1]) if status_parts[-1].isdigit() else 1

            if active_order["delivery_status"].startswith("AWAITING_EMAIL_GAMES"):
                # Fetch credentials immediately
                await message.reply_text(f"⏳ <i>Fetching {qty} {product['category'].lower()} credentials, please wait...</i>", parse_mode="HTML")
                
                # Fetch multiple unused credentials
                credentials_response = supabase.table("credentials").select("*").eq("product_id", product["id"]).eq("status", "UNUSED").limit(qty).execute()
                credentials = credentials_response.data or []
                
                if len(credentials) == qty:
                    # Mark all as used
                    for cred in credentials:
                        mark_credential_used(cred["id"])
                        
                    update_order_completed(active_order["id"], "DELIVERED")
                    
                    # Send credentials via Telegram
                    msg = (
                        f"<blockquote>"
                        f"🎉 <b>PAYMENT SUCCESSFUL!</b> 🎉\n\n"
                        f"✨ Your {qty} login credentials for <b>{product['name']}</b> are ready! 🚀\n\n"
                    )
                    
                    for idx, credential in enumerate(credentials, 1):
                        msg += f"🔑 <b>ACCOUNT {idx}:</b>\n"
                        msg += f"👤 <b>Username:</b> <code>{credential['email_or_username']}</code>\n"
                        msg += f"🔒 <b>Password:</b> <code>{credential['password']}</code>\n\n"
                        
                    msg += (
                        f"📧 <i>We have also sent your login credentials to your email <b>{email}</b>.</i>\n\n"
                        f"⚠️ <i>Please change the credentials after logging in to secure your accounts. Enjoy!</i>\n\n"
                        f"🙏 <b>Thank you {html.escape(user.first_name)} for shopping with us!</b>\n"
                        f"We'd love to hear your feedback. Please write a review for us!"
                        f"</blockquote>"
                    )
                    
                    # Send credentials via email (send 1 email with all credentials)
                    try:
                        # Assuming send_game_credential_email can handle multiple, or we just format the usernames
                        usernames = "\n".join([c["email_or_username"] for c in credentials])
                        passwords = "\n".join([c["password"] for c in credentials])
                        await send_game_credential_email(
                            to_email=email,
                            product_name=f"{product['name']} (x{qty})",
                            order_id=active_order["id"],
                            username=usernames,
                            password=passwords
                        )
                    except Exception as e:
                        logger.error(f"Error sending multi-credential email: {e}")
                    
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
                    logger.info(f"{qty} Credentials delivered to telegram_id {user.id} and email {email}")
                else:
                    # Out of stock or partial stock
                    update_order_completed(active_order["id"], "MANUAL_PROCESSING")
                    msg = (
                        f"⚠️ <b>Thank you for your email!</b> ⚠️\n\n"
                        f"Unfortunately, we only have {len(credentials)} out of {qty} accounts available for <b>{product['name']}</b> right now.\n\n"
                        f"Our admin team has been notified and will manually generate and send the remaining credentials shortly via this chat and to your email: {email}."
                    )
                    await message.reply_text(msg, parse_mode="HTML")
                    logger.warning(f"Not enough credentials available for product: {product['name']}. Wanted {qty}, found {len(credentials)}.")
                return

    # Handle clearing conversational states if user clicks a main menu button
    if any(keyword in text for keyword in ["Products", "Purchase History", "Support", "Wallet"]):
        context.user_data.pop('awaiting_product_selection', None)
        context.user_data.pop('awaiting_quantity_for_product', None)

    # 3. Conversational Flow: Handle Quantity Input
    if context.user_data.get('awaiting_quantity_for_product'):
        product = context.user_data['awaiting_quantity_for_product']
        try:
            qty = int(text)
            if qty <= 0:
                raise ValueError
        except ValueError:
            await message.reply_text("❌ Please enter a valid positive number (e.g., 1, 2, 3).")
            return
            
        # Check stock
        stock_resp = supabase.table("credentials").select("id").eq("product_id", product["id"]).eq("status", "UNUSED").execute()
        stock_count = len(stock_resp.data) if stock_resp.data else 0
        
        if qty > stock_count:
            await message.reply_text(f"❌ <b>Unavailable!</b>\nWe only have <b>{stock_count}</b> accounts in stock for {product['name']}.", parse_mode="HTML")
            return
            
        # Proceed to checkout
        price = float(product['price'])
        total_price = price * qty
        
        from telegram_bot.handlers.menu import get_product_animated_emoji
        anim_emoji = get_product_animated_emoji(product['name'])
        
        checkout_text = (
            f"🛒 <b>CHECKOUT SUMMARY</b>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📦 <b>Product:</b> {anim_emoji} {product['name']}\n"
            f"🔢 <b>Quantity:</b> {qty}\n"
            f"💰 <b>Total Price:</b> ₹{total_price:.2f}\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"Please select your preferred payment method below:"
        )
        
        keyboard = [
            [InlineKeyboardButton("👛 Pay via Wallet", callback_data=f"walletpay_{product['id']}_{qty}")],
            [InlineKeyboardButton("💳 Pay via Razorpay", callback_data=f"rzpterms_{product['id']}_{qty}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ]
        
        await message.reply_text(text=checkout_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        context.user_data.pop('awaiting_quantity_for_product', None)
        return

    # 4. Conversational Flow: Handle Product Selection (Fuzzy Match)
    if context.user_data.get('awaiting_product_selection'):
        category = context.user_data['awaiting_product_selection']
        
        response = supabase.table("products").select("*").eq("category", category).eq("active", True).execute()
        products = response.data or []
        
        if not products:
            await message.reply_text("❌ No products available in this category.")
            context.user_data.pop('awaiting_product_selection', None)
            return

        import difflib
        product_names = {p['name'].lower(): p for p in products}
        matches = difflib.get_close_matches(text.lower(), product_names.keys(), n=1, cutoff=0.3)
        
        if not matches:
            await message.reply_text("❌ Product not found. Please check the spelling and try typing again.\n<i>(Example: Netflix)</i>", parse_mode="HTML")
            return
            
        matched_name = matches[0]
        selected_product = product_names[matched_name]
        
        # Check stock
        stock_resp = supabase.table("credentials").select("id").eq("product_id", selected_product["id"]).eq("status", "UNUSED").execute()
        stock_count = len(stock_resp.data) if stock_resp.data else 0
        
        if stock_count == 0:
            await message.reply_text(f"❌ Sorry, <b>{selected_product['name']}</b> is currently out of stock. Please try again later.", parse_mode="HTML")
            context.user_data.pop('awaiting_product_selection', None)
            return
            
        context.user_data['awaiting_quantity_for_product'] = selected_product
        context.user_data.pop('awaiting_product_selection', None)
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]]
        
        await message.reply_text(
            f"✅ <b>{selected_product['name']}</b> is in stock!\n\n"
            f"📦 <b>Available Accounts:</b> {stock_count}\n\n"
            f"⌨️ <b>How many accounts do you want to buy?</b>\n"
            f"<i>(Type a number, e.g., 1 or 2)</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    # Handle ReplyKeyboardMarkup selections
    if text == "🛍️ Products":
        keyboard = [
            [InlineKeyboardButton("📺 OTT Subscriptions", callback_data="cat_OTT")],
            [InlineKeyboardButton("🎮 Game Accounts", callback_data="cat_Games")],
            [InlineKeyboardButton("🤖 AI Subscriptions", callback_data="cat_AI")],
            [InlineKeyboardButton("🎬 Video Editing", callback_data="cat_VideoEditing")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        products_text = (
            f"<b>OUR PRODUCTS</b> <tg-emoji emoji-id=\"5215203655946346044\">🛒</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"BROWSE OUR CATALOG OF PREMIUM DIGITAL SERVICES <tg-emoji emoji-id=\"5352825278672412291\">✅</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"PLEASE SELECT A CATEGORY BELOW <tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji>"
        )
        await message.reply_text(
            text=products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return
        
    elif text == "📝 Purchase History":
        # Simulate history click
        response = supabase.table("orders").select("*, products(*)").eq("telegram_id", user.id).order("created_at", desc=True).execute()
        orders = response.data or []
        if not orders:
            empty_text = (
                f"<b>PURCHASE HISTORY</b> <tg-emoji emoji-id=\"4938318633475507037\">📜</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"YOU HAVEN'T MADE ANY PURCHASES YET. START SHOPPING TO ACCESS PREMIUM PRODUCTS! <tg-emoji emoji-id=\"5215203655946346044\">🛒</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            )
            await message.reply_text(empty_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]), parse_mode="HTML")
            return
            
        history_text = (
            f"<b>YOUR RECENT PURCHASES</b> <tg-emoji emoji-id=\"4938318633475507037\">📜</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        )
        for idx, order in enumerate(orders[:10], 1):
            prod = order.get("products") or {}
            prod_name = prod.get("name", "Unknown Product")
            
            if order.get("status") == "PENDING":
                status = "Pending Payment / Setup"
            else:
                status = "Delivered" if order.get("delivery_status") == "DELIVERED" else "Processing"
                
            history_text += f"{idx}. <b>{prod_name}</b>\n   💰 ₹{float(order.get('amount', 0)):.2f} | 📅 {order.get('created_at', '')[:10]}\n   🚚 Status: {status}\n\n"
        
        history_text += f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        await message.reply_text(text=history_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]), parse_mode="HTML")
        return
        
    elif text == "↗️ Support":
        support_text = (
            f"<b>CUSTOMER SUPPORT</b> <tg-emoji emoji-id=\"5870692618244984670\">📞</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"NEED HELP WITH YOUR DIGITAL PRODUCTS OR PAYMENT ? OUR ELITE SUPPORT TEAM IS READY TO ASSIST YOU 24/7 <tg-emoji emoji-id=\"5208573502046610594\">🕛</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<b><u>Admin Contact:</u></b>\n"
            f"@ur_Growixx222 <tg-emoji emoji-id=\"5352825278672412291\">✅</tg-emoji>\n\n"
            f"PLEASE KEEP YOUR ORDER ID READY FOR FASTER RESOLUTION. <tg-emoji emoji-id=\"5188481279963715781\">🚀</tg-emoji><tg-emoji emoji-id=\"5188481279963715781\">🚀</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"CLICK THE BUTTON BELOW TO START THE CHAT <tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji>"
        )
        await message.reply_text(text=support_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Chat with Admin", url="https://t.me/ur_Growixx222")]]), parse_mode="HTML")
        return

    elif text == "👛 Wallet":
        from backend.services.supabase_service import get_wallet_balance, get_wallet_transactions
        balance = get_wallet_balance(user.id)
        wallet_text = (
            f"<b>MY WALLET</b> <tg-emoji emoji-id=\"5271604874419647061\">👛</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<b>CURRENT BALANCE:</b> ₹{balance:.2f} <tg-emoji emoji-id=\"5350710934992069206\">💰</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"ADD FUNDS TO YOUR WALLET FOR INSTANT PURCHASES <tg-emoji emoji-id=\"5352825278672412291\">✅</tg-emoji>\n"
            f"MINIMUM DEPOSIT: ₹100.00\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"CHOOSE AN OPTION BELOW <tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji>"
        )
        keyboard = [
            [InlineKeyboardButton("➕ Add Funds", callback_data="wallet_deposit")],
            [InlineKeyboardButton("🧾 Transaction History", callback_data="wallet_history")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await message.reply_text(text=wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
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
