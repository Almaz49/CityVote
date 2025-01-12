from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder,InlineKeyboardBuilder
from aiogram.types import CallbackQuery
from aiogram.methods import GetChatMember
from aiogram.filters.callback_data import CallbackData
import logging
import sqlite3
import asyncio
import re
from config_data.config import Config, load_config
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from LEXICON.LEXICON import LEXICON

#from aiogram import types


# Загружаем конфиг в переменную config
config: Config = load_config('.env')
path_db = 'dbg1.db' #путь к базе данных
# Инициализируем бот и диспетчер
bot = Bot(token=config.tg_bot.token)
dp = Dispatcher()
# Настраиваем базовую конфигурацию логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] #%(levelname)-8s %(filename)s:'
           '%(lineno)d - %(name)s - %(message)s'
)

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)


"""
Ниже - экспериментальный код
"""

# Функция для формирования инлайн-клавиатуры на лету
def create_inline_kb(width: int,
                     *args: str,
                     **kwargs: str) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из аргументов args и kwargs
    if args:
        for button in args:
            buttons.append(InlineKeyboardButton(
                text=LEXICON[button] if button in LEXICON else button,
                callback_data=button))
    if kwargs:
        for button, text in kwargs.items():
            buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=button))

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()

    
all_st = ['admin','registrator','member','user','proxy','delegate']
status = ['member','user']
vacansy = list(set(all_st)-set(status)-{'owner'})
status = list(set(status)-{'owner'})
keyboards = []
for item in vacansy:
    keyboards.append('AppointAs_'+item)
for item in status:
    keyboards.append('not_'+item)
print(keyboards)
markup = create_inline_kb(1,*keyboards)

@dp.message(Command(commands=["start"]))
async def process_start_command1(message: Message):
    await bot.send_message(message.from_user.id,
        text='Привет!\nМеня зовут Эхо-бот!\nНапиши мне что-нибудь',
              reply_markup = markup )
    
    
"""
Конец экспериментального кода
"""


if __name__ == '__main__':
    dp.run_polling(bot)