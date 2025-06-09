from aiogram import BaseMiddleware
from aiogram.types import Message

from services.session import admin_session

class AdminPhotoMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.photo:
            if not admin_session.is_active(event.from_user.id):
                await event.answer("⛔ Требуется активировать админ-режим (/admin)")
                return
        return await handler(event, data)
