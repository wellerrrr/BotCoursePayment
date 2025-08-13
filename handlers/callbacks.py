from aiogram import Router, F, Bot, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keyboards import inline
from services.reviews import ReviewService
from services.purchasing import (save_consent, save_invite_link, has_payment,
                                 save_yookassa_payment, get_user_email, save_user_email, validate_email)
from services.purchasing import get_user_invite_link
from services.commands import get_all_messages, is_admin, get_message_by_title
from config import config
import uuid
from yookassa import Payment, Configuration
import yookassa

from aiogram.types import LabeledPrice
from aiogram.filters import Command
import time
import asyncio

import logging
logger = logging.getLogger(__name__)

cb_handler = Router()
review_service = ReviewService()

Configuration.account_id = config.ACCOUNT_ID
Configuration.secret_key = config.PAYMENTS_TOKEN

class PurchaseStates(StatesGroup):
    awaiting_continue = State()
    awaiting_consent = State()
    awaiting_email = State()


user_consents = {}
def get_consent_buttons(user_id: int):
    data_text = "✓ Согласен с обработкой данных" if user_consents.get(user_id, {}).get("data_consent", False) else "Согласен с обработкой данных"
    offer_text = "✓ Акцептую оферту" if user_consents.get(user_id, {}).get("offer_consent", False) else "Акцептую оферту"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='Политика конфиденциальности', url='https://docs.google.com/document/d/1_01AHDErOBo8EiK_ugseiOJQ_OuxK00C/edit?tab=t.0'),
            InlineKeyboardButton(text='Оферта', url='https://docs.google.com/document/d/1hdaA1hLhKb2vc234-WTVu-33h1viylU-/edit?tab=t.0'),
        ],
        [
            InlineKeyboardButton(text=data_text, callback_data="consent_data"),
            InlineKeyboardButton(text=offer_text, callback_data="consent_offer"),
        ],
        [InlineKeyboardButton(text="Продолжить", callback_data="proceed_to_payment")]
    ])
    return keyboard

async def create_yookassa_payment(user_id: int, email: str):
    try:
        idempotence_key = str(uuid.uuid4())
        amount = 1.00
        
        payment = Payment.create({
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/promote_land_bot"
            },
            "capture": True,
            "description": "Доступ к курсу 'Выкуп Земли 2025'",
            "metadata": {
                "user_id": user_id,
                "product": "land_course_2025",
                "bot_payment": True
            },
            "receipt": {
                "customer": {
                    "email": email
                },
                "items": [
                    {
                        "description": "Доступ к курсу 'Выкуп Земли 2025'",
                        "quantity": "1",
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency": "RUB"
                        },
                        "vat_code": "1",
                        "payment_mode": "full_payment",
                        "payment_subject": "service"
                    }
                ]
            }
        }, idempotence_key)
        
        return payment.confirmation.confirmation_url, payment.id
    except Exception as e:
        print(f"Ошибка при создании платежа в ЮKassa: {e}")
        return None
    

def get_russian_status(status: str) -> str:
    status_map = {
        'pending': 'в обработке',
        'waiting_for_capture': 'ожидает подтверждения',
        'succeeded': 'оплачен',
        'canceled': 'отменен',
        'refunded': 'возвращен'
    }
    return status_map.get(status, status)

@cb_handler.callback_query(F.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    
    data = await state.get_data()
    user_id = callback.from_user.id
    chat_id = "-1002597950609"
    
    # Сначала проверяем БД
    if has_payment(user_id):
        # Вместо генерации новой ссылки — даём универсальную кнопку для входа в канал
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в канал", url=f"https://t.me/c/{chat_id[4:]}/1")]
        ])
        await callback.message.answer(
            "✅ Оплата подтверждена! Используйте кнопку ниже для входа в канал.",
            reply_markup=keyboard
        )
        return
        
    # Если в БД нет, проверяем через ЮKassa
    payment_id = data.get('yookassa_payment_id')
    if not payment_id:
        await callback.message.answer('❌ Данные платежа не найдены')
        return

    try:
        payment = Payment.find_one(payment_id)
        status = get_russian_status(payment.status)
        
        if payment.status == 'succeeded':
            if not has_payment(user_id):
                save_yookassa_payment(user_id, payment)
            # После успешной оплаты — также даём универсальную кнопку
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти в канал", url=f"https://t.me/c/{chat_id[4:]}/1")]
            ])
            await callback.message.answer(
                "✅ Оплата подтверждена! Используйте кнопку ниже для входа в канал.",
                reply_markup=keyboard
            )
        else:
            await callback.message.answer(f'⌛ Платеж {status}. Пожалуйста, подождите...')
            
    except Exception as e:
        await callback.message.answer(f'⚠️ Ошибка: {str(e)}')

async def send_access_message(message: Message, user_id: int, bot: Bot):
    
    await send_invite_link(message, user_id, bot)

async def send_invite_link(message: Message, user_id: int, bot: Bot):
    """Функция для отправки инвайт-ссылки"""
    chat_id = "-1002597950609"  # ID приватного канала
    
    try:
        # Генерация одноразовой инвайт-ссылки
        invite_link = await bot.create_chat_invite_link(
            chat_id=chat_id,
            name=f"Invite for user {user_id}",
            expire_date=int(time.time()) + 24 * 3600,  # 24 часа
            member_limit=1  # Одноразовая ссылка
        )

        # Сохранение ссылки в базе данных
        save_invite_link(user_id, invite_link.invite_link)

        # Создание клавиатуры с кнопкой
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в канал", url=invite_link.invite_link)]
        ])

        # Отправка сообщения
        await message.answer(
            """
Ваш доступ к материалам курса находится в закрытом Telegram-канале. 

**Важно**: 
- Она одноразовая и предназначена только для вас
- Не передавайте её другим!""",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await message.answer("❌ Произошла ошибка при создании доступа. Обратитесь в поддержку.")
        print(f"Error creating invite link: {e}")

@cb_handler.callback_query(F.data == 'buy')
async def handler_buy(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    await callback.answer()

    # Проверяем, есть ли уже оплата
    if has_payment(user_id):
        chat_id = "-1002597950609"
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                # Показываем кнопку, которая вызывает join request (без url)
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Перейти в канал", url=f"https://t.me/c/{chat_id[4:]}/1")],
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
                ])
                await callback.message.answer(
                    "✅ У вас уже есть доступ к каналу и вы уже в нём состоите!\n"
                    "Если вы вышли из канала — используйте кнопку ниже для повторного входа.",
                    reply_markup=keyboard
                )
                return
        except Exception:
            pass  # Если не удалось проверить, продолжаем как обычно

        invite_link = get_user_invite_link(user_id)
        if not invite_link:
            # Если ссылки нет в БД, генерируем новую
            await send_invite_link(callback.message, user_id, bot)
            return
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в канал", url=invite_link)],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
        ])
        await callback.message.answer(
            "✅ У вас уже есть доступ к каналу с курсом!\nИспользуйте кнопку ниже, чтобы перейти:",
            reply_markup=keyboard
        )
        return

    # Если оплаты нет - продолжаем стандартный процесс покупки
    msg_data = get_message_by_title("Купить")
    msg_text = msg_data[2]
    await bot.send_message('admin', f"Пользователь {user_id} нажал 'Купить'")

    await callback.message.answer(
        text=msg_text,
        reply_markup=inline.get_continue_button()
    )
    await state.set_state(PurchaseStates.awaiting_continue)

# Обработка предварительной проверки платежа
@cb_handler.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@cb_handler.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):

    payment_info = message.successful_payment
    user_id = message.from_user.id
    
    # Сохраняем платеж
    save_yookassa_payment(user_id, payment_info)
    
    # Отправляем инвайт-ссылку
    await send_invite_link(message, user_id, bot)

# Функция для проверки участников канала
async def check_channel_members(bot: Bot):
    chat_id = "-1002597950609"
    try:
        # Получаем список участников (ограниченное количество)
        members_count = await bot.get_chat_member_count(chat_id)
        
        pass
        
    except Exception as e:
        print(f"Error checking channel members: {e}")

# Обработчик для новых участников канала
@cb_handler.chat_join_request()
async def handle_join_request(update: types.ChatJoinRequest, bot: Bot):
    user_id = update.from_user.id
    chat_id = update.chat.id
    
    if has_payment(user_id):
        # Одобряем запрос, если пользователь оплатил
        await update.approve()
    else:
        # Отклоняем запрос, если оплаты нет
        await update.decline()

def check(payment_id):
    payment = yookassa.Payment.find_one(payment_id)
    if payment.status == "succeeded":
        return payment.metadata
    
    return False


# Команда для ручной проверки доступа
@cb_handler.message(Command("check_access"))
async def check_access(message: Message, bot: Bot):
    user_id = message.from_user.id
    chat_id = "-1002597950609"
    
    if has_payment(user_id):
        try:
            # Проверяем, является ли пользователь участником канала
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                await message.answer("✅ Вы имеете доступ к каналу и уже в нём состоите!")
            else:
                # Создаем новую ссылку, если пользователь оплатил, но не в канале
                invite_link = await bot.create_chat_invite_link(
                    chat_id=chat_id,
                    name=f"New invite for user {user_id}",
                    expire_date=int(time.time()) + 24 * 3600,
                    member_limit=1
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Перейти в канал", url=invite_link.invite_link)]
                ])
                
                await message.answer(
                    "✅ Вы имеете доступ к каналу, но ещё не присоединились. "
                    "Используйте кнопку ниже, чтобы перейти:",
                    reply_markup=keyboard
                )
        except Exception as e:
            await message.answer("Ошибка проверки доступа. Обратитесь в поддержку.")
    else:
        await message.answer("❌ У вас нет доступа к каналу. Пожалуйста, оплатите курс.")

async def scheduled_members_check(bot: Bot):
    while True:
        await check_channel_members(bot)
        await asyncio.sleep(3600)


@cb_handler.callback_query(F.data == 'continue_to_consent')
async def continue_to_consent(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    msg_data = get_message_by_title("Согласие на обработку данных")
    msg_text = msg_data[2]

    user_id = callback.from_user.id
    user_consents[user_id] = {"data_consent": False, "offer_consent": False}
    
    await callback.message.answer(
        msg_text,
        reply_markup=get_consent_buttons(user_id),
    )

    await state.set_state(PurchaseStates.awaiting_consent)

@cb_handler.callback_query(F.data == 'proceed_to_payment')
async def proceed_to_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    user_id = callback.from_user.id

    # Проверяем текущее состояние
    current_state = await state.get_state()
    if current_state != PurchaseStates.awaiting_consent.state:
        await callback.answer("Процесс покупки уже завершён или не начат. Нажмите 'Купить' для повторного прохождения.", show_alert=True)
        return

    # Проверяем согласия
    consents = user_consents.get(user_id, {})
    if not (consents.get("data_consent") and consents.get("offer_consent")):
        await callback.answer("Необходимо подтвердить оба согласия", show_alert=True)
        return
    
    # Сохраняем согласия в БД
    save_consent(user_id, True, True)
    
    # Проверяем email в БД
    email = get_user_email(user_id)
    if not email:
        # Если email нет - запрашиваем
        await callback.message.answer("Пожалуйста, укажите ваш email для отправки чека:")
        await state.set_state(PurchaseStates.awaiting_email)
        await state.update_data(
            callback_message=callback.message,
            from_proceed_to_payment=True  # Флаг, что перешли из этого обработчика
        )
        return
    
    # Если email есть - сразу создаем платеж
    await process_payment(user_id, email, callback.message, state, bot)

async def process_payment(user_id: int, email: str, message: Message, state: FSMContext, bot: Bot):
    """Создание платежа без сохранения в БД"""
    payment_url, payment_id = await create_yookassa_payment(user_id, email)
    
    if payment_url:
        await state.update_data(
            yookassa_payment_id=payment_id,
            user_id=user_id,
            callback_message=message
        )
        
        pay_button = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить на сайте ЮKassa", url=payment_url)],
            [InlineKeyboardButton(text="Проверить оплату", callback_data="check_payment")]
        ])
        
        await message.answer("""Остался всего один шаг. Сделайте его и начните зарабатывать на земле.

Стоимость доступа: 1 рубль

Нажмите «Оплатить на сайте ЮKassa», чтобы получить пошаговый план по покупке Ваших первых участков!""", reply_markup=pay_button)
    else:
        await message.answer("Ошибка при создании платежа")

@cb_handler.message(PurchaseStates.awaiting_email)
async def process_email(message: Message, state: FSMContext, bot: Bot):
    email = message.text.strip()
    
    # Валидация email
    if not validate_email(email):
        await message.answer("❌ Пожалуйста, введите корректный email (например: example@mail.ru):")
        return
    
    # Сохраняем email
    save_user_email(message.from_user.id, email)
    
    # Получаем контекст
    state_data = await state.get_data()
    callback_message = state_data.get("callback_message")
    
    # Если перешли из обработчика proceed_to_payment
    if state_data.get("from_proceed_to_payment"):
        await process_payment(message.from_user.id, email, callback_message or message, state, bot)
    else:
        await message.answer(f"✅ Email {email} сохранен. Теперь вы можете продолжить покупку.")
    
    await state.clear()


@cb_handler.callback_query(F.data == 'consent_data')
async def consent_data(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    current_state = await state.get_state()
    if current_state != PurchaseStates.awaiting_consent.state:
        await callback.answer("Процесс покупки уже завершён или не начат. Нажмите 'Купить' для повторного прохождения.", show_alert=True)
        return
    
    if user_id not in user_consents:
        user_consents[user_id] = {"data_consent": False, "offer_consent": False}
    
    user_consents[user_id]["data_consent"] = True
    await callback.answer("Согласие на обработку персональных данных подтверждено!")
    await callback.message.edit_reply_markup(reply_markup=get_consent_buttons(user_id))


@cb_handler.callback_query(F.data == 'consent_offer')
async def consent_offer(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    current_state = await state.get_state()
    if current_state != PurchaseStates.awaiting_consent.state:
        await callback.answer("Процесс покупки уже завершён или не начат. Нажмите 'Купить' для повторного прохождения.", show_alert=True)
        return
    
    if user_id not in user_consents:
        user_consents[user_id] = {"data_consent": False, "offer_consent": False}
    
    user_consents[user_id]["offer_consent"] = True
    await callback.answer("Оферта акцептована!")
    await callback.message.edit_reply_markup(reply_markup=get_consent_buttons(user_id))



@cb_handler.callback_query(F.data == 'reviews')
async def show_reviews_to_user(callback: CallbackQuery, review_service: ReviewService, bot: Bot):
    msg_data = get_message_by_title("Отзывы о гайде")
    msg_text = msg_data[2]
    try:
        review_photos = await review_service.get_all_reviews()
        
        if not review_photos:
            await callback.answer()
            await callback.message.answer("📭 Пока нет отзывов", 
                                        reply_markup=inline.get_back_button())
            return
        
        await callback.answer()
        
        media_group = MediaGroupBuilder()
        for photo_url in review_photos[:10]:
            media_group.add_photo(media=photo_url)
        
        await bot.send_media_group(chat_id=callback.message.chat.id, 
                                 media=media_group.build())
        
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=msg_text,
            parse_mode='HTML',
            reply_markup=inline.add_back_button(inline.buy_keyboard_menu)
        )
        
        try:
            await bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id
            )
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка показа отзывов: {e}")
        await callback.message.answer("⚠️ Не удалось загрузить отзывы",
                                    reply_markup=inline.get_back_button())

@cb_handler.callback_query(F.data == 'preview')
async def handler_preview(callback: CallbackQuery, bot: Bot):
    await callback.answer()

    msg_data = get_message_by_title("Подробнее")
    msg_text = msg_data[2]

    await callback.message.edit_text(
        msg_text,
        reply_markup=inline.get_press_to_buy_button(),
    )
    

@cb_handler.callback_query(lambda c: c.data.startswith("back_to_menu_") and is_admin(c.from_user.id))
async def handler_back_to_menu(callback: CallbackQuery, bot: Bot, state: FSMContext):
    message_id = int(callback.data.split("_")[3])
    logging.debug(f"Выбрано сообщение с ID {message_id} для возврата в меню")
    messages = get_all_messages()
    selected_message = next((msg for msg in messages if msg[0] == message_id), None)
    if selected_message:
        try:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=f"{selected_message[2]}",
                parse_mode='HTML',
                reply_markup=inline.get_start_keyboard()
            )
            # Очищаем состояние редактирования
            await state.clear()
        except Exception as e:
            logging.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.message.answer(f"Ошибка при возврате в меню: {str(e)}")
    else:
        await callback.message.answer("Сообщение не найдено.")
        logging.error(f"Сообщение с ID {message_id} не найдено")
    await callback.answer()

@cb_handler.callback_query(F.data == 'support')
async def handler_support(callback: CallbackQuery):
    await callback.answer()

    
@cb_handler.callback_query(F.data == 'back_menu')
async def handler_back_menu(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await callback.message.delete()
    
    msg_data = get_message_by_title("Начать")
    msg_text = msg_data[2] 

    await callback.message.answer(
        msg_text,
        reply_markup=inline.get_start_keyboard(),
    )
    

@cb_handler.callback_query(F.data == "back_to_menu")
async def handler_back_to_menu(callback: CallbackQuery, bot: Bot, state: FSMContext):
    msg_data = get_message_by_title("Начать")
    msg_text = msg_data[2] 
    await callback.answer()

    await callback.message.edit_text(
        msg_text,
        reply_markup=inline.get_start_keyboard(),
    )