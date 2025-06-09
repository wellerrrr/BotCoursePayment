from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Bot, types, F
from aiogram.types import (
    Message, 
    CallbackQuery,
    KeyboardButton, 
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from services.reviews import Database

from config import config
import logging

logger = logging.getLogger(__name__)
db = Database()

class AdminStates(StatesGroup):
    WAITING_FOR_REPLY = State()

USER_START_MESSAGE = "Здравствуйте! Задайте вопрос, и мы ответим в ближайшее время."
ADMIN_START_MESSAGE = "👮 Вы в режиме администратора. Новые вопросы будут приходить здесь. /tickets - Чтобы посмотреть открытые вопросы пользователей."

async def start(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id in config.ADMIN_IDS:
        await message.answer(ADMIN_START_MESSAGE)
    else:
        await message.answer(USER_START_MESSAGE)

async def handle_user_question(message: Message, bot: Bot):
    if message.from_user.id in config.ADMIN_IDS or message.text.startswith('/'):
        return

    ticket_id = db.create_ticket(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        question=message.text
    )

    if db.get_user_message_count(message.from_user.id) > 5:
        db.delete_old_messages(message.from_user.id)

    for admin_id in config.ADMIN_IDS:
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Ответить", callback_data=f"reply_{ticket_id}")]
            ])
            await bot.send_message(
                chat_id=admin_id,
                text=f"🆕 Тикет #{ticket_id}\n"
                     f"👤 {message.from_user.full_name or 'Без имени'}\n"
                     f"📩 Вопрос:\n{message.text}",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка отправки админу {admin_id}: {e}")

    await message.answer(f"✅ Спасибо за ваше обращение! Ожидайте ответа.")

async def handle_reply_callback(callback: CallbackQuery, state: FSMContext):
    try:
        _, ticket_id_str = callback.data.split('_')
        ticket_id = int(ticket_id_str)
        
        ticket = db.get_ticket(ticket_id)
        if not ticket:
            await callback.answer("Тикет не найден!", show_alert=True)
            return
            
        await state.set_state(AdminStates.WAITING_FOR_REPLY)
        await state.update_data(
            ticket_id=ticket_id,
            user_id=ticket['user_id']
        )
        
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"Введите ответ на тикет #{ticket_id}:",
            reply_markup=types.ForceReply()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_reply_callback: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

async def handle_close_callback(callback: CallbackQuery):
    ticket_id = int(callback.data.split('_')[1])
    db.close_ticket(ticket_id)
    
    await callback.message.edit_text(
        text=f"🚫 ЗАКРЫТО\n{callback.message.text}",
        reply_markup=None
    )
    await callback.answer("Тикет закрыт", show_alert=True)

async def handle_close_ticket(callback: CallbackQuery, bot: Bot):
    try:
        ticket_id = int(callback.data.split('_')[1])
        
        ticket = db.get_ticket(ticket_id)
        if not ticket:
            await callback.answer("Тикет не найден!", show_alert=True)
            return
        
        deleted_count = db.delete_user_messages(ticket['user_id'])        
        new_text = f"🚫 ЗАКРЫТО (удалено {deleted_count} сообщений)\n{callback.message.text}"
        
        if new_text != callback.message.text:
            await callback.message.edit_text(
                text=new_text,
                reply_markup=None
            )
        else: 
            await callback.message.edit_reply_markup(reply_markup=None)
        
        await callback.answer(
            f"Удалено {deleted_count} сообщений пользователя", 
            show_alert=True
        )
        
        try:
            await bot.send_message(
                chat_id=ticket['user_id'],
                text="ℹ️ Все ваши предыдущие обращения были закрыты поддержкой"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя: {e}")

    except Exception as e:
        logger.error(f"Ошибка при закрытии тикета: {e}")
        await callback.answer("Произошла ошибка при обработке", show_alert=True)

async def handle_admin_reply(message: Message, bot: Bot, state: FSMContext):
    """Отправляет ответ пользователю"""
    data = await state.get_data()
    ticket_id = data.get('ticket_id')
    user_id = data.get('user_id')
    
    if not ticket_id or not user_id or message.text.startswith('/'):
        await message.answer("Ошибка: данные тикета потеряны")
        await state.clear()
        return

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"📨 Ответ поддержки:\n\n{message.text}"
        )
        db.close_ticket(ticket_id)
        
        await message.answer("✅ Ответ отправлен!")

    except AttributeError as ae:
        await message.answer(f"❌ Ошибка: {ae}")
        
    finally:
        await state.clear()
        await show_tickets_menu(message)

async def show_tickets_menu(message: Message):
    """Показывает меню с открытыми тикетами"""
    tickets = db.get_open_tickets()
    
    if not tickets:
        await message.answer("Нет активных тикетов.", reply_markup=ReplyKeyboardRemove())
        return
    
    keyboard = [
        [KeyboardButton(text=f"#{ticket['id']} {ticket['full_name']}")]
        for ticket in tickets
    ]
    keyboard.append([KeyboardButton(text="🔄 Обновить список")])
    
    reply_markup = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    await message.answer(
        "📂 Открытые тикеты:",
        reply_markup=reply_markup
    )

async def handle_ticket_select(message: Message, state: FSMContext):
    """Обрабатывает выбор тикета админом"""
    if message.text == "🔄 Обновить список":
        await show_tickets_menu(message)
        return

    try:
        ticket_id = int(message.text.split()[0][1:])
    except:
        await message.answer("Ошибка формата тикета")
        return

    ticket = next((t for t in db.get_open_tickets() if t['id'] == ticket_id), None)
    
    if not ticket:
        await message.answer("Тикет не найден!", reply_markup=ReplyKeyboardRemove())
        return

    await state.set_state(AdminStates.WAITING_FOR_REPLY)
    await state.update_data(
        ticket_id=ticket_id,
        user_id=ticket['user_id']
    )

    await message.answer(
        f"👤 {ticket['full_name']} (@{ticket['username']})\n"
        f"❓ Вопрос:\n\n<strong>{ticket['question']}</strong>\n\n"
        "Введите ответ:",
        reply_markup=ReplyKeyboardRemove(), parse_mode='HTML'
    )
