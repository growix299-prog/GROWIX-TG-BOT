import os
import sys
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Setup path so we can import backend packages
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Load .env file from root directory
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            # Strip null bytes and whitespace to handle corrupted encoding
            line = line.replace("\x00", "").strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


from telegram_bot.handlers.menu import start_command, handle_callback_query, history_command, support_command
from telegram_bot.handlers.delivery import handle_user_text

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Health Check Server (keeps Render free tier alive) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"pong")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        
    def log_message(self, format, *args):
        pass  # Suppress noisy HTTP logs

def start_health_server():
    port = int(os.getenv("BOT_HEALTH_PORT", 8082) if os.getenv("BOT_HEALTH_PORT") else os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info(f"Health check server running on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Could not start health check server on port {port}: {e}. Bot will continue running anyway.")


async def setup_commands(application: Application):
    """Set up the bot command menu."""
    commands = [
        BotCommand("start", "Open Main Menu"),
        BotCommand("history", "View Order History"),
        BotCommand("support", "Contact Support")
    ]
    await application.bot.set_my_commands(commands)

def main():
    """Starts the Telegram Bot."""
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not defined in environment variables! Exiting.")
        sys.exit(1)

    # Start health check server in background thread (for Render free tier)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    logger.info("Initializing Telegram Digital Delivery Bot...")
    
    # Initialize python-telegram-bot application
    application = Application.builder().token(BOT_TOKEN).post_init(setup_commands).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_text))

    import time
    logger.info("Waiting 5 seconds for any old instances to shut down...")
    time.sleep(5)
    
    logger.info("Bot is active and polling for new messages...")
    
    # Run the bot polling loop
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
