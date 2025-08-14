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
        event = notification.event
        user_id = payment.metadata.get('user_id') if payment.metadata else None

        logger.info(f"Received YooKassa webhook: {event} for payment {payment.id}")
        
        if not user_id:
            logger.warning(f"No user_id in payment metadata: {payment.id}")
            return {"status": "error", "message": "No user_id in metadata"}

        # Расширенная обработка событий
        match event:
            case 'payment.waiting_for_capture':
                # Платёж ожидает подтверждения
                try:
                    await bot.send_message(
                        chat_id=int(user_id),
                        text="⌛ Ожидаем подтверждение оплаты..."
                    )
                except Exception as e:
                    logger.error(f"Error sending waiting message: {e}")

            case 'payment.canceled':
                # Платёж отменён
                save_yookassa_payment(int(user_id), payment)
                try:
                    cancel_reason = payment.cancellation_details.reason if payment.cancellation_details else "неизвестна"
                    await bot.send_message(
                        chat_id=int(user_id),
                        text=f"❌ Платёж был отменён\n"
                             f"Причина: {cancel_reason}\n\n"
                             f"Попробуйте оплатить снова или обратитесь в поддержку."
                    )
                except Exception as e:
                    logger.error(f"Error sending cancel message: {e}")

            case 'payment.pending':
                # Платёж в процессе
                try:
                    await bot.send_message(
                        chat_id=int(user_id),
                        text="⏳ Платёж обрабатывается. Пожалуйста, подождите..."
                    )
                except Exception as e:
                    logger.error(f"Error sending pending message: {e}")

            case 'refund.succeeded':
                # Успешный возврат средств
                try:
                    await bot.send_message(
                        chat_id=int(user_id),
                        text="♻️ Возврат средств успешно выполнен.\n"
                             "Доступ к каналу будет закрыт."
                    )
                except Exception as e:
                    logger.error(f"Error sending refund message: {e}")

            case _:
                logger.info(f"Received unhandled event type: {event}")

        return {
            "status": "success",
            "payment_id": payment.id,
            "event": event,
            "user_id": user_id
        }
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
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