import os
import logging
import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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
def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📺 OTT Subscriptions", callback_data="cat_OTT"),
            InlineKeyboardButton("🎮 Game Accounts", callback_data="cat_Games")
        ],
        [
            InlineKeyboardButton("📜 Order History", callback_data="view_history"),
            InlineKeyboardButton("ℹ️ Support / Help", callback_data="view_support")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

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

    banner = (
        f"⚡ <b>WELCOME TO ELITE DIGITAL STORE</b> ⚡\n\n"
        f"Hello {html.escape(user.first_name)}! We provide 100% automated instant delivery of gaming credentials and premium OTT services.\n\n"
        f"📦 <b>Instant Delivery:</b> Game accounts (Steam, Valorant, GTA V, etc.)\n"
        f"⚙️ <b>Fast Setup:</b> OTT subscriptions (Netflix, Spotify, YouTube Premium, etc.)\n\n"
        f"📢 <b>Join our channels for updates & offers:</b>\n"
        f"👇 <i>Select a category below to browse our inventory:</i>"
    )

    base_keyboard = get_main_menu_keyboard().inline_keyboard
    channel_buttons = [
        [
            InlineKeyboardButton("🔴 Join OTT Updates 🔴", url="https://t.me/growix_otts")
        ],
        [
            InlineKeyboardButton("🔴 Join Games Updates 🔴", url="https://t.me/growix_games")
        ]
    ]
    
    await update.message.reply_text(
        text=banner,
        reply_markup=InlineKeyboardMarkup(channel_buttons + list(base_keyboard)),
        parse_mode="HTML"
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes all inline button clicks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user
    supabase = get_db()

    if data == "main_menu":
        banner = (
            f"⚡ <b>ELITE DIGITAL STORE - MAIN MENU</b> ⚡\n\n"
            f"Browse our high-quality inventory using the buttons below:"
        )
        await query.edit_message_text(
            text=banner,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )

    elif data.startswith("cat_"):
        category = data.split("_")[1]
        
        # Fetch active products in this category
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
                text=f"🗂️ <b>Category: {category}</b>\n\nCurrently, there are no active products in this category. Please check back later!\n\n<i>[SYSTEM DEBUG]: {error_msg}</i>",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            return

        keyboard = []
        # Create grid of products
        for prod in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"{prod['name']} - ₹{float(prod['price']):.2f}", 
                    callback_data=f"prod_{prod['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])

        await query.edit_message_text(
            text=f"🗂️ <b>Browse {category} Products:</b>\n\nChoose a product below to view details and buy:",
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
                text="❌ Product not found. It may have been disabled or deleted by the admin.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]),
                parse_mode="HTML"
            )
            return

        # Check stock availability
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
            f"📦 <b>PRODUCT DETAIL</b> 📦\n\n"
            f"🏷️ <b>Name:</b> {product['name']}\n"
            f"🗂️ <b>Category:</b> {product['category']}\n"
            f"💰 <b>Price:</b> ₹{float(product['price']):.2f}\n"
            f"⚡ <b>Delivery:</b> ✨ INSTANT AUTO-DELIVERY ✨\n"
            f"📊 <b>Stock:</b> {stock_label}\n\n"
        )

        if is_in_stock:
            details += f"🛒 <i>Ready to purchase? Click 'Buy Now' to generate a secure Razorpay checkout link:</i>"
            keyboard = [
                [InlineKeyboardButton("💳 Buy Now (Generate Link)", callback_data=f"buy_{product['id']}")],
                [InlineKeyboardButton(f"🔙 Back to {product['category']}", callback_data=f"cat_{product['category']}")]
            ]
        else:
            details += f"⚠️ <i>This product is currently out of stock. Please check back later or contact support.</i>"
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
        
        await query.edit_message_text("⏳ <i>Checking stock & generating payment link, please wait...</i>", parse_mode="HTML")

        try:
            response = supabase.table("products").select("*").eq("id", product_id).execute()
            product = response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error checking product: {str(e)}")
            product = None

        if not product:
            await query.edit_message_text("❌ Product not found.")
            return

        # ⚠️ STOCK CHECK: Verify credentials exist before accepting payment
        has_stock = False
        try:
            stock_check = supabase.table("credentials").select("id").eq("product_id", product_id).eq("status", "UNUSED").limit(1).execute()
            has_stock = bool(stock_check.data)
        except Exception as e:
            logger.error(f"Stock check failed: {str(e)}")
            has_stock = False

        if not has_stock:
            await query.edit_message_text(
                text=(
                    f"❌ <b>OUT OF STOCK!</b>\n\n"
                    f"Sorry, <b>{product['name']}</b> is currently out of stock. "
                    f"No credentials are available for delivery right now.\n\n"
                    f"Please check back later or contact support for restocking updates."
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
                ]),
                parse_mode="HTML"
            )
            return

        price = float(product["price"])
        
        # Create Razorpay payment link
        pay_res = await create_payment_link(
            amount=price,
            product_name=product["name"],
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

        # Save order as PENDING in database
        create_order(
            telegram_id=user.id,
            product_id=product["id"],
            payment_id=payment_id,
            amount=price
        )

        checkout_text = (
            f"🛒 <b>CHECKOUT DETAILS</b> 🛒\n\n"
            f"📦 <b>Item:</b> {product['name']}\n"
            f"💰 <b>Amount Due:</b> ₹{price:.2f}\n"
            f"🆔 <b>Order Reference:</b> <code>{payment_id}</code>\n\n"
            f"🔐 Click the button below to pay securely via Razorpay. "
            f"Once you complete the payment, the transaction is verified instantly by our webhooks."
        )

        keyboard = [
            [InlineKeyboardButton("💳 Pay Securely (Razorpay)", url=short_url)],
            [InlineKeyboardButton("❌ Cancel Order", callback_data="main_menu")]
        ]

        await query.edit_message_text(
            text=checkout_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif data == "view_history":
        try:
            # Query user orders (all statuses)
            response = supabase.table("orders").select("*, products(*)").eq("telegram_id", user.id).order("created_at", desc=True).execute()
            orders = response.data
        except Exception as e:
            logger.error(f"Error fetching order history: {str(e)}")
            orders = []

        if not orders:
            await query.edit_message_text(
                text="📜 <b>Order History</b>\n\nYou haven't made any purchases yet. Start shopping now!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
                parse_mode="HTML"
            )
            return

        history_text = "📜 <b>YOUR RECENT ORDERS:</b>\n\n"
        for idx, order in enumerate(orders[:10], 1): # Show latest 10
            prod = order.get("products") or {}
            prod_name = prod.get("name", "Unknown Product")
            
            if order.get("status") == "PENDING":
                status = "Pending Payment / Setup"
            else:
                status = "Delivered" if order.get("delivery_status") == "DELIVERED" else "Processing"
                
            history_text += f"{idx}. <b>{prod_name}</b>\n   💰 ₹{float(order.get('amount', 0)):.2f} | 📅 {order.get('created_at', '')[:10]}\n   🚚 Status: {status}\n\n"
            
        await query.edit_message_text(
            text=history_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]),
            parse_mode="HTML"
        )

    elif data == "view_support":
        support_text = (
            f"ℹ️ <b>CUSTOMER SUPPORT</b> ℹ️\n\n"
            f"Have issues with a digital product or payment? We are here to help!\n\n"
            f"👤 <b>Admin Contact:</b> @ur_aurexia222\n\n"
            f"<i>Please share your Order Reference ID while contacting support for quick resolution.</i>"
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
            f"🌟 <b>We value your feedback!</b> 🌟\n\n"
            f"Please type your review below and send it to me. Your reviews help us improve our services!"
        )
        await query.edit_message_text(
            text=review_text,
            parse_mode="HTML"
        )

