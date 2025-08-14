from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENTS_TOKEN = os.getenv("PAYMENTS_TOKEN")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
NGROK_TUNEL_URL = os.getenv("NGROK_TUNEL_URL")

MYSQL_CONFIG = {
    'host': os.getenv("MYSQL_HOST", "localhost"),
    'port': int(os.getenv("MYSQL_PORT", 3306)),
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", ""),
    'database': os.getenv("MYSQL_DATABASE", "land_course"),
    'autocommit': True
}