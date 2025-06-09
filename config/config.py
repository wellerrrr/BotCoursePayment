import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "default_token_if_not_set")
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "default_support_token_if_not_set")
ADMIN_IDS = eval(os.getenv("ADMIN_IDS", "[0]"))