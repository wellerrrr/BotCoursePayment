from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENTS_TOKEN = os.getenv("PAYMENTS_TOKEN")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

# Добавь отладочный вывод
print(f"Loaded ADMIN_IDS: {ADMIN_IDS}")