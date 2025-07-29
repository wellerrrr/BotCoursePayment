from aiogram import Router, F, Bot, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keyboards import inline
from services.reviews import ReviewService
from services.purchasing import check_consent, save_consent, save_invite_link, save_payment, has_payment
from services.commands import get_all_messages, is_admin, get_message_by_title
from config import config

from aiogram.types import LabeledPrice
from aiogram.filters import Command
import time
import asyncio

import logging
logger = logging.getLogger(__name__)

cb_handler = Router()
review_service = ReviewService()

class PurchaseStates(StatesGroup):
    awaiting_continue = State()
    awaiting_consent = State()



user_consents = {}
def get_consent_buttons(user_id: int):
    data_text = "✓ Согласен с обработкой данных" if user_consents.get(user_id, {}).get("data_consent", False) else "Согласен с обработкой данных"
    offer_text = "✓ Акцептую оферту" if user_consents.get(user_id, {}).get("offer_consent", False) else "Акцептую оферту"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=data_text, callback_data="consent_data"),
            InlineKeyboardButton(text=offer_text, callback_data="consent_offer")
        ],
        [InlineKeyboardButton(text="Продолжить", callback_data="proceed_to_payment")]
    ])
    return keyboard

@cb_handler.callback_query(F.data == 'buy')
async def handler_buy(callback: CallbackQuery, state: FSMContext, bot: Bot):
    msg_data = get_message_by_title("Купить")
    msg_text = msg_data[2]
    await callback.answer()
    user_id = callback.from_user.id
    data_consent, offer_consent = check_consent(user_id)
    if data_consent and offer_consent:
        prices = [LabeledPrice(label="Курс Выкуп Земли 2025", amount=990000)]
        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title="Курс Выкуп Земли 2025",
            description="""Финальный шаг к Вашим первым участкам

Сумма к оплате: 9.900 руб

Нажмите «Заплатить», чтобы начать свой путь земельного инвестора прямо сейчас""",
            provider_token=config.PAYMENTS_TOKEN,
            payload="test-invoice-payload",
            currency="RUB",
            prices=prices,
            start_parameter="test-payment",
            need_email=False,
        )
        await callback.message.edit_reply_markup(reply_markup=inline.get_buy_button())
        return

    await callback.message.answer(
        text=msg_text,
        reply_markup=inline.get_continue_button()
    )
    await state.set_state(PurchaseStates.awaiting_continue)

# Обработка предварительной проверки платежа
@cb_handler.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@cb_handler.message(F.content_type == types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: Message, bot: Bot):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    chat_id = "-1002597950609"  # ID приватного канала

    # Сохраняем информацию о платеже
    save_payment(user_id, payment_info)

    # Генерация одноразовой инвайт-ссылки
    try:
        invite_link: types.ChatInviteLink = await bot.create_chat_invite_link(
            chat_id=chat_id,
            name=f"Invite for user {user_id}",
            expire_date=int(time.time()) + 24 * 3600,  # Ссылка активна 24 часа
            member_limit=1  # Только один пользователь может использовать
        )

        # Сохранение ссылки в базе данных
        save_invite_link(user_id, invite_link.invite_link)

        # Создание инлайн-кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в канал", url=invite_link.invite_link)]
        ])

        # Отправка сообщения с кнопкой
        await message.answer(
            """Спасибо за покупку!

Ваш доступ к материалам курса находится в закрытом Telegram-канале. Нажмите кнопку ниже, чтобы перейти.

**Важно**: Эта ссылка одноразовая и предназначена только для вас. Не передавайте её другим!""",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer("Произошла ошибка при создании ссылки. Обратитесь в поддержку.")
        print(f"Error creating invite link: {e}")

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
    user_id = callback.from_user.id
    current_state = await state.get_state()
    if current_state != PurchaseStates.awaiting_consent.state:
        await callback.answer("Процесс покупки уже завершён или не начат. Нажмите 'Купить' для повторного прохождения.", show_alert=True)
        return
    
    if user_consents.get(user_id, {}).get("data_consent") and user_consents.get(user_id, {}).get("offer_consent"):

        save_consent(user_id, True, True)
        
        user_id = callback.from_user.id
        data_consent, offer_consent = check_consent(user_id)
        if data_consent and offer_consent:
            prices = [LabeledPrice(label="Курс Выкуп Земли 2025", amount=990000)]
            await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title="Курс Выкуп Земли 2025",
            description="""Финальный шаг к Вашим первым участкам

\nСумма к оплате: 9.900 руб

Нажмите «Заплатить», чтобы начать свой путь земельного инвестора прямо сейчас""",
            provider_token=config.PAYMENTS_TOKEN,
            payload="test-invoice-payload",
            currency="RUB",
            prices=prices,
            start_parameter="test-payment",
            need_email=False,
        )
    else:
        await callback.answer("Пожалуйста, подтвердите оба согласия перед продолжением.", show_alert=True)


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

    msg_data = get_message_by_title("Посмотреть, что внутри")
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