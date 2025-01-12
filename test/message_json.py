from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
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
from data_base.telegram_bot_logic import *
from keyboards.keyboards import *


from filters.filters import filter_isAdmin
from FSMs.FSMs import FSMNewRegistrator, FSMNewVoting, FSMNewStatus
from data_base.telegram_bot_logic import (extract_new_registrator_data,
new_status_tg, all_status)
from keyboards.keyboards import *
from config_data.config import Config, load_config

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
"""
Буду изучать разные апдейты
"""

#Функция выяснения статуса участника. Если участник с таким телеграм id не обнаружен,
# заносит его в БД ,без статуса (что равнозначно статусю юзер). Возвращает список кортежей типа
#[(admin,),(registrator,)]
# В каждом кортеже только один элемент. Кортежей столько, сколько статусов у участника.



@dp.message(Command(commands=["start"]),filter_isAdmin)
async def process_start_command1(message: Message):
    await bot.send_message(message.from_user.id,
        text='Привет, Админ!\nМеня зовут Эхо-бот!\nНапиши мне что-нибудь',
                           reply_markup=confirm_markup)
        




# Этот хэндлер будет срабатывать на любой апдейт и распечатывать его

@dp.message()
async def process_new_status(message: Message):
    print(message.model_dump_json(indent=4, exclude_none=True))
#     print(message.contact.user_id)



"""
Конец экспериментального кода
"""


if __name__ == '__main__':
    dp.run_polling(bot)