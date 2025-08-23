from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, F, types
from fastapi import FastAPI, Request
from yookassa.domain.notification import WebhookNotification
import uvicorn

from handlers import callbacks, admin, start, db_callback_messages
from services.reviews import ReviewService

from middlewares.admin import AdminPhotoMiddleware

from config import config

import logging
import asyncio

# Инициализация логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация базовых компонентов
storage = MemoryStorage()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=storage)
app = FastAPI()

# Инициализация сервисов
review_service = ReviewService()
dp["review_service"] = review_service

# Регистрация роутеров
dp.include_router(start.router)
dp.include_router(admin.admin_router)
dp.include_router(callbacks.cb_handler)
dp.include_router(db_callback_messages.db_cb_router)

# Middleware
dp.message.middleware(AdminPhotoMiddleware())


# Функция для запуска бота
async def start_bot():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    try:
        print('Бот включен!')
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print('Бот выключен!')