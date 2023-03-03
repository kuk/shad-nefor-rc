
from aiogram.types import (
    ChatType,
    ChatMemberStatus
)
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.utils.exceptions import BadRequest

from neludim.log import (
    log,
    json_msg
)
from neludim.const import CHAT_ID


class PrivateMiddleware(BaseMiddleware):
    def on_pre_process(self, type):
        if type != ChatType.PRIVATE:
            raise CancelHandler

    async def on_pre_process_message(self, message, data):
        self.on_pre_process(message.chat.type)

    async def on_pre_process_callback_query(self, query, data):
        self.on_pre_process(query.message.chat.type)


class LoggingMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message, data):
        log.info(json_msg(
            user_id=message.from_user.id,
            text=message.text
        ))

    async def on_pre_process_callback_query(self, query, data):
        log.info(json_msg(
            user_id=query.from_user.id,
            data=query.data
        ))


######
#   CHAT MEMBER
######


NOT_CHAT_MEMBER_TEXT = 'Не нашел тебя в чате выпускников ШАДа. Напиши, пожалуйста, кураторам. Бот отвечает только тем кто в чатике.'


class UserNotFound(BadRequest):
    match = 'user not found'


async def is_chat_member(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(
            chat_id=chat_id,
            user_id=user_id
        )
    except UserNotFound:
        return False

    if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
        return False

    return True


class ChatMemberMiddleware(BaseMiddleware):
    def __init__(self, context):
        self.context = context
        BaseMiddleware.__init__(self)

    async def on_pre_process(self, user_id, message=None):
        if await is_chat_member(
                self.context.bot,
                chat_id=CHAT_ID,
                user_id=user_id
        ):
            return
        else:
            if message:
                await message.answer(text=NOT_CHAT_MEMBER_TEXT)

            raise CancelHandler

    async def on_pre_process_message(self, message, data):
        await self.on_pre_process(message.from_user.id, message)

    async def on_pre_process_callback_query(self, query, data):
        await self.on_pre_process(query.from_user.id)


#####
#  SETUP
######


def setup_middlewares(context):
    middlewares = [
        PrivateMiddleware(),
        LoggingMiddleware(),
        ChatMemberMiddleware(context)
    ]
    for middleware in middlewares:
        context.dispatcher.middleware.setup(middleware)
