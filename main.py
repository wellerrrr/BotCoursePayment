from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import CommandStart
from aiogram import Bot, Dispatcher, F

from handlers import callbacks, admin, start, db_callback_messages
from services.reviews import ReviewService
from middlewares.admin import AdminPhotoMiddleware

from support_bot import handlers as support_handlers
from support_bot.handlers import AdminStates
from config import config

import logging
import asyncio


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
    support_bot = Bot(token=config.SUPPORT_BOT_TOKEN)

    dp_main = Dispatcher(storage=MemoryStorage())
    support_bot_dp = Dispatcher(storage=MemoryStorage())
    review_service = ReviewService()

    support_bot_dp["review_service"] = review_service
    
    support_bot_dp.message.register(support_handlers.start, CommandStart())
    support_bot_dp.message.register(
        support_handlers.handle_user_question,
        F.text & ~F.command & ~F.from_user.id.in_(config.ADMIN_IDS)
    )
    support_bot_dp.callback_query.register(
        support_handlers.handle_reply_callback,
        F.data.startswith("reply_")
    )
    support_bot_dp.callback_query.register(
        support_handlers.handle_close_callback,
        F.data.startswith("close_")
    )
    support_bot_dp.message.register(
        support_handlers.handle_admin_reply,
        AdminStates.WAITING_FOR_REPLY,
        F.from_user.id.in_(config.ADMIN_IDS)
    )
    support_bot_dp.message.register(
        support_handlers.show_tickets_menu,
        F.text == "/tickets",
        F.from_user.id.in_(config.ADMIN_IDS)
    )
    support_bot_dp.message.register(
        support_handlers.handle_ticket_select,
        F.from_user.id.in_(config.ADMIN_IDS),
        lambda msg: msg.text.startswith("#") or msg.text == "🔄 Обновить список"
    )
    support_bot_dp.message.register(
        support_handlers.handle_admin_reply,
        F.from_user.id.in_(config.ADMIN_IDS),
        AdminStates.WAITING_FOR_REPLY
    )
    
    dp_main["review_service"] = review_service
    dp_main.message.middleware(AdminPhotoMiddleware())
    
    dp_main.include_router(start.router)
    dp_main.include_router(admin.admin_router)
    dp_main.include_router(callbacks.cb_handler)
    dp_main.include_router(db_callback_messages.db_cb_router)
    
    logger.info("Запускаем бот")
    await asyncio.gather(
        run_bot(dp_main, bot),
        run_bot(support_bot_dp, support_bot),
    )

if __name__ == '__main__':
    try:
        logger.info("Запускаем бот")
        asyncio.run(main())
    except KeyboardInterrupt as e:
        print('Бот выключен!')