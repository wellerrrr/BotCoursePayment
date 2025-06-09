from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Router, F, types, Bot
from aiogram.filters import Command

from middlewares.admin import AdminPhotoMiddleware
from services.reviews import ReviewService
from services.session import admin_session
from keyboards.admin import get_admin_kb, get_back_kb

import logging
import asyncio
from config import config

class AdminStates(StatesGroup):
    waiting_for_new_text = State()

logger = logging.getLogger(__name__)
admin_router = Router()
admin_router.message.middleware(AdminPhotoMiddleware())
admin_router.callback_query.middleware(AdminPhotoMiddleware())

@admin_router.message(Command("admin"))
async def admin_login(message: Message, bot: Bot):
    """Вход с активацией прав"""
    try:
        if message.from_user.id in config.ADMIN_IDS:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=message.message_id - 1,
                reply_markup=None
            )
    except TelegramBadRequest:
        pass
    
    if message.from_user.id in config.ADMIN_IDS:
        admin_session.login(message.from_user.id)
        await message.answer(
            "🔐 Админ-режим АКТИВИРОВАН\n",
            reply_markup=get_admin_kb()
        )
    else:
        await message.answer('⛔ Вы не являетесь админом!')

@admin_router.callback_query(F.data == "admin_add_review")
async def add_review_handler(callback: CallbackQuery):
    """Обработчик кнопки добавления отзыва"""
    await callback.message.answer(
        "📤 Отправьте скриншот отзыва (только фото)\n"
        "Или /cancel для отмены"
    )
    await callback.answer()

@admin_router.message(F.photo)
async def handle_admin_photo(message: Message, review_service: ReviewService):
    """Обработка фото ТОЛЬКО для активных админов"""
    if not admin_session.is_active(message.from_user.id):
        await message.answer("✋ Режим добавления отзывов отключен. Используйте /admin")
        return

    try:
        photo_url = message.photo[-1].file_id
        if await review_service.add_review(photo_url):
            await message.answer("✅ Отзыв добавлен",
                                 reply_markup=get_admin_kb())
            
        else:
            await message.answer("❌ Такой отзыв уже есть",
                                 reply_markup=get_admin_kb())
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await message.answer("⚠️ Ошибка обработки фото")

@admin_router.message(Command("cancel"))
async def cancel_operation(message: Message):
    user_id = message.from_user.id
    admin_session.logout(user_id)
    
    await message.delete()
    await message.answer("Действие отменено", reply_markup=get_admin_kb())

@admin_router.callback_query(F.data == "admin_list_reviews")
async def show_all_reviews(callback: CallbackQuery, review_service: ReviewService):
    """Показать все отзывы"""
    try:
        await callback.answer()
        reviews = await review_service.get_all_reviews()
        
        if not reviews:
            await callback.message.answer("📭 Нет сохраненных отзывов")
            return

        media_group = MediaGroupBuilder()
        for photo_url in reviews[:10]:
            media_group.add_photo(media=photo_url)
        
        await callback.message.answer_media_group(media=media_group.build())
            
    except Exception as e:
        await callback.message.answer("⚠️ Ошибка при загрузке отзывов")

@admin_router.callback_query(F.data.startswith("del_preview_"))
async def preview_for_deletion(callback: CallbackQuery, review_service: ReviewService):
    """Предпросмотр перед удалением с плавным переходом"""
    user_id = callback.from_user.id
    try:
        await callback.message.edit_text("Загружаем отзыв... ⏳")
        await asyncio.sleep(0.5)

        review_id = int(callback.data.split("_")[2])
        photo_url = await review_service.get_photo_url(review_id)
        
        if not photo_url:
            await callback.message.edit_text("❌ Отзыв не найден")
            await asyncio.sleep(1)
            await back_to_delete_menu(callback, review_service)
            return

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Удалить", callback_data=f"del_confirm_{review_id}")
        builder.button(text="🔙 Назад", callback_data="admin_delete_reviews")
        
        await callback.message.delete()
        sent_msg = await callback.message.answer_photo(
            photo_url,
            caption=f"Отзыв #{review_id}\nУдалить этот отзыв?",
            reply_markup=builder.as_markup()
        )

        await callback.answer()
        return sent_msg
        
    except Exception as e:
        logger.error(f"User {user_id} error: {str(e)}")
        await callback.message.edit_text(
            "⚠️ Ошибка при загрузке отзыва\nВозвращаемся в меню...",
            reply_markup=None
        )
        await asyncio.sleep(1)
        await back_to_delete_menu(callback, review_service)
        await callback.answer()

@admin_router.callback_query(F.data == "admin_delete_reviews")
async def back_to_delete_menu(callback: CallbackQuery, review_service: ReviewService):
    """Возврат в меню удаления"""
    user_id = callback.from_user.id
    try:         
        reviews = await review_service.get_reviews_for_deletion()
        
        if not reviews:
            await callback.message.answer(
                "📭 Нет отзывов для удаления",
                reply_markup=get_back_kb()
            )
            return

        builder = InlineKeyboardBuilder()
        for review_id, _ in reviews:
            builder.button(
                text=f"❌ {review_id}",
                callback_data=f"del_preview_{review_id}"
            )
        builder.button(text="🔙 В админку", callback_data="admin_back")
        builder.adjust(3, repeat=True)
        
        await callback.message.answer(
            "Выберите отзыв для удаления:",
            reply_markup=builder.as_markup()
        )
        
    except Exception as e:
        logger.error(f"User {user_id} error: {str(e)}")
        await callback.message.answer(
            "⚠️ Ошибка при возврате",
            reply_markup=get_back_kb()
        )
    finally:
        await callback.answer()

@admin_router.callback_query(F.data.startswith("del_confirm_"))
async def confirm_review_deletion(callback: CallbackQuery, review_service: ReviewService):
    """Удаление с перенумерацией"""
    try:
        review_id = int(callback.data.split("_")[2])
        
        if await review_service.delete_review_and_reset_ids(review_id):
            await callback.message.delete()
            
            # Получаем актуальный список для отображения
            reviews = await review_service.get_reviews_for_deletion()
            count = len(reviews)
            
            await callback.message.answer(
                f"✅ Отзыв удален. Всего отзывов: {count}\n"
                "🔐 Админ-панель:",
                reply_markup=get_admin_kb()
            )
        else:
            await callback.message.edit_caption(
                "❌ Не удалось удалить отзыв",
                reply_markup=get_back_kb()
            )
            
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        await callback.message.answer(
            "⚠️ Ошибка при удалении",
            reply_markup=get_admin_kb()
        )
    finally:
        await callback.answer()

@admin_router.callback_query(F.data == "admin_back")
async def back_to_admin_panel(callback: CallbackQuery):
    """Возврат в админ-панель"""
    try:
        await callback.message.edit_text(
            "🔐 Админ-панель:",
            reply_markup=get_admin_kb()
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await callback.message.answer(
            "🔐 Админ-панель:",
            reply_markup=get_admin_kb()
        )
    finally:
        await callback.answer()

@admin_router.callback_query(F.data == "admin_exit")
async def exit_admin_panel(callback: CallbackQuery):
    """Полный выход с деактивацией прав"""
    try:
        user_id = callback.from_user.id
        admin_session.logout(user_id)
        
        await callback.message.delete()
        await callback.message.answer(
            "🔒 Вы вышли из админ-режима\n",
            reply_markup=types.ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Exit error: {e}")
        await callback.message.answer("⚠️ Ошибка выхода")
    finally:
        await callback.answer()
    
@admin_router.message(F.photo)
async def handle_admin_photo(
    message: Message, 
    review_service: ReviewService,
    bot: Bot
):
    """Обработка фото ТОЛЬКО для админов"""
    try:
        if not await AdminPhotoMiddleware.is_admin(message.from_user.id):
            return

        photo_url = message.photo[-1].file_id
        success, review_id = await review_service.add_review(photo_url)
        
        if success:
            await message.answer(f"✅ Отзыв #{review_id} сохранен")
        else:
            await message.answer("❌ Ошибка сохранения")
            
    except Exception as e:
        logger.error(f"Admin photo error: {e}")
        await message.answer("⚠️ Ошибка обработки фото")

