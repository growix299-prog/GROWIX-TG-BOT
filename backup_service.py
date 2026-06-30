import os
import time
import json
import logging
from datetime import datetime

# Load .env file
if os.path.exists('.env'):
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

from backend.services.supabase_service import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TABLES = [
    "users", "products", "credentials", "orders", 
    "ott_requests", "payments", "reviews", "wallet_transactions"
]

def perform_backup():
    db = get_db()
    if not db:
        logger.error("Database connection failed. Cannot backup.")
        return

    os.makedirs("backups", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = f"backups/db_backup_{timestamp}.json"
    
    backup_data = {}
    
    for table in TABLES:
        try:
            res = db.table(table).select("*").execute()
            backup_data[table] = res.data or []
            logger.info(f"Backed up table '{table}' - {len(backup_data[table])} rows.")
        except Exception as e:
            logger.error(f"Error backing up {table}: {e}")
            
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4, default=str)
        logger.info(f"✅ Successfully created full database backup: {backup_file}")
    except Exception as e:
        logger.error(f"Failed to save backup file: {e}")

if __name__ == "__main__":
    logger.info("Starting Automated Database Backup Service (Interval: 48 Hours)...")
    
    # Run the first backup immediately
    perform_backup()
    
    # Then loop every 2 days
    while True:
        logger.info("Next backup scheduled in 48 hours...")
        time.sleep(2 * 24 * 60 * 60)  # 2 days in seconds
