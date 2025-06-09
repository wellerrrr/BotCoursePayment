from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keyboards import inline
from services.reviews import ReviewService
from services.purchasing import check_consent, save_consent
from services.commands import get_all_messages, is_admin, get_message_by_title
from handlers.start import start

import logging
logger = logging.getLogger(__name__)

cb_handler = Router()
review_service = ReviewService()

class PurchaseStates(StatesGroup):
    awaiting_continue = State()
    awaiting_consent = State()



def get_consent_buttons(user_id: int):
    data_text = "Согласен с обработкой данных ✓" if user_consents.get(user_id, {}).get("data_consent", False) else "Согласен с обработкой данных"
    offer_text = "Акцептую оферту ✓" if user_consents.get(user_id, {}).get("offer_consent", False) else "Акцептую оферту"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=data_text, callback_data="consent_data"),
            InlineKeyboardButton(text=offer_text, callback_data="consent_offer")
        ],
        [InlineKeyboardButton(text="Продолжить", callback_data="proceed_to_payment")]
    ])
    return keyboard

user_consents = {}

@cb_handler.callback_query(F.data == 'buy')
async def handler_buy(callback: CallbackQuery, state: FSMContext):
    msg_data = get_message_by_title("Продолжить покупку")
    msg_text = msg_data[2] 
    await callback.answer()
    user_id = callback.from_user.id
    data_consent, offer_consent = check_consent(user_id)
    if data_consent and offer_consent:
        await callback.message.answer(
            """Чтобы оплатить переходите по ссылке: https://example.com

P.S. Если у вас проблемы с оплатой, нажмите кнопку "Не получается оплатить", и мы поможем""",
            reply_markup=inline.get_buy_button()
        )
        return

    await callback.message.answer(
        text=msg_text,
        reply_markup=inline.get_continue_button()
    )
    await state.set_state(PurchaseStates.awaiting_continue)

@cb_handler.callback_query(F.data == 'continue_to_consent')
async def continue_to_consent(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    user_consents[user_id] = {"data_consent": False, "offer_consent": False}
    
    await callback.message.answer(
        "Перед покупкой необходимо согласиться с обработкой персональных данных и акцептовать оферту.\n\n"
        "Ознакомьтесь с документами:\n"
        "[Политика конфиденциальности](https://your-site.com/privacy)\n"
        "[Оферта](https://your-site.com/offer)\n\n"
        "Подтвердите согласие, нажав на кнопки ниже:",
        reply_markup=get_consent_buttons(user_id),
        parse_mode="Markdown"
    )

    await state.set_state(PurchaseStates.awaiting_consent)


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


@cb_handler.callback_query(F.data == 'proceed_to_payment')
async def proceed_to_payment(callback: CallbackQuery, state: FSMContext):
    msg_data = get_message_by_title("Оплата")
    msg_text = msg_data[2]
    user_id = callback.from_user.id
    current_state = await state.get_state()
    if current_state != PurchaseStates.awaiting_consent.state:
        await callback.answer("Процесс покупки уже завершён или не начат. Нажмите 'Купить' для повторного прохождения.", show_alert=True)
        return
    
    if user_consents.get(user_id, {}).get("data_consent") and user_consents.get(user_id, {}).get("offer_consent"):

        save_consent(user_id, True, True)
        
        await callback.answer()

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            msg_text,
            reply_markup=inline.get_buy_button()
        )
        await state.clear()
        user_consents.pop(user_id, None)
    else:
        await callback.answer("Пожалуйста, подтвердите оба согласия перед продолжением.", show_alert=True)

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