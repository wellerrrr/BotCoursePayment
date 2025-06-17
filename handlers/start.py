from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram import Router, F, Bot
from aiogram.types import Message

from keyboards import inline

from services.commands import get_message_by_title

router = Router()

@router.message(CommandStart())
async def start(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    print(f'User id: {user_id}\nUsername: {username}')

    msg = get_message_by_title("Начать")
    if msg:
        await message.answer(msg[2],
                             reply_markup=inline.get_start_keyboard())
    
@router.message(F.forward_from_chat)
async def handle_forward(message: Message):
    if message.forward_from_chat.type == "channel":
        await message.reply(f"ID канала: <code>{message.forward_from_chat.id}</code>", 
                          parse_mode="HTML")