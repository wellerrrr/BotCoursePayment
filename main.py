from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, F

from handlers import callbacks, admin, start, db_callback_messages
from services.reviews import ReviewService
from middlewares.admin import AdminPhotoMiddleware

from config import config
from aiohttp import web

import logging
import asyncio


async def handle_webhook(request, bot: Bot):
    data = await request.json()
    payment = data['object']
    
    if payment['status'] == 'succeeded':
        user_id = payment['metadata']['user_id']
        await bot.send_message(user_id, "✅ Платеж подтверждён! Доступ: t.me/ваш_канал")
    
    return web.Response(text="OK")

app = web.Application()
app.router.add_post('/yookassa_webhook', handle_webhook)


async def run_bot(dispatcher: Dispatcher, bot: Bot):
    try:
        logger.info(f"Starting bot with token: [REDACTED]")
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=config.BOT_TOKEN)

    dp_main = Dispatcher(storage=MemoryStorage())
    review_service = ReviewService()
    
    dp_main["review_service"] = review_service
    dp_main.message.middleware(AdminPhotoMiddleware())
    
    dp_main.include_router(start.router)
    dp_main.include_router(admin.admin_router)
    dp_main.include_router(callbacks.cb_handler)
    dp_main.include_router(db_callback_messages.db_cb_router)
    
    logger.info("Запускаем бот")
    await asyncio.gather(
        run_bot(dp_main, bot),
    )

if __name__ == '__main__':
    try:
        logger.info("Запускаем бот")
        asyncio.run(main())
    except KeyboardInterrupt as e:
        print('Бот выключен!')