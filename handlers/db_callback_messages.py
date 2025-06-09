import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.commands import get_message_by_title, get_all_messages, is_admin, update_message_text

db_cb_router = Router()

class EditMessage(StatesGroup):
    waiting_for_new_text = State()

@db_cb_router.message(lambda message: message.text and message.text.startswith('/'))
async def handle_commands(message: Message):
    command = message.text.lstrip('/').split()[0]  # Извлекаем команду без "/"
    logging.debug(f"Получена команда: {command}")
    msg = get_message_by_title(command)
    if msg:
        await message.answer(msg[2])
    else:
        await message.answer(f"Сообщение для команды /{command} не найдено в базе.")
    # Для админов добавляем инлайн-кнопку "Редактировать сообщение"
    if is_admin(message.from_user.id):
        edit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Редактировать сообщение", callback_data="edit_bot_message")]
        ])
        await message.answer("Админ-панель:", reply_markup=edit_keyboard)

@db_cb_router.callback_query(lambda c: c.data == "edit_bot_message" and is_admin(c.from_user.id))
async def edit_choosen_message(callback: CallbackQuery):
    logging.debug(f"Пользователь {callback.from_user.id} нажал 'Редактировать сообщение'")
    messages = get_all_messages()
    if not messages:
        await callback.message.answer("В базе нет сообщений для редактирования.")
        logging.debug("Нет сообщений для редактирования")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for msg_id, title, _ in messages:
        if not title or len(title.strip()) == 0:
            title = "Без заголовка"
        title = title[:30]  # Ограничим длину заголовка для кнопки
        button = InlineKeyboardButton(text=title, callback_data=f"edit_{msg_id}")
        keyboard.inline_keyboard.append([button])
        logging.debug(f"Добавлена кнопка для сообщения: id={msg_id}, title={title}")
    await callback.message.answer("Выберите сообщение для редактирования:", reply_markup=keyboard)
    await callback.answer()

# Обработчик выбора сообщения через инлайн-кнопку
@db_cb_router.callback_query(lambda c: c.data.startswith("edit_") and is_admin(c.from_user.id))
async def process_message_selection(callback: CallbackQuery, state: FSMContext):
    message_id = int(callback.data.split("_")[1])
    logging.debug(f"Выбрано сообщение с ID {message_id}")
    messages = get_all_messages()
    selected_message = next((msg for msg in messages if msg[0] == message_id), None)
    if selected_message:
        cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отменить редактирование", callback_data="cancel_edit")]
        ])
        await callback.message.answer(f"{selected_message[2]}", reply_markup=cancel_keyboard)
        await callback.message.answer("Скопируйте текст выше, вставьте его в поле ввода, отредактируйте и отправьте.")
        await state.update_data(message_id=message_id)
        await state.set_state(EditMessage.waiting_for_new_text)
        logging.debug(f"Ожидается новый текст для сообщения с ID {message_id}")
    else:
        await callback.message.answer("Сообщение не найдено.")
        logging.error(f"Сообщение с ID {message_id} не найдено")
    await callback.answer()

# Обработчик кнопки "Отмена"
@db_cb_router.callback_query(lambda c: c.data == "cancel_edit" and is_admin(c.from_user.id))
async def process_cancel_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Редактирование отменено.")
    logging.debug(f"Редактирование отменено пользователем {callback.from_user.id}")
    await callback.answer()

# Получение нового текста и обновление сообщения
@db_cb_router.message(EditMessage.waiting_for_new_text)
async def process_new_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только админы могут редактировать сообщения.")
        await state.clear()
        logging.debug(f"Пользователь {message.from_user.id} не админ, редактирование отклонено")
        return
    data = await state.get_data()
    message_id = data.get("message_id")
    new_text = message.text
    try:
        update_message_text(message_id, new_text)
        await message.answer("Сообщение успешно обновлено в базе данных!")
        logging.debug(f"Сообщение с ID {message_id} успешно обновлено")
    except Exception as e:
        await message.answer(f"Ошибка при обновлении: {str(e)}")
        logging.error(f"Ошибка при обновлении сообщения с ID {message_id}: {e}")
    await state.clear()