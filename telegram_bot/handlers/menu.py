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
            InlineKeyboardButton("🛍 Products", callback_data="view_products"),
            InlineKeyboardButton("👛 Wallet", callback_data="view_wallet")
        ],
        [
            InlineKeyboardButton("📋 Purchase History", callback_data="view_history"),
            InlineKeyboardButton("🔄 Support", callback_data="view_support")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def check_channel_membership(user_id, context: ContextTypes.DEFAULT_TYPE):
    """Checks if the user is a member of the required channels."""
    try:
        member = await context.bot.get_chat_member(chat_id="@Growixx_store", user_id=user_id)
        if member.status in ['member', 'administrator', 'creator', 'restricted']:
            return True
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
    return False

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
            f"<b>JOIN OUR CHANNEL</b> <tg-emoji emoji-id=\"5456140674028019486\">✅</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"Hello <b>{html.escape(user.first_name)}</b>! To unlock our automated instant delivery of gaming credentials and premium OTT services, you must join our official channel.\n\n"
            f"<tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji> <i>Please join the channel below:</i>"
        )
        keyboard = [
            [InlineKeyboardButton("🚀 Join Channel 🚀", url="https://t.me/Growixx_store")],
            [InlineKeyboardButton("✅ I've Joined", callback_data="check_joined")]
        ]
        await update.message.reply_text(
            text=banner,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    banner = (
            f"<b>HI</b> 🫲<tg-emoji emoji-id=\"5456258317477230911\">😎</tg-emoji>🫱 <b>{html.escape(user.first_name)}</b>\n"
            f"<b>WELCOME TO</b> <tg-emoji emoji-id=\"5352625743081775722\">🔘</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"𝐆𝐀𝐌𝐄𝐒 𝐀𝐍𝐃 𝐎𝐓𝐓 𝐁𝐎𝐓 <tg-emoji emoji-id=\"5314391089514291948\">🤖</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<tg-emoji emoji-id=\"5222444124698853913\">🔖</tg-emoji> <b><u>QUICK GUIDE</u> :</b>\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚃𝙰𝙿 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂' 𝙱𝚄𝚃𝚃𝙾𝙽.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚃𝙰𝙿 '𝙾𝚃𝚃' 𝙾𝚁 '𝙶𝙰𝙼𝙴𝚂' 𝚃𝙾 𝙱𝚁𝙾𝚆𝚂𝙴 𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝙲𝙷𝙾𝙾𝚂𝙴 𝚃𝙷𝙴 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚈𝙾𝚄 𝚆𝙰𝙽𝚃.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴 𝚃𝙷𝙴 '𝙿𝙰𝚈𝙼𝙴𝙽𝚃'.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚈𝙾𝚄𝚁 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚆𝙸𝙻𝙻 𝙱𝙴 𝙳𝙴𝙻𝙸𝚅𝙴𝚁𝙴𝙳 𝙸𝙽𝚂𝚃𝙰𝙽𝚃𝙻𝚈.\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<b>PLEASE CHOOSE A MENU BELOW</b>\n"
            f"<tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji>"
        )

    # Send the bottom reply keyboard first
    await update.message.reply_text(
        text="Loading interface...",
        reply_markup=get_reply_keyboard()
    )
    try:
        # Then send the main menu with inline buttons
        await update.message.reply_text(
            text=banner,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send banner: {e}")
        await update.message.reply_text(
            text=f"⚠️ Interface Error: {str(e)}\n\nFallback Menu:",
            reply_markup=get_main_menu_keyboard()
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
        empty_text = (
            f"<b>PURCHASE HISTORY</b> <tg-emoji emoji-id=\"4938318633475507037\">📜</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"YOU HAVEN'T MADE ANY PURCHASES YET. START SHOPPING TO ACCESS PREMIUM PRODUCTS! 🛒\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
        )
        await update.message.reply_text(
            text=empty_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
            parse_mode="HTML"
        )
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
    
    await update.message.reply_text(
        text=history_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
        parse_mode="HTML"
    )

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /support command."""
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
    keyboard = [
        [InlineKeyboardButton("💬 Chat with Admin", url="https://t.me/ur_Growixx222")],
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
    if 'youtube' in n or 'yt' in n: return '▶️'
    if 'spotify' in n or 'spofy' in n: return '🟢'
    if 'amazon' in n or 'prime' in n: return '🔵'
    if 'disney' in n or 'hotstar' in n: return '🟡'
    if 'steam' in n or 'syeam' in n: return '🎮'
    if 'zee5' in n: return '🟣'
    if 'sony' in n or 'liv' in n: return '🟠'
    if 'chatgpt' in n: return '🤖'
    if 'capcut' in n or 'captcut' in n: return '✂️'
    if 'google' in n: return '☁️'
    if 'canva' in n or 'anva' in n: return '🖌️'
    if 'crunchyroll' in n: return '🟠'
    if 'claude' in n: return '🧠'
    if 'adobe' in n or 'creative' in n: return '🎨'
    if 'picsart' in n: return '🎨'
    return '🔹'

def get_product_animated_emoji(name):
    n = name.lower()
    if 'netflix' in n: return '<tg-emoji emoji-id="5318911503938634641">🔴</tg-emoji>'
    if 'youtube' in n or 'yt' in n: return '<tg-emoji emoji-id="5334681713316479679">▶️</tg-emoji>'
    if 'spotify' in n or 'spofy' in n: return '<tg-emoji emoji-id="5346074681004801565">🟢</tg-emoji>'
    if 'amazon' in n or 'prime' in n: return '<tg-emoji emoji-id="5346056560537779652">🔵</tg-emoji>'
    if 'disney' in n or 'hotstar' in n: return '<tg-emoji emoji-id="5332394707655869572">🟡</tg-emoji>'
    if 'steam' in n or 'syeam' in n: return '<tg-emoji emoji-id="5373144051690258848">🎮</tg-emoji>'
    if 'zee5' in n: return '<tg-emoji emoji-id="6327648409503142865">🟣</tg-emoji>'
    if 'sony' in n or 'liv' in n: return '<tg-emoji emoji-id="6327725937957801811">🟠</tg-emoji>'
    if 'chatgpt' in n: return '<tg-emoji emoji-id="5359726582447487916">🤖</tg-emoji>'
    if 'capcut' in n or 'captcut' in n: return '<tg-emoji emoji-id="5364339557712020484">✂️</tg-emoji>'
    if 'google' in n: return '<tg-emoji emoji-id="5875095634033250205">☁️</tg-emoji>'
    if 'canva' in n or 'anva' in n: return '<tg-emoji emoji-id="5879982576671657703">🖌️</tg-emoji>'
    if 'crunchyroll' in n: return '<tg-emoji emoji-id="6231196182907983273">🟠</tg-emoji>'
    if 'claude' in n: return '<tg-emoji emoji-id="5899837428797020489">🧠</tg-emoji>'
    if 'adobe' in n or 'creative' in n: return '<tg-emoji emoji-id="5879753496000991296">🎨</tg-emoji>'
    if 'picsart' in n: return '<tg-emoji emoji-id="5877624510777135360">🎨</tg-emoji>'
    return '<tg-emoji emoji-id="5352625743081775722">🔹</tg-emoji>'

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes all inline button clicks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user
    supabase = get_db()
    
    if data != "check_joined":
        is_member = await check_channel_membership(user.id, context)
        if not is_member:
            await query.answer("❌ You must join our channel to use the bot!", show_alert=True)
            banner = (
                f"<b>JOIN OUR CHANNEL</b> <tg-emoji emoji-id=\"5456140674028019486\">✅</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"You must join our official channel to continue using the bot.\n\n"
                f"<tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji> <i>Please join the channel below:</i>"
            )
            keyboard = [
                [InlineKeyboardButton("🚀 Join Channel 🚀", url="https://t.me/Growixx_store")],
                [InlineKeyboardButton("✅ I've Joined", callback_data="check_joined")]
            ]
            await query.edit_message_text(
                text=banner,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return

    if data == "coming_soon":
        await query.answer("⏳ This feature is coming soon!", show_alert=True)
        return

    if data == "view_products":
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
        await query.edit_message_text(
            text=products_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
        return

    if data == "check_joined":
        is_member = await check_channel_membership(user.id, context)
        if is_member:
            banner = (
                f"<b>HI</b> 🫲<tg-emoji emoji-id=\"5456258317477230911\">😎</tg-emoji>🫱 <b>{html.escape(user.first_name)}</b>\n"
                f"<b>WELCOME TO</b> <tg-emoji emoji-id=\"5352625743081775722\">🔘</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"𝐆𝐀𝐌𝐄𝐒 𝐀𝐍𝐃 𝐎𝐓𝐓 𝐁𝐎𝐓 <tg-emoji emoji-id=\"5314391089514291948\">🤖</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"<tg-emoji emoji-id=\"5222444124698853913\">🔖</tg-emoji> <b><u>QUICK GUIDE</u> :</b>\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚃𝙰𝙿 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂' 𝙱𝚄𝚃𝚃𝙾𝙽.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚃𝙰𝙿 '𝙾𝚃𝚃' 𝙾𝚁 '𝙶𝙰𝙼𝙴𝚂' 𝚃𝙾 𝙱𝚁𝙾𝚆𝚂𝙴 𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝙲𝙷𝙾𝙾𝚂𝙴 𝚃𝙷𝙴 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚈𝙾𝚄 𝚆𝙰𝙽𝚃.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴 𝚃𝙷𝙴 '𝙿𝙰𝚈𝙼𝙴𝙽𝚃'.\n"
                f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚈𝙾𝚄𝚁 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚆𝙸𝙻𝙻 𝙱𝙴 𝙳𝙴𝙻𝙸𝚅𝙴𝚁𝙴𝙳 𝙸𝙽𝚂𝚃𝙰𝙽𝚃𝙻𝚈.\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"<b>PLEASE CHOOSE A MENU BELOW</b>\n"
                f"<tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji>"
            )
            try:
                await query.message.reply_text(
                    text="Loading interface...",
                    reply_markup=get_reply_keyboard()
                )
                await query.edit_message_text(
                    text=banner,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
            except Exception as e:
                await query.edit_message_text(
                    text=f"⚠️ Interface Error: {str(e)}\n\nFallback Menu:",
                    reply_markup=get_main_menu_keyboard()
                )
        else:
            await query.answer("❌ First join the channel!", show_alert=True)
            banner = (
                f"<b>ACCESS DENIED</b> <tg-emoji emoji-id=\"5456140674028019486\">✅</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"You haven't joined our channel yet! First join the channel to continue.\n\n"
                f"<tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji> <i>Please join the channel below:</i>"
            )
            keyboard = [
                [InlineKeyboardButton("🚀 Join Channel 🚀", url="https://t.me/Growixx_store")],
                [InlineKeyboardButton("✅ I've Joined", callback_data="check_joined")]
            ]
            await query.edit_message_text(
                text=banner,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            
    elif data == "main_menu":
        # Clear any pending conversational states
        context.user_data.pop('awaiting_product_selection', None)
        context.user_data.pop('awaiting_quantity_for_product', None)
        
        banner = (
            f"<b>HI</b> 🫲<tg-emoji emoji-id=\"5456258317477230911\">😎</tg-emoji>🫱 <b>{html.escape(user.first_name)}</b>\n"
            f"<b>WELCOME TO</b> <tg-emoji emoji-id=\"5352625743081775722\">🔘</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"𝐆𝐀𝐌𝐄𝐒 𝐀𝐍𝐃 𝐎𝐓𝐓 𝐁𝐎𝐓 <tg-emoji emoji-id=\"5314391089514291948\">🤖</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<tg-emoji emoji-id=\"5222444124698853913\">🔖</tg-emoji> <b><u>QUICK GUIDE</u> :</b>\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚃𝙰𝙿 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂' 𝙱𝚄𝚃𝚃𝙾𝙽.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚃𝙰𝙿 '𝙾𝚃𝚃' 𝙾𝚁 '𝙶𝙰𝙼𝙴𝚂' 𝚃𝙾 𝙱𝚁𝙾𝚆𝚂𝙴 𝙿𝚁𝙾𝙳𝚄𝙲𝚃𝚂.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝙲𝙷𝙾𝙾𝚂𝙴 𝚃𝙷𝙴 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚈𝙾𝚄 𝚆𝙰𝙽𝚃.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝙲𝙾𝙼𝙿𝙻𝙴𝚃𝙴 𝚃𝙷𝙴 '𝙿𝙰𝚈𝙼𝙴𝙽𝚃'.\n"
            f"<tg-emoji emoji-id=\"5346105514575025401\">▶️</tg-emoji> 𝚈𝙾𝚄𝚁 '𝙿𝚁𝙾𝙳𝚄𝙲𝚃' 𝚆𝙸𝙻𝙻 𝙱𝙴 𝙳𝙴𝙻𝙸𝚅𝙴𝚁𝙴𝙳 𝙸𝙽𝚂𝚃𝙰𝙽𝚃𝙻𝚈.\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"<b>PLEASE CHOOSE A MENU BELOW</b>\n"
            f"<tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji>"
        )
        try:
            await query.edit_message_text(
                text=banner,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            await query.edit_message_text(
                text=f"⚠️ Interface Error: {str(e)}\n\nFallback Menu:",
                reply_markup=get_main_menu_keyboard()
            )

    elif data.startswith("cat_"):
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

        # Store the category in user_data to track state
        context.user_data['awaiting_product_selection'] = category

        list_text = (
            f"<b>{category.upper()} CATALOG</b> 🛒\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        )

        for prod in products:
            emoji = get_product_animated_emoji(prod['name'])
            list_text += f"{emoji} <b>{prod['name']}</b>\n\n"
        
        category_examples = {
            "OTT": "Netflix",
            "Games": "Steam",
            "AI": "ChatGPT",
            "VideoEditing": "CapCut"
        }
        example_prod = category_examples.get(category, "Netflix")

        list_text += (
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"<tg-emoji emoji-id=\"5344036847871865919\">⌨️</tg-emoji> <b>Please TYPE the name of the product you want to buy below:</b>\n"
            f"<i>(Example: {example_prod})</i>"
        )

        keyboard = [[InlineKeyboardButton("🔙 Back to Products", callback_data="view_products")]]

        await query.edit_message_text(
            text=list_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data.startswith("type_again_"):
        category = data.split("type_again_")[1]
        context.user_data['awaiting_product_selection'] = category
        category_examples = {
            "OTT": "Netflix",
            "Games": "Steam",
            "AI": "ChatGPT",
            "VideoEditing": "CapCut"
        }
        example_prod = category_examples.get(category, "Netflix")
        prompt = (
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"<tg-emoji emoji-id=\"5344036847871865919\">⌨️</tg-emoji> <b>Please TYPE the name of the product you want to buy below:</b>\n"
            f"<i>(Example: {example_prod})</i>"
        )
        await query.edit_message_text(
            text=prompt,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Products", callback_data=f"cat_{category}")]]),
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
        stock_by_duration = {1: 0, 3: 0, 6: 0}
        
        try:
            stock_resp = supabase.table("credentials").select("id, subscription_months").eq("product_id", product["id"]).eq("status", "UNUSED").execute()
            if stock_resp.data:
                stock_count = len(stock_resp.data)
                for cred in stock_resp.data:
                    m = cred.get("subscription_months")
                    if m in stock_by_duration:
                        stock_by_duration[m] += 1
            else:
                stock_count = 0
        except Exception as e:
            logger.error(f"Error checking stock: {str(e)}")
            stock_count = 0

        is_in_stock = stock_count > 0

        if not is_in_stock:
            await query.answer("❌ OUT OF STOCK", show_alert=True)
            return

        stock_label = f"✅ In Stock ({stock_count} available)"

        anim_emoji = get_product_animated_emoji(product['name'])

        details = (
            f"<b>PRODUCT DETAIL</b> 📦\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"🏷️ <b>Name:</b> {anim_emoji} <b>{product['name']}</b>\n"
            f"🗂️ <b>Category:</b> <b>{product['category']}</b>\n"
        )
        if product['category'] == 'OTT':
            details += (
                f"💰 <b>1 Month:</b> ₹{float(product.get('price_1m') or 0):.2f}\n"
                f"💰 <b>3 Months:</b> ₹{float(product.get('price_3m') or 0):.2f}\n"
                f"💰 <b>6 Months:</b> ₹{float(product.get('price_6m') or 0):.2f}\n"
            )
        else:
            details += f"💰 <b>Price:</b> ₹{float(product['price']):.2f}\n"
        
        details += (
            f"⚡ <b>Delivery:</b> ✨ INSTANT AUTO-DELIVERY ✨\n"
            f"📊 <b>Stock Status:</b> {stock_label}\n\n"
        )

        details += f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        details += f"🛒 <i>Ready to purchase? Please select an option below:</i>\n"
        details += f"<tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji><tg-emoji emoji-id=\"5406745015365943482\">⬇️</tg-emoji>"
        
        keyboard = []
        if product['category'] == 'OTT':
            if stock_by_duration[1] > 0:
                keyboard.append([InlineKeyboardButton(f"💳 Buy 1 Month (₹{float(product.get('price_1m') or 0):.2f})", callback_data=f"buy_{product['id']}_1")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ 1 Month (Out of Stock)", callback_data="ignore")])
                
            if stock_by_duration[3] > 0:
                keyboard.append([InlineKeyboardButton(f"💳 Buy 3 Months (₹{float(product.get('price_3m') or 0):.2f})", callback_data=f"buy_{product['id']}_3")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ 3 Months (Out of Stock)", callback_data="ignore")])
                
            if stock_by_duration[6] > 0:
                keyboard.append([InlineKeyboardButton(f"💳 Buy 6 Months (₹{float(product.get('price_6m') or 0):.2f})", callback_data=f"buy_{product['id']}_6")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ 6 Months (Out of Stock)", callback_data="ignore")])
        else:
            keyboard.append([InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{product['id']}_0")])
            
        keyboard.append([InlineKeyboardButton(f"🔙 Back to {product['category']}", callback_data=f"cat_{product['category']}")])

        await query.edit_message_text(
            text=details,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data == "ignore":
        await query.answer("❌ This duration is currently out of stock.", show_alert=True)
        return

    elif data.startswith("buy_"):
        parts = data.split("_")
        product_id = parts[1]
        months = int(parts[2]) if len(parts) > 2 else 0
        
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
            q = supabase.table("credentials").select("id").eq("product_id", product_id).eq("status", "UNUSED")
            if product["category"] == "OTT" and months > 0:
                q = q.eq("subscription_months", months)
            stock_check = q.limit(1).execute()
            has_stock = bool(stock_check.data)
        except Exception as e:
            has_stock = False

        if not has_stock:
            duration_text = f" ({months} Months)" if product["category"] == "OTT" and months > 0 else ""
            await query.edit_message_text(
                text=(
                    f"<blockquote>"
                    f"❌ <b>OUT OF STOCK!</b>\n\n"
                    f"Sorry, <b>{product['name']}{duration_text}</b> is currently out of stock. "
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

        context.user_data['awaiting_quantity_for_product'] = product
        context.user_data['awaiting_quantity_duration'] = months
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]]
        
        duration_text = f" ({months} Months)" if product["category"] == "OTT" and months > 0 else ""
        
        await query.edit_message_text(
            f"✅ <b>{product['name']}{duration_text}</b> is in stock!\n\n"
            f"📦 <b>Available Accounts:</b> {len(stock_check.data) if stock_check.data else 0}\n\n"
            f"<tg-emoji emoji-id=\"5344036847871865919\">⌨️</tg-emoji> <b>How many accounts do you want to buy?</b>\n"
            f"<i>(Type a number, e.g., 1 or 2)</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data == "alert_wallet":
        await query.answer("❌ Insufficient wallet balance! Add funds first or use Razorpay.", show_alert=True)
        return

    elif data.startswith("walletpay_"):
        parts = data.split("_")
        product_id = parts[1]
        
        if len(parts) > 3:
            months = int(parts[2])
            qty = int(parts[3])
        else:
            months = 0
            qty = int(parts[2]) if len(parts) > 2 else 1
        
        try:
            response = supabase.table("products").select("*").eq("id", product_id).execute()
            product = response.data[0] if response.data else None
        except Exception as e:
            product = None

        if not product:
            await query.edit_message_text("❌ Product not found.", parse_mode="HTML")
            return

        if product["category"] == "OTT" and months > 0:
            price = float(product.get(f"price_{months}m") or 0) * qty
        else:
            price = float(product["price"]) * qty
            
        wallet_balance = get_wallet_balance(user.id)

        if wallet_balance < price:
            await query.answer(f"❌ Insufficient balance! You have ₹{wallet_balance:.2f} but need ₹{price:.2f}.", show_alert=True)
            return

        # Deduct from wallet
        success = deduct_wallet_balance(
            telegram_id=user.id,
            amount=price,
            description=f"Purchase: {product['name']} (x{qty})"
        )

        if not success:
            await query.answer("❌ Wallet deduction failed. Try again.", show_alert=True)
            return

        # Create a wallet-based order
        order_data = create_order(
            telegram_id=user.id,
            product_id=product["id"],
            payment_id=f"WALLET_{user.id}_{int(__import__('time').time())}_{qty}",
            amount=price,
            quantity=qty,
            subscription_months=months
        )

        if not order_data:
            # Refund if order creation failed
            refund_wallet_balance(user.id, price, description=f"Refund: Order creation failed for {product['name']}")
            await query.edit_message_text("❌ Order creation failed. Your wallet has been refunded.", parse_mode="HTML")
            return

        # Request email
        update_order_completed(order_data["id"], "AWAITING_EMAIL_GAMES")

        msg = (
            f"🎉 <b>WALLET PAYMENT SUCCESSFUL!</b> 🎉\n\n"
            f"Thank you for purchasing <b>{qty}x {product['name']}</b>!\n\n"
            f"💰 <b>Amount Paid:</b> ₹{price:.2f} (from Wallet)\n"
            f"👛 <b>Remaining Balance:</b> ₹{get_wallet_balance(user.id):.2f}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 <b>NEXT STEP — SEND YOUR EMAIL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"To receive your {qty} credentials securely, "
            f"please <b>type and send your email address</b> in this chat right now.\n\n"
            f"Your login details will be delivered here instantly and also sent to your email! 🚀"
        )
        await query.edit_message_text(text=msg, parse_mode="HTML")
        return

    elif data == "view_wallet":
        context.user_data.pop('awaiting_manual_deposit', None)
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
        await query.edit_message_text(text=wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data == "wallet_deposit":
        deposit_text = (
            f"<tg-emoji emoji-id=\"5206607081334906820\">✅</tg-emoji> 𝐀𝐃𝐃 𝐅𝐔𝐍𝐃𝐒\n"
            f"▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"Choose an amount to deposit into your wallet:\n\n"
            f"Minimum: ₹1 | Maximum: ₹10,000\n"
            f"▬▬▬▬▬▬▬▬▬▬▬"
        )
        keyboard = [
            [
                InlineKeyboardButton("₹1", callback_data="deposit_1"),
                InlineKeyboardButton("₹10", callback_data="deposit_10"),
                InlineKeyboardButton("₹50", callback_data="deposit_50")
            ],
            [
                InlineKeyboardButton("₹100", callback_data="deposit_100"),
                InlineKeyboardButton("₹500", callback_data="deposit_500"),
                InlineKeyboardButton("₹1000", callback_data="deposit_1000")
            ],
            [InlineKeyboardButton("✍️ Type Custom Amount", callback_data="manual_deposit")],
            [InlineKeyboardButton("🔙 Back to Wallet", callback_data="view_wallet")]
        ]
        await query.edit_message_text(text=deposit_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    elif data == "manual_deposit":
        context.user_data['awaiting_manual_deposit'] = True
        prompt = (
            f"✍️ <b>MANUAL DEPOSIT</b>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"Please type the amount you want to deposit below:\n"
            f"<i>(Example: 150)</i>"
        )
        await query.edit_message_text(
            text=prompt,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="view_wallet")]]),
            parse_mode="HTML"
        )
        return

    elif data.startswith("deposit_"):
        amount = int(data.split("_")[1])
        if amount < 1:
            await query.answer("❌ Minimum deposit is ₹1!", show_alert=True)
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
            f"<b>DEPOSIT INITIATED</b> <tg-emoji emoji-id=\"6230853345733510932\">💰</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"<b>Amount:</b> ₹{amount:.2f}\n\n"
            f"<i>Click the button below to complete your deposit securely via Razorpay.\n"
            f"Your wallet will be credited instantly after payment confirmation.</i>"
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
            text = (
                f"<b>TRANSACTION HISTORY</b> <tg-emoji emoji-id=\"5940804519083383006\">📜</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
                f"<i>No transactions yet. Add funds to get started!</i>"
            )
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Wallet", callback_data="view_wallet")]]),
                parse_mode="HTML"
            )
            return

        history_text = (
            f"<b>TRANSACTION HISTORY</b> <tg-emoji emoji-id=\"5940804519083383006\">📜</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
        )
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
        parts = data.split("_")
        product_id = parts[1]
        
        if len(parts) > 3:
            months = int(parts[2])
            qty = int(parts[3])
        else:
            months = 0
            qty = int(parts[2]) if len(parts) > 2 else 1
            
        terms_text = (
            f"⚠️ <b>RAZORPAY TERMS & CONDITIONS</b> ⚠️\n\n"
            f"1. We use Razorpay for secure automated payments (Cards/UPI/Netbanking).\n"
            f"2. You MUST complete the payment on the next screen.\n"
            f"3. Do NOT modify the pre-filled amount in your UPI app.\n"
            f"4. No refunds will be provided for incorrect payments or useless reasons.\n\n"
            f"Do you agree to these terms?"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Agree", callback_data=f"rzpagree_{product_id}_{months}_{qty}")],
            [InlineKeyboardButton("❌ Decline", callback_data="main_menu")]
        ]
        await query.edit_message_text(text=terms_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("rzpagree_"):
        parts = data.split("_")
        product_id = parts[1]
        
        if len(parts) > 3:
            months = int(parts[2])
            qty = int(parts[3])
        else:
            months = 0
            qty = int(parts[2]) if len(parts) > 2 else 1
        
        loading_text = (
            f"<b>ORDER INITIATED</b> <tg-emoji emoji-id=\"6230853345733510932\">💰</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"<i>⏳ Securing your order & generating payment gateway...</i>"
        )
        await query.edit_message_text(text=loading_text, parse_mode="HTML")

        try:
            response = supabase.table("products").select("*").eq("id", product_id).execute()
            product = response.data[0] if response.data else None
        except Exception as e:
            product = None

        if not product:
            await query.edit_message_text("❌ <b>Product not found.</b>", parse_mode="HTML")
            return

        if product["category"] == "OTT" and months > 0:
            price = float(product.get(f"price_{months}m") or 0) * qty
        else:
            price = float(product["price"]) * qty
        
        pay_res = await create_payment_link(
            amount=price,
            product_name=f"{qty}x {product['name']}",
            telegram_id=user.id,
            product_id=product["id"],
            first_name=user.first_name
        )

        if not pay_res.get("success"):
            await query.edit_message_text(
                text=f"❌ <b>Error generating payment link:</b>\n<code>{pay_res.get('error')}</code>",
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
            amount=price,
            quantity=qty,
            subscription_months=months
        )

        checkout_text = (
            f"<b>ORDER GENERATED</b> <tg-emoji emoji-id=\"6093648802986592017\">✅</tg-emoji>\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"<b>Order Ref:</b> <code>{payment_id}</code>\n"
            f"<b>Product:</b> {product['name']} (x{qty})\n"
            f"<b>Amount:</b> ₹{price:.2f}\n\n"
            f"<i>Click the button below to pay securely. Once completed, your product will be delivered instantly.</i>"
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
            empty_text = (
                f"<b>PURCHASE HISTORY</b> <tg-emoji emoji-id=\"5940804519083383006\">📜</tg-emoji>\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"YOU HAVEN'T MADE ANY PURCHASES YET. START SHOPPING TO ACCESS PREMIUM PRODUCTS! 🛒\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            )
            await query.edit_message_text(
                text=empty_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
                parse_mode="HTML"
            )
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
            
        await query.edit_message_text(
            text=history_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
            parse_mode="HTML"
        )

    elif data == "view_support":
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
        keyboard = [
            [InlineKeyboardButton("💬 Chat with Admin", url="https://t.me/ur_Growixx222")],
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
