
from json import (
    loads as parse_json,
    dumps as format_json
)

from aiogram.types import Update

import pytest

from neludim.bot.bot import (
    Bot,
    Dispatcher,
)
from neludim.bot.middlewares import setup_middlewares
from neludim.bot.filters import setup_filters
from neludim.bot.handlers import setup_handlers
from neludim.schedule import (
    Schedule,
    START_DATE,
)
from neludim.db import DB
from neludim.context import Context
from neludim.obj import (
    User,
    Intro,
    Contact,
)
from neludim.const import (
    MONTH,

    CONFIRM_STATE,
    FAIL_STATE,
)


class FakeBot(Bot):
    def __init__(self):
        Bot.__init__(self, '123:faketoken')
        self.trace = []

    async def request(self, method, data):
        json = format_json(data, ensure_ascii=False)
        self.trace.append([method, json])
        return {}


class FakeDB(DB):
    def __init__(self):
        DB.__init__(self)
        self.chat_states = {}
        self.users = []
        self.contacts = []

    async def set_chat_state(self, id, state):
        self.chat_states[id] = state

    async def get_chat_state(self, id):
        return self.chat_states.get(id)

    async def put_user(self, user):
        await self.delete_user(user.user_id)
        self.users.append(user)

    async def get_user(self, user_id):
        for user in self.users:
            if user.user_id == user_id:
                return user

    async def delete_user(self, user_id):
        self.users = [
            _ for _ in self.users
            if _.user_id != user_id
        ]

    async def put_contact(self, contact):
        await self.delete_contact(contact.key)
        self.contacts.append(contact)

    async def get_contact(self, key):
        for contact in self.contacts:
            if contact.key == key:
                return contact

    async def delete_contact(self, key):
        self.contacts = [
            _ for _ in self.contacts
            if _.key != key
        ]


class FakeSchedule(Schedule):
    def now(self):
        return START_DATE


class FakeContext(Context):
    def __init__(self):
        Context.__init__(self)
        self.bot = FakeBot()
        self.dispatcher = Dispatcher(self.bot)
        self.db = FakeDB()
        self.schedule = FakeSchedule()


@pytest.fixture(scope='function')
def context():
    context = FakeContext()
    setup_middlewares(context)
    setup_filters(context)
    setup_handlers(context)

    Bot.set_current(context.bot)
    Dispatcher.set_current(context.dispatcher)

    return context


async def process_update(context, json):
    data = parse_json(json)
    update = Update(**data)
    await context.dispatcher.process_update(update)


def match_trace(trace, etalon):
    if len(trace) != len(etalon):
        return False

    for (method, json), (etalon_method, etalon_match) in zip(trace, etalon):
        if method != etalon_method:
            return False

        if etalon_match not in json:
            return False

    return True


######
#  START
######


START_JSON = '{"message": {"message_id": 2, "from": {"id": 113947584, "is_bot": false, "first_name": "Alexander", "last_name": "Kukushkin", "username": "alexkuk", "language_code": "ru"}, "chat": {"id": 113947584, "first_name": "Alexander", "last_name": "Kukushkin", "username": "alexkuk", "type": "private"}, "date": 1659800990, "text": "/start", "entities": [{"type": "bot_command", "offset": 0, "length": 6}]}}'


async def test_start(context):
    await process_update(context, START_JSON)
    assert match_trace(context.bot.trace, [
        ['setMyCommands', '{"commands"'],
        ['sendMessage', '{"chat_id": 113947584, "text": "Бот организует']
    ])
    assert context.db.users == [User(user_id=113947584, username='alexkuk', intro=Intro(name='Alexander Kukushkin'))]


#######
#  INTRO
######


async def test_edit_name(context):
    context.db.users = [User(user_id=113947584, intro=Intro())]
    await process_update(context, START_JSON.replace('/start', '/edit_intro'))
    await process_update(context, START_JSON.replace('/start', '/edit_name'))
    await process_update(context, START_JSON.replace('/start', 'Alexander Kukushkin'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', '{"chat_id": 113947584, "text": "Имя:'],
        ['sendMessage', '{"chat_id": 113947584, "text": "Напиши своё настоящее имя'],
        ['sendMessage', '{"chat_id": 113947584, "text": "Имя: Alexander Kukushkin'],
    ])
    assert context.db.users[0].intro.name == 'Alexander Kukushkin'


async def test_edit_city(context):
    context.db.users = [User(user_id=113947584, intro=Intro())]
    await process_update(context, START_JSON.replace('/start', '/edit_city'))
    await process_update(context, START_JSON.replace('/start', 'Moscow'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', '{"chat_id": 113947584, "text": "Напиши город'],
        ['sendMessage', 'Город: Moscow'],
    ])
    assert context.db.users[0].intro.city == 'Moscow'


async def test_edit_links(context):
    context.db.users = [User(user_id=113947584, intro=Intro())]
    await process_update(context, START_JSON.replace('/start', '/edit_links'))
    await process_update(context, START_JSON.replace('/start', 'vk.com/alexkuk'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', '{"chat_id": 113947584, "text": "Накидай ссылок'],
        ['sendMessage', 'Ссылки: vk.com/alexkuk'],
    ])
    assert context.db.users[0].intro.links == 'vk.com/alexkuk'


async def test_edit_about(context):
    context.db.users = [User(user_id=113947584, intro=Intro())]
    await process_update(context, START_JSON.replace('/start', '/edit_about'))
    await process_update(context, START_JSON.replace('/start', 'Закончил ШАД, работал в Яндексе'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', '{"chat_id": 113947584, "text": "Напиши о себе'],
        ['sendMessage', 'Закончил ШАД, работал в Яндексе'],
    ])
    assert context.db.users[0].intro.about == 'Закончил ШАД, работал в Яндексе'


async def test_empty_edit(context):
    context.db.users = [User(user_id=113947584, intro=Intro(name='A K'))]
    await process_update(context, START_JSON.replace('/start', '/edit_name'))
    await process_update(context, START_JSON.replace('/start', '/empty'))
    assert context.db.users[0].intro.name is None


async def test_cancel_edit(context):
    context.db.users = [User(user_id=113947584, intro=Intro(name='A K', links='vk.com/alexkuk'))]
    await process_update(context, START_JSON.replace('/start', '/edit_links'))
    await process_update(context, START_JSON.replace('/start', '/cancel'))

    assert context.db.users == [User(user_id=113947584, intro=Intro(name='A K', links='vk.com/alexkuk'))]


#######
#   PARTICIPATE/PAUSE
#######


async def test_participate(context):
    context.db.users = [User(user_id=113947584)]
    await process_update(context, START_JSON.replace('/start', '/participate'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', 'Пометил, что участвуешь'],
    ])

    user = context.db.users[0]
    assert user.agreed_participate == context.schedule.now()
    assert user.paused is None


async def test_pause(context):
    context.db.users = [User(user_id=113947584)]
    await process_update(context, START_JSON.replace('/start', '/pause_month'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', 'Поставил встречи на паузу'],
    ])

    user = context.db.users[0]
    assert user.agreed_participate is None
    assert user.paused == context.schedule.now()
    assert user.pause_period == MONTH


#######
#  CONTACT
######


async def test_show_no_contact(context):
    context.db.users = [User(user_id=113947584, partner_user_id=None)]
    await process_update(context, START_JSON.replace('/start', '/show_contact'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', 'Бот не назначил'],
    ])


async def test_show_contact(context):
    context.db.users = [User(user_id=113947584, partner_user_id=113947584, intro=Intro())]
    context.db.contacts = [Contact(week_index=0, user_id=113947584, partner_user_id=113947584)]
    await process_update(context, START_JSON.replace('/start', '/show_contact'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', 'Контакт собеседника'],
    ])


async def test_confirm_contact(context):
    context.db.users = [User(user_id=113947584, partner_user_id=113947584)]
    context.db.contacts = [Contact(week_index=0, user_id=113947584, partner_user_id=113947584)]
    await process_update(context, START_JSON.replace('/start', '/confirm_contact'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', 'получилось договориться'],
    ])
    assert context.db.contacts[0].state == CONFIRM_STATE


async def test_fail_contact(context):
    context.db.users = [User(user_id=113947584, partner_user_id=113947584)]
    context.db.contacts = [Contact(week_index=0, user_id=113947584, partner_user_id=113947584)]
    await process_update(context, START_JSON.replace('/start', '/fail_contact'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', 'встреча не состоится'],
    ])
    assert context.db.contacts[0].state == FAIL_STATE


async def test_contact_feedback(context):
    context.db.users = [User(user_id=113947584, partner_user_id=113947584, intro=Intro())]
    context.db.contacts = [Contact(week_index=0, user_id=113947584, partner_user_id=113947584)]
    await process_update(context, START_JSON.replace('/start', '/contact_feedback'))
    await process_update(context, START_JSON.replace('/start', '3'))

    assert match_trace(context.bot.trace, [
        ['sendMessage', 'очень плохо'],
        ['sendMessage', 'Фидбек'],
    ])
    assert context.db.contacts[0].feedback == '3'


#######
#   OTHER/STUB
#######


async def test_other(context):
    await process_update(context, START_JSON.replace('/start', 'abc'))
    assert match_trace(context.bot.trace, [
        ['sendMessage', 'Бот ответчает только на команды']
    ])