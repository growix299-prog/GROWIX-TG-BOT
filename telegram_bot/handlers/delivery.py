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

    if context.user_data.get('awaiting_manual_deposit'):
        try:
            amount = float(text.strip())
            if amount < 1 or amount > 10000:
                raise ValueError("Amount out of range")
        except ValueError:
            await message.reply_text(
                "❌ Please enter a valid number between ₹1 and ₹10,000.\n<i>(Example: 150)</i>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="view_wallet")]]),
                parse_mode="HTML"
            )
            return

        # Valid amount, generate payment link
        context.user_data.pop('awaiting_manual_deposit', None)
        
        loading_msg = await message.reply_text("<blockquote>⏳ <i>Generating secure payment link for wallet deposit...</i></blockquote>", parse_mode="HTML")
        
        from telegram_bot.services.razorpay_service import create_deposit_payment_link
        pay_res = await create_deposit_payment_link(
            amount=amount,
            telegram_id=user.id,
            first_name=user.first_name
        )
        
        if not pay_res.get("success"):
            await loading_msg.edit_text(
                text=f"❌ Failed to create payment link: {pay_res.get('error')}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Wallet", callback_data="view_wallet")]])
            )
            return
            
        checkout_url = pay_res.get("short_url")
        
        deposit_confirm_text = (
            f"<b>DEPOSIT INITIATED</b> <tg-emoji emoji-id=\"6230853345733510932\">💰</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"<b>Amount:</b> ₹{amount:.2f}\n\n"
            f"<i>Click the button below to complete your deposit securely via Razorpay.\n"
            f"Your wallet will be credited instantly after payment confirmation.</i>"
        )
        
        pay_keyboard = [
            [InlineKeyboardButton("🔗 Pay & Deposit via Razorpay", url=checkout_url)],
            [InlineKeyboardButton("❌ Cancel", callback_data="view_wallet")]
        ]
        
        await loading_msg.edit_text(
            text=deposit_confirm_text,
            reply_markup=InlineKeyboardMarkup(pay_keyboard),
            parse_mode="HTML"
        )
        return

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
                    f"⚠️ <b>Action Required: Pending Delivery</b>\n\n"
                    f"You have a pending order for <b>{product['name']}</b>!\n"
                    f"Before you can continue, please type your email address (e.g., <code>alex@gmail.com</code>) below so we can deliver your credentials securely.",
                    parse_mode="HTML"
                )
                return

            # Email is valid! Create the OTT activation request
            email = text.lower()
            
            qty = active_order.get("quantity", 1)

            if active_order["delivery_status"].startswith("AWAITING_EMAIL_GAMES"):
                # Fetch credentials immediately
                await message.reply_text(f"⏳ <i>Fetching {qty} {product['category'].lower()} credentials, please wait...</i>", parse_mode="HTML")
                
                # Fetch multiple unused credentials
                q = supabase.table("credentials").select("*").eq("product_id", product["id"]).eq("status", "UNUSED")
                if product["category"] == "OTT" and active_order.get("subscription_months", 0) > 0:
                    q = q.eq("subscription_months", active_order.get("subscription_months"))
                credentials_response = q.limit(qty).execute()
                
                credentials = credentials_response.data or []
                
                if len(credentials) == qty:
                    # Mark all as used
                    for cred in credentials:
                        mark_credential_used(cred["id"])
                        
                    update_order_completed(active_order["id"], "DELIVERED")
                    
                    months = active_order.get("subscription_months", 0)
                    duration_text = f" ({months} Months)" if product["category"] == "OTT" and months > 0 else ""
                    product_display_name = f"{product['name']}{duration_text}"
                    
                    # Send credentials via Telegram
                    msg = (
                        f"<b>PAYMENT SUCCESSFUL</b> <tg-emoji emoji-id=\"6093648802986592017\">✅</tg-emoji>\n"
                        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
                        f"✨ Your {qty} login credentials for <b>{product_display_name}</b> are ready! <tg-emoji emoji-id=\"5343553259971822765\">🚀</tg-emoji>\n\n"
                    )
                    
                    for idx, credential in enumerate(credentials, 1):
                        msg += f"<b>ACCOUNT {idx}</b> <tg-emoji emoji-id=\"5427009714745517609\">🔑</tg-emoji>\n"
                        msg += f"👤 <b>Username:</b> <code>{credential['email_or_username']}</code>\n"
                        msg += f"🔒 <b>Password:</b> <code>{credential['password']}</code>\n\n"
                        
                    msg += (
                        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                        f"<tg-emoji emoji-id=\"5465665476971471368\">📧</tg-emoji> <i>We have also sent your login credentials to your email <b>{email}</b>.</i>\n\n"
                        f"<tg-emoji emoji-id=\"5463139369978174548\">⚠️</tg-emoji> <i>Please change the credentials after logging in to secure your accounts. Enjoy!</i>\n\n"
                        f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> <b>Thank you {html.escape(user.first_name)} for shopping with us!</b>\n"
                        f"We'd love to hear your feedback. Please write a review for us!"
                    )
                    
                    # Send credentials via email (send 1 email with all credentials)
                    try:
                        # Assuming send_game_credential_email can handle multiple, or we just format the usernames
                        usernames = "\n".join([c["email_or_username"] for c in credentials])
                        passwords = "\n".join([c["password"] for c in credentials])
                        await send_game_credential_email(
                            to_email=email,
                            product_name=f"{product_display_name} (x{qty})",
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
        months = context.user_data.get('awaiting_quantity_duration', 0)
        
        try:
            qty = int(text)
            if qty <= 0:
                raise ValueError
        except ValueError:
            await message.reply_text("❌ Please enter a valid positive number (e.g., 1, 2, 3).")
            return
            
        # Check stock
        q = supabase.table("credentials").select("id").eq("product_id", product["id"]).eq("status", "UNUSED")
        if product["category"] == "OTT" and months > 0:
            q = q.eq("subscription_months", months)
        stock_resp = q.execute()
        stock_count = len(stock_resp.data) if stock_resp.data else 0
        
        if qty > stock_count:
            await message.reply_text(f"❌ <b>Unavailable!</b>\nWe only have <b>{stock_count}</b> accounts in stock for {product['name']}.", parse_mode="HTML")
            return
            
        # Proceed to checkout
        if product["category"] == "OTT" and months > 0:
            price = float(product.get(f"price_{months}m") or 0)
            product_name_display = f"{product['name']} ({months} Months)"
        else:
            price = float(product['price'])
            product_name_display = product['name']
            
        total_price = price * qty
        
        from telegram_bot.handlers.menu import get_product_animated_emoji
        anim_emoji = get_product_animated_emoji(product['name'])
        
        checkout_text = (
            f"🛒 <b>CHECKOUT SUMMARY</b>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📦 <b>Product:</b> {anim_emoji} {product_name_display}\n"
            f"🔢 <b>Quantity:</b> {qty}\n"
            f"💰 <b>Total Price:</b> ₹{total_price:.2f}\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"Please select your preferred payment method below:"
        )
        
        keyboard = [
            [InlineKeyboardButton("👛 Pay via Wallet", callback_data=f"walletpay_{product['id']}_{months}_{qty}")],
            [InlineKeyboardButton("💳 Pay via Razorpay", callback_data=f"rzpterms_{product['id']}_{months}_{qty}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ]
        
        await message.reply_text(text=checkout_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        context.user_data.pop('awaiting_quantity_for_product', None)
        context.user_data.pop('awaiting_quantity_duration', None)
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
            category_name = context.user_data.get('awaiting_product_selection', 'OTT')
            category_examples = {
                "OTT": "Netflix",
                "Games": "Steam",
                "AI": "ChatGPT",
                "VideoEditing": "CapCut"
            }
            example_prod = category_examples.get(category_name, "Netflix")
            keyboard = [
                [InlineKeyboardButton("⌨️ Type Again", callback_data=f"type_again_{category_name}")],
                [InlineKeyboardButton("🔙 Back to Products", callback_data=f"cat_{category_name}")]
            ]
            await message.reply_text(
                f"❌ Product not found. Please check the spelling and try typing again.\n<i>(Example: {example_prod})</i>", 
                reply_markup=InlineKeyboardMarkup(keyboard), 
                parse_mode="HTML"
            )
            return
            
        matched_name = matches[0]
        selected_product = product_names[matched_name]
        
        if selected_product['category'] == 'OTT':
            from telegram_bot.handlers.menu import get_product_animated_emoji
            anim_emoji = get_product_animated_emoji(selected_product['name'])
            
            stock_by_duration = {1: 0, 3: 0, 6: 0}
            stock_resp = supabase.table("credentials").select("id, subscription_months").eq("product_id", selected_product["id"]).eq("status", "UNUSED").execute()
            if stock_resp.data:
                for cred in stock_resp.data:
                    m = cred.get("subscription_months")
                    if m in stock_by_duration:
                        stock_by_duration[m] += 1
            
            keyboard = []
            if stock_by_duration[1] > 0:
                keyboard.append([InlineKeyboardButton(f"💳 Buy 1 Month (₹{float(selected_product.get('price_1m') or 0):.2f})", callback_data=f"buy_{selected_product['id']}_1")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ 1 Month (Out of Stock)", callback_data="ignore")])
                
            if stock_by_duration[3] > 0:
                keyboard.append([InlineKeyboardButton(f"💳 Buy 3 Months (₹{float(selected_product.get('price_3m') or 0):.2f})", callback_data=f"buy_{selected_product['id']}_3")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ 3 Months (Out of Stock)", callback_data="ignore")])
                
            if stock_by_duration[6] > 0:
                keyboard.append([InlineKeyboardButton(f"💳 Buy 6 Months (₹{float(selected_product.get('price_6m') or 0):.2f})", callback_data=f"buy_{selected_product['id']}_6")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ 6 Months (Out of Stock)", callback_data="ignore")])
                
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="main_menu")])
            
            details = (
                f"<blockquote>"
                f"📦 <b>PRODUCT DETAIL</b> 📦\n\n"
                f"🏷️ <b>Name:</b> {anim_emoji} {selected_product['name']}\n"
                f"🗂️ <b>Category:</b> {selected_product['category']}\n"
                f"💰 <b>1 Month:</b> ₹{float(selected_product.get('price_1m') or 0):.2f}\n"
                f"💰 <b>3 Months:</b> ₹{float(selected_product.get('price_3m') or 0):.2f}\n"
                f"💰 <b>6 Months:</b> ₹{float(selected_product.get('price_6m') or 0):.2f}\n"
                f"⚡ <b>Delivery:</b> ✨ INSTANT AUTO-DELIVERY ✨\n\n"
                f"🛒 <i>Please select your desired duration below:</i>\n"
                f"</blockquote>"
            )
            
            await message.reply_text(details, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            context.user_data.pop('awaiting_product_selection', None)
            return

        # Check stock for non-OTT
        stock_resp = supabase.table("credentials").select("id").eq("product_id", selected_product["id"]).eq("status", "UNUSED").execute()
        stock_count = len(stock_resp.data) if stock_resp.data else 0
        
        if stock_count == 0:
            await message.reply_text(f"❌ Sorry, <b>{selected_product['name']}</b> is currently out of stock. Please try again later.", parse_mode="HTML")
            context.user_data.pop('awaiting_product_selection', None)
            return
            
        context.user_data['awaiting_quantity_for_product'] = selected_product
        context.user_data['awaiting_quantity_duration'] = 0
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
            f"<b>OUR PRODUCTS</b> <tg-emoji emoji-id=\"5780560530515171033\">🛒</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"BROWSE OUR CATALOG OF PREMIUM DIGITAL SERVICES <tg-emoji emoji-id=\"5456140674028019486\">✅</tg-emoji>\n"
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
                f"<b>PURCHASE HISTORY</b> <tg-emoji emoji-id=\"5940804519083383006\">📜</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"YOU HAVEN'T MADE ANY PURCHASES YET. START SHOPPING TO ACCESS PREMIUM PRODUCTS! <tg-emoji emoji-id=\"6230853345733510932\">🛒</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            )
            await message.reply_text(empty_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]), parse_mode="HTML")
            return
            
        history_text = (
            f"<b>YOUR RECENT PURCHASES</b> <tg-emoji emoji-id=\"5940804519083383006\">📜</tg-emoji>\n"
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
            f"<b>MY WALLET</b> <tg-emoji emoji-id=\"5343777479091831702\">👛</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<b>CURRENT BALANCE:</b> ₹{balance:.2f} <tg-emoji emoji-id=\"5350710934992069206\">💰</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"ADD FUNDS TO YOUR WALLET FOR INSTANT PURCHASES\n"
            f"MINIMUM DEPOSIT: ₹1 <tg-emoji emoji-id=\"5417924076503062111\">✅</tg-emoji>\n"
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
