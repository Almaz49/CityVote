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

#Создаем контекстный менеджер для работы с базой данных
class Database:
    def __init__(self, db_name):
        self.db_name = db_name
            
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit() # Если ошибок нет, подтверждаем изменения
        else:
            self.conn.rollback() # В случае ошибки откатываем изменения
#             self.exc_val = exc_val
#             print(exc_val)
#             return(exc_val)
            #print('type:',exc_type, ' value:', exc_val, 'traceback: ', exc_tb)
            #return(exc_val)
        self.conn.close() # Закрываем соединение
        


with Database(path_db) as cursor:
    cursor.execute(
            '''
            SELECT MAX(time_election), variant_id FROM Elections
            WHERE (
            member_id = ? AND variant_id IN
            (SELECT id FROM Variants WHERE vote_id IN
               (SELECT vote_id FROM Variants WHERE id = ?)
               )
            )
            ''',(1, 1)
            )
    print(cursor.fetchall())




# Этот хэндлер будет срабатывать на любой апдейт и распечатывать его




"""
Конец экспериментального кода
"""


if __name__ == '__main__':
    dp.run_polling(bot)