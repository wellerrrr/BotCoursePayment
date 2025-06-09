from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_kb():
    """Основная клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить отзыв", callback_data="admin_add_review")
    builder.button(text="🗑 Удалить отзывы", callback_data="admin_delete_reviews")
    builder.button(text="👀 Показать все", callback_data="admin_list_reviews")
    builder.button(text="Редактировать сообщение", callback_data="edit_bot_message")
    builder.button(text="🔙 Выход", callback_data="admin_exit")
    builder.adjust(2, 2, 1)
    return builder.as_markup()

def get_back_kb():
    """Клавиатура с кнопкой Назад"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_back")
    return builder.as_markup()