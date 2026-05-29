import os
import logging
import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from backend.services.supabase_service import (
    create_user_if_not_exists,
    get_db,
    create_order,
    get_unused_credential,
    get_wallet_balance,
    deduct_wallet_balance,
    refund_wallet_balance,
    get_wallet_transactions,
    mark_credential_used,
    update_order_completed
)
from telegram_bot.services.razorpay_service import create_payment_link

logger = logging.getLogger(__name__)

# Main Menu Layout
def get_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🛍️ Products", "👛 Wallet"],
        ["📝 Purchase History", "↗️ Support"]
    ], resize_keyboard=True)

def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🛍️ Products", callback_data="view_products"),
            InlineKeyboardButton("👛 Wallet", callback_data="view_wallet")
        ],
        [
            InlineKeyboardButton("📝 Purchase History", callback_data="view_history"),
            InlineKeyboardButton("↗️ Support", callback_data="view_support")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_channel_membership(user_id, context: ContextTypes.DEFAULT_TYPE):
    """Checks if the user is a member of the required channels."""
    # Temporarily bypassed as requested by user
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
            f"HI 🫲<tg-emoji emoji-id=\"5456258317477230911\">😎</tg-emoji>🫱 {html.escape(user.first_name)}\n"
            f"WELCOME TO <tg-emoji emoji-id=\"5217558900047359541\">🤖</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"𝐆𝐀𝐌𝐄𝐒 𝐀𝐍𝐃 𝐎𝐓𝐓 𝐁𝐎𝐓 <tg-emoji emoji-id=\"5895646210731019949\">➡️</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<tg-emoji emoji-id=\"5406745015365943482\">🔖</tg-emoji> QUICK GUIDE :\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝚃𝙰𝙿 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂' 𝙱𝚄𝚃𝚃𝙾𝙽.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝚃𝙰𝙿 '𝙾𝚃𝚃' 𝙾𝚁 '𝙶𝙰𝙼𝙴𝚂' 𝚃𝙾 𝙱𝚁𝙾𝚆𝚂𝙴 𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝙲𝙷𝙾𝙾𝚂𝙴 𝚃𝙷𝙴 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚈𝙾𝚄 𝚆𝙰𝙽𝚃.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴 𝚃𝙷𝙴 '𝙿𝙰𝚈𝙼𝙴𝙽𝚃'.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝚈𝙾𝚄𝚁 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚆𝙸𝙻𝙻 𝙱𝙴 𝙳𝙴𝙻𝙸𝚅𝙴𝚁𝙴𝙳 𝙸𝙽𝚂𝚃𝙰𝙽𝚃𝙻𝚈.\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"PLEASE CHOOSE A MENU BELOW <tg-emoji emoji-id=\"5222444124698853913\">⬇️</tg-emoji><tg-emoji emoji-id=\"5222444124698853913\">⬇️</tg-emoji><tg-emoji emoji-id=\"5222444124698853913\">⬇️</tg-emoji>"
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
                f"HI 🫲<tg-emoji emoji-id=\"5456258317477230911\">😎</tg-emoji>🫱 {html.escape(user.first_name)}\n"
                f"WELCOME TO <tg-emoji emoji-id=\"5217558900047359541\">🤖</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬\n"
                f"𝐆𝐀𝐌𝐄𝐒 𝐀𝐍𝐃 𝐎𝐓𝐓 𝐁𝐎𝐓 <tg-emoji emoji-id=\"5895646210731019949\">➡️</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬\n"
                f"<tg-emoji emoji-id=\"5406745015365943482\">🔖</tg-emoji> QUICK GUIDE :\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝚃𝙰𝙿 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂' 𝙱𝚄𝚃𝚃𝙾𝙽.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝚃𝙰𝙿 '𝙾𝚃𝚃' 𝙾𝚁 '𝙶𝙰𝙼𝙴𝚂' 𝚃𝙾 𝙱𝚁𝙾𝚆𝚂𝙴 𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝙲𝙷𝙾𝙾𝚂𝙴 𝚃𝙷𝙴 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚈𝙾𝚄 𝚆𝙰𝙽𝚃.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴 𝚃𝙷𝙴 '𝙿𝙰𝚈𝙼𝙴𝙽𝚃'.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">🔴</tg-emoji> 𝚈𝙾𝚄𝚁 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚆𝙸𝙻𝙻 𝙱𝙴 𝙳𝙴𝙻𝙸𝚅𝙴𝚁𝙴𝙳 𝙸𝙽𝚂𝚃𝙰𝙽𝚃𝙻𝚈.\n"
                f"▬▬▬▬▬▬▬▬▬▬▬\n"
                f"PLEASE CHOOSE A MENU BELOW <tg-emoji emoji-id=\"5222444124698853913\">⬇️</tg-emoji><tg-emoji emoji-id=\"5222444124698853913\">⬇️</tg-emoji><tg-emoji emoji-id=\"5222444124698853913\">⬇️</tg-emoji>"
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
            f"HI 🫲😀🫱 {html.escape(user.first_name)}\n"
            f"WELCOME TO 🎬\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"𝐆𝐀𝐌𝐄𝐒 𝐀𝐍𝐃 𝐎𝐓𝐓 𝐁𝐎𝐓\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📌 QUICK GUIDE :\n"
            f"🔖 𝚃𝙰𝙿 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂' 𝙱𝚄𝚃𝚃𝙾𝙽.\n"
            f"🔖 𝚃𝙰𝙿 '𝙾𝚃𝚃' 𝙾𝚁 '𝙶𝙰𝙼𝙴𝚂' 𝚃𝙾 𝙱𝚁𝙾𝚆𝚂𝙴 𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂.\n"
            f"🔖 𝙲𝙷𝙾𝙾𝚂𝙴 𝚃𝙷𝙴 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚈𝙾𝚄 𝚆𝙰𝙽𝚃.\n"
            f"🔖 𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴 𝚃𝙷𝙴 '𝙿𝙰𝚈𝙼𝙴𝙽𝚃'.\n"
            f"🔖 𝚈𝙾𝚄𝚁 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚆𝙸𝙻𝙻 𝙱𝙴 𝙳𝙴𝙻𝙸𝚅𝙴𝚁𝙴𝙳 𝙸𝙽𝚂𝚃𝙰𝙽𝚃𝙻𝚈.\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📌 PLEASE CHOOSE A MENU BELOW 👇👇👇"
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
        wallet_balance = get_wallet_balance(user.id)
        
        checkout_text = (
            f"⚠️ <b>PURCHASE CONFIRMATION</b> ⚠️\n\n"
            f"📦 <b>Product:</b> {emoji} {product['name']}\n"
            f"🔢 <b>Quantity:</b> 1\n"
            f"💵 <b>Base Total:</b> ₹{price:.2f}\n\n"
            f"💲 <b>FINAL DUE:</b> ₹{price:.2f}\n\n"
            f"👛 <b>Wallet Balance:</b> ₹{wallet_balance:.2f}\n\n"
            f"Select payment method:"
        )

        keyboard = []
        if wallet_balance >= price:
            keyboard.append([InlineKeyboardButton(f"👛 Pay with Wallet (₹{wallet_balance:.2f})", callback_data=f"walletpay_{product['id']}")] )
        else:
            keyboard.append([InlineKeyboardButton(f"👛 Wallet (₹{wallet_balance:.2f}) — Insufficient", callback_data="alert_wallet")])
        keyboard.append([InlineKeyboardButton("💳 Pay with Razorpay (Auto)", callback_data=f"rzpterms_{product['id']}")])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="main_menu")])

        await query.edit_message_text(
            text=checkout_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data == "alert_wallet":
        await query.answer("❌ Insufficient wallet balance! Add funds first or use Razorpay.", show_alert=True)
        return

    elif data.startswith("walletpay_"):
        product_id = data.split("_")[1]
        try:
            response = supabase.table("products").select("*").eq("id", product_id).execute()
            product = response.data[0] if response.data else None
        except Exception as e:
            product = None

        if not product:
            await query.edit_message_text("❌ Product not found.", parse_mode="HTML")
            return

        price = float(product["price"])
        wallet_balance = get_wallet_balance(user.id)

        if wallet_balance < price:
            await query.answer(f"❌ Insufficient balance! You have ₹{wallet_balance:.2f} but need ₹{price:.2f}.", show_alert=True)
            return

        # Deduct from wallet
        success = deduct_wallet_balance(
            telegram_id=user.id,
            amount=price,
            description=f"Purchase: {product['name']}"
        )

        if not success:
            await query.answer("❌ Wallet deduction failed. Try again.", show_alert=True)
            return

        # Create a wallet-based order
        order_data = create_order(
            telegram_id=user.id,
            product_id=product["id"],
            payment_id=f"WALLET_{user.id}_{int(__import__('time').time())}",
            amount=price
        )

        if not order_data:
            # Refund if order creation failed
            refund_wallet_balance(user.id, price, description=f"Refund: Order creation failed for {product['name']}")
            await query.edit_message_text("❌ Order creation failed. Your wallet has been refunded.", parse_mode="HTML")
            return

        # Try to deliver credentials immediately
        credential = get_unused_credential(product["id"])
        if credential:
            mark_credential_used(credential["id"])
            update_order_completed(order_data["id"], "AWAITING_EMAIL_GAMES")

            msg = (
                f"🎉 <b>WALLET PAYMENT SUCCESSFUL!</b> 🎉\n\n"
                f"Thank you for purchasing <b>{product['name']}</b>!\n\n"
                f"💰 <b>Amount Paid:</b> ₹{price:.2f} (from Wallet)\n"
                f"👛 <b>Remaining Balance:</b> ₹{get_wallet_balance(user.id):.2f}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📧 <b>NEXT STEP — SEND YOUR EMAIL</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"To receive your credentials securely, "
                f"please <b>type and send your email address</b> in this chat right now.\n\n"
                f"Your login ID and password will be delivered here instantly and also sent to your email! 🚀"
            )
            await query.edit_message_text(text=msg, parse_mode="HTML")
        else:
            # Out of stock — AUTO REFUND
            refund_wallet_balance(
                telegram_id=user.id,
                amount=price,
                reference_id=order_data["id"],
                description=f"Auto-refund: {product['name']} out of stock"
            )
            update_order_completed(order_data["id"], "MANUAL_PROCESSING")

            msg = (
                f"❌ <b>OUT OF STOCK!</b>\n\n"
                f"Sorry, <b>{product['name']}</b> is currently out of stock.\n\n"
                f"💰 <b>₹{price:.2f} has been automatically refunded</b> to your wallet.\n"
                f"👛 <b>Current Balance:</b> ₹{get_wallet_balance(user.id):.2f}\n\n"
                f"Please try again later or contact support."
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
            await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data == "view_wallet":
        balance = get_wallet_balance(user.id)
        wallet_text = (
            f"👛 𝐌𝐘 𝐖𝐀𝐋𝐋𝐄𝐓\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"💰 <b>Current Balance:</b> ₹{balance:.2f}\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📌 Add funds to your wallet for instant one-tap purchases!\n"
            f"Minimum deposit: ₹100.00"
        )
        keyboard = [
            [InlineKeyboardButton("➕ Add Funds", callback_data="wallet_deposit")],
            [InlineKeyboardButton("🧾 Transaction History", callback_data="wallet_history")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        await query.edit_message_text(text=wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data == "wallet_deposit":
        deposit_text = (
            f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> 𝐀𝐃𝐃 𝐅𝐔𝐍𝐃𝐒\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"Choose an amount to deposit into your wallet:\n\n"
            f"Minimum: ₹100 | Maximum: ₹10,000\n"
            f"▬▬▬▬▬▬▬▬▬▬▬"
        )
        keyboard = [
            [
                InlineKeyboardButton("₹100", callback_data="deposit_100"),
                InlineKeyboardButton("₹200", callback_data="deposit_200"),
                InlineKeyboardButton("₹500", callback_data="deposit_500")
            ],
            [
                InlineKeyboardButton("₹1000", callback_data="deposit_1000"),
                InlineKeyboardButton("₹2000", callback_data="deposit_2000"),
                InlineKeyboardButton("₹5000", callback_data="deposit_5000")
            ],
            [InlineKeyboardButton("🔙 Back to Wallet", callback_data="view_wallet")]
        ]
        await query.edit_message_text(text=deposit_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data.startswith("deposit_"):
        amount = int(data.split("_")[1])
        if amount < 100:
            await query.answer("❌ Minimum deposit is ₹100!", show_alert=True)
            return

        await query.edit_message_text("<blockquote>⏳ <i>Generating secure payment link for wallet deposit...</i></blockquote>", parse_mode="HTML")

        from telegram_bot.services.razorpay_service import create_deposit_payment_link
        pay_res = await create_deposit_payment_link(
            amount=float(amount),
            telegram_id=user.id,
            first_name=user.first_name
        )

        if not pay_res.get("success"):
            await query.edit_message_text(
                text=f"❌ <b>Error generating deposit link:</b>\n<code>{pay_res.get('error')}</code>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Wallet", callback_data="view_wallet")]]),
                parse_mode="HTML"
            )
            return

        short_url = pay_res["short_url"]
        deposit_confirm_text = (
            f"✅ <b>Deposit Link Generated!</b>\n\n"
            f"💰 <b>Amount:</b> ₹{amount:.2f}\n\n"
            f"Click the button below to complete your deposit securely via Razorpay.\n"
            f"Your wallet will be credited instantly after payment confirmation."
        )
        keyboard = [
            [InlineKeyboardButton("🔗 Pay & Deposit via Razorpay", url=short_url)],
            [InlineKeyboardButton("❌ Cancel", callback_data="view_wallet")]
        ]
        await query.edit_message_text(text=deposit_confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data == "wallet_history":
        transactions = get_wallet_transactions(user.id, limit=10)
        if not transactions:
            await query.edit_message_text(
                text="🧾 <b>TRANSACTION HISTORY</b>\n\nNo transactions yet. Add funds to get started!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Wallet", callback_data="view_wallet")]]),
                parse_mode="HTML"
            )
            return

        history_text = "🧾 𝐓𝐑𝐀𝐍𝐒𝐀𝐂𝐓𝐈𝐎𝐍 𝐇𝐈𝐒𝐓𝐎𝐑𝐘\n▬▬▬▬▬▬▬▬▬▬▬\n\n"
        for idx, txn in enumerate(transactions, 1):
            t_type = txn.get("transaction_type", "")
            if t_type == "DEPOSIT":
                emoji = "➕"
                sign = "+"
            elif t_type == "PURCHASE":
                emoji = "🛒"
                sign = "-"
            elif t_type == "REFUND":
                emoji = "↩️"
                sign = "+"
            else:
                emoji = "📌"
                sign = ""
            
            desc = txn.get("description", t_type)
            date = txn.get("created_at", "")[:10]
            amount = float(txn.get("amount", 0))
            history_text += f"{idx}. {emoji} {sign}₹{amount:.2f}\n   {desc}\n   📅 {date}\n\n"

        keyboard = [[InlineKeyboardButton("🔙 Back to Wallet", callback_data="view_wallet")]]
        await query.edit_message_text(text=history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
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
            f"🎧 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐂𝐔𝐒𝐓𝐎𝐌𝐄𝐑 𝐒𝐔𝐏𝐏𝐎𝐑𝐓\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"Need help with your digital products or payments? Our elite support team is ready to assist you 24/7.\n\n"
            f"👨‍💻 𝗔𝗱𝗺𝗶𝗻 𝗖𝗼𝗻𝘁𝗮𝗰𝘁: @ur_aurexia222\n\n"
            f"📌 𝘗𝘭𝘦𝘢𝘴𝘦 𝘬𝘦𝘦𝘱 𝘺𝘰𝘶𝘳 𝘖𝘳𝘥𝘦𝘳 𝘐𝘋 𝘳𝘦𝘢𝘥𝘺 𝘧𝘰𝘳 𝘧𝘢𝘴𝘵𝘦𝘳 𝘳𝘦𝘴𝘰𝘭𝘶𝘵𝘪𝘰𝘯.\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n"
            f"👇 Click the button below to start a live chat"
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
