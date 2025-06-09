from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,)
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Купить', callback_data='buy')],
        [InlineKeyboardButton(text='Посмотреть, что внутри', callback_data='preview')],
        [InlineKeyboardButton(text='Отзывы', callback_data='reviews')],
        [InlineKeyboardButton(text='Поддержка', url='https://t.me/promote_land_support_bot')],
    ])


buy_keyboard_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Купить', callback_data='buy')],
])


def get_buy_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Не получается оплатить', url='https://t.me/promote_land_support_bot')],
        [InlineKeyboardButton(text='В меню', callback_data='back_menu')],
    ])

def get_support_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Не получается оплатить', url='https://t.me/promote_land_support_bot')],
    ])

def get_press_to_buy_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Купить', callback_data='buy')],
        [InlineKeyboardButton(text='⬅️ Назад', callback_data='back_to_menu')],
    ])

def get_back_button() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    return builder.as_markup()

def add_back_button(keyboard: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
    """Добавляет кнопку 'Назад' к существующей клавиатуре"""
    builder = InlineKeyboardBuilder.from_markup(keyboard)
    builder.button(text="⬅️ Назад", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_continue_button():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продолжить", callback_data="continue_to_consent")]
    ])
    return keyboard