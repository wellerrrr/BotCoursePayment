import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "your_default_token_here")
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "your_default_support_token_here")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")