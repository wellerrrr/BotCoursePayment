from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")