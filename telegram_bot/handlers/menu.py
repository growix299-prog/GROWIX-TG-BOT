import os
import logging
import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from backend.services.supabase_service import (
    create_user_if_not_exists,
    get_db,
    create_order,
    get_unused_credential
)
from telegram_bot.services.razorpay_service import create_payment_link

logger = logging.getLogger(__name__)

# Main Menu Layout
def get_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🛍️ Products", "📝 Purchase History"],
        ["↗️ Support"]
    ], resize_keyboard=True)

def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🛍️ Products", callback_data="view_products"),
            InlineKeyboardButton("📝 Purchase History", callback_data="view_history")
        ],
        [
            InlineKeyboardButton("↗️ Support", callback_data="view_support")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_channel_membership(user_id, context: ContextTypes.DEFAULT_TYPE):
    """Checks if the user is a member of the required channels."""
    channels = ["@aurexia_store"]
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked', 'restricted']:
                return False
        except Exception as e:
            logger.error(f"Error checking membership for {channel}: {e}")
            return False
    return True

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot.")
    
    # Save user to DB
    create_user_if_not_exists(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )

    is_member = await check_channel_membership(user.id, context)
    
    if not is_member:
        banner = (
            f"🚀 System Dashboard Activated\n\n"
            f"Hello {html.escape(user.first_name)}! To unlock our automated instant delivery of gaming credentials and premium OTT services, you must join our official channels.\n\n"
            f"📌 Join the channel below to continue:"
        )
        keyboard = [
            [InlineKeyboardButton("🔴 Join Channel 🔴", url="https://t.me/aurexia_store", **{"style": "danger"} if True else {})],
            [InlineKeyboardButton("✅ I've Joined", callback_data="check_joined")]
        ]
        await update.message.reply_text(
            text=banner,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    banner = (
        f"🚀 <b>System Dashboard Activated</b>\n\n"
        f"📌 <b>Quick guide:</b>\n"
        f"1. Tap 'OTT' or 'Games' to browse products.\n"
        f"2. Choose the product you want.\n"
        f"3. Complete the payment.\n"
        f"4. Your product will be delivered instantly.\n\n"
        f"📌 <i>Please choose a menu below:</i>"
    )

    # Send the bottom reply keyboard first
    await update.message.reply_text(
        text="Loading interface...",
        reply_markup=get_reply_keyboard()
    )
    # Then send the main menu with inline buttons
    await update.message.reply_text(
        text=banner,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /history command."""
    user = update.effective_user
    supabase = get_db()
    
    try:
        response = supabase.table("orders").select("*, products(*)").eq("telegram_id", user.id).order("created_at", desc=True).execute()
        orders = response.data
    except Exception as e:
        logger.error(f"Error fetching order history: {str(e)}")
        orders = []

    if not orders:
        await update.message.reply_text(
            text="<blockquote>📜 <b>ORDER HISTORY</b>\n\nYou haven't made any purchases yet. Start shopping to access premium products!</blockquote>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
            parse_mode="HTML"
        )
        return

    history_text = "<blockquote>📜 <b>YOUR RECENT ORDERS:</b>\n\n"
    for idx, order in enumerate(orders[:10], 1):
        prod = order.get("products") or {}
        prod_name = prod.get("name", "Unknown Product")
        
        if order.get("status") == "PENDING":
            status = "Pending Payment / Setup"
        else:
            status = "Delivered" if order.get("delivery_status") == "DELIVERED" else "Processing"
            
        history_text += f"{idx}. <b>{prod_name}</b>\n   💰 ₹{float(order.get('amount', 0)):.2f} | 📅 {order.get('created_at', '')[:10]}\n   🚚 Status: {status}\n\n"
        
    history_text += "</blockquote>"
    
    await update.message.reply_text(
        text=history_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
        parse_mode="HTML"
    )

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /support command."""
    support_text = (
        f"<blockquote>"
        f"ℹ️ <b>PREMIUM CUSTOMER SUPPORT</b> ℹ️\n\n"
        f"Experiencing an issue with a digital product or payment? Our elite support team is ready to assist you.\n\n"
        f"👤 <b>Admin Contact:</b> @ur_aurexia222\n\n"
        f"<i>Please provide your Order Reference ID when reaching out for the fastest resolution.</i>"
        f"</blockquote>"
    )
    keyboard = [
        [InlineKeyboardButton("💬 Chat with Admin", url="https://t.me/ur_aurexia222")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    await update.message.reply_text(
        text=support_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


def get_product_emoji(name):
    n = name.lower()
    if 'netflix' in n: return '🔴'
    if 'prime' in n: return '🔵'
    if 'canva' in n: return '🖌️'
    if 'crunchyroll' in n: return '🟠'
    if 'spotify' in n: return '🟢'
    if 'duolingo' in n: return '🟢'
    if 'gta' in n: return '🚗'
    if 'valorant' in n: return '🎯'
    if 'nord' in n or 'vpn' in n: return '🛡️'
    if 'tradingview' in n: return '📈'
    return '🔹'

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes all inline button clicks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user
    supabase = get_db()

    if data == "coming_soon":
        await query.answer("⏳ This feature is coming soon!", show_alert=True)
        return

    if data == "view_products":
        keyboard = [
            [InlineKeyboardButton("📺 OTT Subscriptions", callback_data="cat_OTT")],
            [InlineKeyboardButton("🎮 Game Accounts", callback_data="cat_Games")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            text="<blockquote>🛒 <b>CATEGORIES</b>\n\nPlease select a product category below:</blockquote>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if data == "check_joined":
        is_member = await check_channel_membership(user.id, context)
        if is_member:
            banner = (
                f"🚀 <b>System Dashboard Activated</b>\n\n"
                f"📌 <b>Quick guide:</b>\n"
                f"1. Tap 'OTT' or 'Games' to browse products.\n"
                f"2. Choose the product you want.\n"
                f"3. Complete the payment.\n"
                f"4. Your product will be delivered instantly.\n\n"
                f"📌 <i>Please choose a menu below:</i>"
            )
            await query.edit_message_text(
                text=banner,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ First join the channel!", show_alert=True)
            banner = (
                f"<blockquote>"
                f"❌ <b>ACCESS DENIED</b> ❌\n\n"
                f"You haven't joined both channels yet! First join the channel to continue.\n\n"
                f"👇 <i>Please join the channel below:</i>"
                f"</blockquote>"
            )
            keyboard = [
                [InlineKeyboardButton("🔴 Join Channel 🔴", url="https://t.me/aurexia_store", **{"style": "danger"} if True else {})],
                [InlineKeyboardButton("✅ I've Joined", callback_data="check_joined")]
            ]
            await query.edit_message_text(
                text=banner,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            
    elif data == "main_menu":
        is_member = await check_channel_membership(user.id, context)
        if not is_member:
            banner = (
                f"<blockquote>"
                f"❌ <b>ACCESS DENIED</b> ❌\n\n"
                f"First join the channel to unlock the bot!\n\n"
                f"👇 <i>Please join the channel below:</i>"
                f"</blockquote>"
            )
            keyboard = [
                [InlineKeyboardButton("🔴 Join Channel 🔴", url="https://t.me/aurexia_store", **{"style": "danger"} if True else {})],
                [InlineKeyboardButton("✅ I've Joined", callback_data="check_joined")]
            ]
            await query.edit_message_text(
                text=banner,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return

        banner = (
            f"🚀 System Dashboard Activated\n\n"
            f"📌 Quick guide:\n"
            f"1. Tap 'Products'.\n"
            f"2. Choose the product you want.\n"
            f"3. Complete the payment.\n"
            f"4. Your product will be delivered instantly.\n\n"
            f"📌 Please choose a menu:"
        )
        await query.edit_message_text(
            text=banner,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )

    elif data.startswith("cat_"):
        is_member = await check_channel_membership(user.id, context)
        if not is_member:
            await query.answer("❌ First join the channel!", show_alert=True)
            banner = (
                f"<blockquote>"
                f"❌ <b>ACCESS DENIED</b> ❌\n\n"
                f"First join the channel to view products!\n\n"
                f"👇 <i>Please join the channel below:</i>"
                f"</blockquote>"
            )
            keyboard = [
                [InlineKeyboardButton("🔴 Join Channel 🔴", url="https://t.me/aurexia_store", **{"style": "danger"} if True else {})],
                [InlineKeyboardButton("✅ I've Joined", callback_data="check_joined")]
            ]
            await query.edit_message_text(
                text=banner,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return

        category = data.split("_")[1]
        
        try:
            response = supabase.table("products").select("*").eq("category", category).eq("active", True).execute()
            products = response.data
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            products = []
            error_msg = str(e)
        else:
            error_msg = "No products found in DB."

        if not products:
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
            await query.edit_message_text(
                text=f"🛒 <b>Available {category} Products:</b>\n\nCurrently out of stock. Please check back later!",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return

        keyboard = []
        for prod in products:
            emoji = get_product_emoji(prod['name'])
            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} {prod['name']} | ₹{float(prod['price']):.2f}", 
                    callback_data=f"prod_{prod['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])

        await query.edit_message_text(
            text=f"🛒 <b>Available Products:</b>\n\nChoose a product below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data.startswith("prod_"):
        product_id = data.split("_")[1]
        
        try:
            response = supabase.table("products").select("*").eq("id", product_id).execute()
            product = response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error fetching product detail: {str(e)}")
            product = None

        if not product:
            await query.edit_message_text(
                text="<blockquote>❌ Product not found. It may have been discontinued.</blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
                parse_mode="HTML"
            )
            return

        is_in_stock = False
        stock_label = ""
        
        try:
            stock_resp = supabase.table("credentials").select("id").eq("product_id", product["id"]).eq("status", "UNUSED").execute()
            stock_count = len(stock_resp.data) if stock_resp.data else 0
        except Exception as e:
            logger.error(f"Error checking stock: {str(e)}")
            stock_count = 0

        is_in_stock = stock_count > 0
        stock_label = f"✅ In Stock ({stock_count} available)" if is_in_stock else "❌ OUT OF STOCK"

        details = (
            f"<blockquote>"
            f"📦 <b>PRODUCT DETAIL</b> 📦\n\n"
            f"🏷️ <b>Name:</b> {product['name']}\n"
            f"🗂️ <b>Category:</b> {product['category']}\n"
            f"💰 <b>Price:</b> ₹{float(product['price']):.2f}\n"
            f"⚡ <b>Delivery:</b> ✨ INSTANT AUTO-DELIVERY ✨\n"
            f"📊 <b>Stock Status:</b> {stock_label}\n\n"
        )

        if is_in_stock:
            details += f"🛒 <i>Ready to purchase? Click 'Buy Now' to generate a secure automated checkout link.</i>"
            details += "</blockquote>"
            keyboard = [
                [InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{product['id']}")],
                [InlineKeyboardButton(f"🔙 Back to {product['category']}", callback_data=f"cat_{product['category']}")]
            ]
        else:
            details += f"⚠️ <i>This product is currently out of stock. Please contact support for restocking information.</i>"
            details += "</blockquote>"
            keyboard = [
                [InlineKeyboardButton(f"🔙 Back to {product['category']}", callback_data=f"cat_{product['category']}")]
            ]

        await query.edit_message_text(
            text=details,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data.startswith("buy_"):
        product_id = data.split("_")[1]
        
        try:
            response = supabase.table("products").select("*").eq("id", product_id).execute()
            product = response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error checking product: {str(e)}")
            product = None

        if not product:
            await query.edit_message_text("<blockquote>❌ Product not found.</blockquote>", parse_mode="HTML")
            return

        has_stock = False
        try:
            stock_check = supabase.table("credentials").select("id").eq("product_id", product_id).eq("status", "UNUSED").limit(1).execute()
            has_stock = bool(stock_check.data)
        except Exception as e:
            has_stock = False

        if not has_stock:
            await query.edit_message_text(
                text=(
                    f"<blockquote>"
                    f"❌ <b>OUT OF STOCK!</b>\n\n"
                    f"Sorry, <b>{product['name']}</b> is currently out of stock. "
                    f"No credentials are available for delivery right now.\n\n"
                    f"Please check back later or contact support for restocking updates."
                    f"</blockquote>"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
                ]),
                parse_mode="HTML"
            )
            return

        price = float(product["price"])
        emoji = get_product_emoji(product['name'])
        
        checkout_text = (
            f"⚠️ <b>PURCHASE CONFIRMATION</b> ⚠️\n\n"
            f"📦 <b>Product:</b> {emoji} {product['name']}\n"
            f"🔢 <b>Quantity:</b> 1\n"
            f"💵 <b>Base Total:</b> ₹{price:.2f}\n\n"
            f"💲 <b>FINAL DUE:</b> ₹{price:.2f}\n\n"
            f"Select payment method:"
        )

        keyboard = [
            [InlineKeyboardButton("👛 Pay with Wallet (₹0.00)", callback_data="alert_wallet")],
            [InlineKeyboardButton("🟨 Binance Pay / Crypto", callback_data="alert_crypto")],
            [InlineKeyboardButton("💳 Pay with Razorpay (Auto)", callback_data=f"rzpterms_{product['id']}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ]

        await query.edit_message_text(
            text=checkout_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data == "alert_wallet":
        await query.answer("❌ Wallet balance is ₹0.00! Please use Razorpay.", show_alert=True)
        return

    elif data == "alert_crypto":
        await query.answer("⏳ Binance Pay is currently under maintenance. Please use Razorpay.", show_alert=True)
        return

    elif data.startswith("rzpterms_"):
        product_id = data.split("_")[1]
        terms_text = (
            f"⚠️ <b>RAZORPAY TERMS & CONDITIONS</b> ⚠️\n\n"
            f"1. We use Razorpay for secure automated payments (Cards/UPI/Netbanking).\n"
            f"2. You MUST complete the payment on the next screen.\n"
            f"3. Do NOT modify the pre-filled amount in your UPI app.\n"
            f"4. No refunds will be provided for incorrect payments or useless reasons.\n\n"
            f"Do you agree to these terms?"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Agree", callback_data=f"rzpagree_{product_id}")],
            [InlineKeyboardButton("❌ Decline", callback_data="main_menu")]
        ]
        await query.edit_message_text(text=terms_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("rzpagree_"):
        product_id = data.split("_")[1]
        await query.edit_message_text("<blockquote>⏳ <i>Securing your order & generating payment gateway...</i></blockquote>", parse_mode="HTML")

        try:
            response = supabase.table("products").select("*").eq("id", product_id).execute()
            product = response.data[0] if response.data else None
        except Exception as e:
            product = None

        if not product:
            await query.edit_message_text("<blockquote>❌ Product not found.</blockquote>", parse_mode="HTML")
            return

        price = float(product["price"])
        from telegram_bot.services.payment_gateway import create_payment_link
        from telegram_bot.services.order_service import create_order
        
        pay_res = await create_payment_link(
            amount=price,
            product_name=product["name"],
            telegram_id=user.id,
            product_id=product["id"],
            first_name=user.first_name
        )

        if not pay_res.get("success"):
            await query.edit_message_text(
                text=f"<blockquote>❌ <b>Error generating payment link:</b>\n<code>{pay_res.get('error')}</code></blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
                parse_mode="HTML"
            )
            return

        payment_id = pay_res["payment_link_id"]
        short_url = pay_res["short_url"]

        create_order(
            telegram_id=user.id,
            product_id=product["id"],
            payment_id=payment_id,
            amount=price
        )

        checkout_text = (
            f"✅ <b>Order Generated Successfully!</b>\n\n"
            f"🔖 <b>Order Ref:</b> <code>{payment_id}</code>\n\n"
            f"Click the button below to pay securely. Once completed, your product will be delivered instantly."
        )

        keyboard = [
            [InlineKeyboardButton("🔗 Pay Securely via Razorpay", url=short_url)],
            [InlineKeyboardButton("❌ Cancel Order", callback_data="main_menu")]
        ]

        await query.edit_message_text(
            text=checkout_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data == "view_history":
        try:
            response = supabase.table("orders").select("*, products(*)").eq("telegram_id", user.id).order("created_at", desc=True).execute()
            orders = response.data
        except Exception as e:
            logger.error(f"Error fetching order history: {str(e)}")
            orders = []

        if not orders:
            await query.edit_message_text(
                text="<blockquote>📜 <b>ORDER HISTORY</b>\n\nYou haven't made any purchases yet. Start shopping to access premium products!</blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
                parse_mode="HTML"
            )
            return

        history_text = "<blockquote>📜 <b>YOUR RECENT ORDERS:</b>\n\n"
        for idx, order in enumerate(orders[:10], 1):
            prod = order.get("products") or {}
            prod_name = prod.get("name", "Unknown Product")
            
            if order.get("status") == "PENDING":
                status = "Pending Payment / Setup"
            else:
                status = "Delivered" if order.get("delivery_status") == "DELIVERED" else "Processing"
                
            history_text += f"{idx}. <b>{prod_name}</b>\n   💰 ₹{float(order.get('amount', 0)):.2f} | 📅 {order.get('created_at', '')[:10]}\n   🚚 Status: {status}\n\n"
            
        history_text += "</blockquote>"
            
        await query.edit_message_text(
            text=history_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
            parse_mode="HTML"
        )

    elif data == "view_support":
        support_text = (
            f"<blockquote>"
            f"ℹ️ <b>PREMIUM CUSTOMER SUPPORT</b> ℹ️\n\n"
            f"Experiencing an issue with a digital product or payment? Our elite support team is ready to assist you.\n\n"
            f"👤 <b>Admin Contact:</b> @ur_aurexia222\n\n"
            f"<i>Please provide your Order Reference ID when reaching out for the fastest resolution.</i>"
            f"</blockquote>"
        )
        keyboard = [
            [InlineKeyboardButton("💬 Chat with Admin", url="https://t.me/ur_aurexia222")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            text=support_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data == "write_review":
        context.user_data['awaiting_review'] = True
        review_text = (
            f"<blockquote>"
            f"🌟 <b>WE VALUE YOUR FEEDBACK!</b> 🌟\n\n"
            f"Please type your review below and send it to me. Your reviews help us improve our premium services!"
            f"</blockquote>"
        )
        await query.edit_message_text(
            text=review_text,
            parse_mode="HTML"
        )
