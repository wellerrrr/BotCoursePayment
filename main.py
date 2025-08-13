from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, F, types
from fastapi import FastAPI, Request
from yookassa.domain.notification import WebhookNotification
import uvicorn

from handlers import callbacks, admin, start, db_callback_messages
from services.reviews import ReviewService
from services.purchasing import save_yookassa_payment
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

# Эндпоинт для вебхука YooKassa
@app.post("/yookassa-webhook")
async def yookassa_webhook(request: Request):
    try:
        data = await request.json()
        notification = WebhookNotification(data)
        payment = notification.object
        user_id = payment.metadata.get('user_id')
        
        if payment.status == 'succeeded' and user_id:
            save_yookassa_payment(int(user_id), payment)
            try:
                await callbacks.send_access_message(
                    message=types.Message(chat=types.Chat(id=int(user_id))),
                    user_id=int(user_id),
                    bot=bot
                )
            except Exception as e:
                logger.error(f"Error sending access message: {e}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

# Функция для запуска бота
async def start_bot():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

# FastAPI startup event
@app.on_event("startup")
async def on_startup():
    # Запускаем бота в фоновом режиме
    asyncio.create_task(start_bot())

if __name__ == "__main__":
    # Запускаем всё вместе через uvicorn
    uvicorn.run(
        "main:app",
        reload=True,
        reload_includes=["*.py"],
        loop="asyncio"
    )