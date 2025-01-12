from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.methods import GetChatMember
import logging
import asyncio
import re
from config_data.config import Config, load_config
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from aiogram.fsm.storage.memory import MemoryStorage

#Импортируем модули
from handlers import (admin_handlers, candidate_handlers, member_handlers, delegate_handlers,
        new_user_handlers, registrator_handlers, oll_users_handlers, 
      reg_process_handlers)
from data_base import data_base
from filters import filters
from keyboards import keyboards
from LEXICON.LEXICON import LEXICON


# Загружаем конфиг в переменную config
config: Config = load_config('.env')
path_db = config.db.path_db #путь к базе данных
club_id = config.tg_bot.club_id # id группы в БД (не телеграм)
print(path_db)
# Инициализируем бот и диспетчер
bot = Bot(token=config.tg_bot.token)
dp = Dispatcher()
#Записываем путь к базе данных в словарь-хранилище диспетчера для доступа в других модулях
dp['path_db'] = path_db
# Записываем id группы в словрь-храилище диспетчера
dp['club_id'] = club_id
# Настраиваем базовую конфигурацию логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] #%(levelname)-8s %(filename)s:'
           '%(lineno)d - %(name)s - %(message)s'
)

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)


# Инициализируем хранилище (создаем экземпляр класса MemoryStorage)
storage = MemoryStorage()


#егистрируем роутеры
dp.include_router(admin_handlers.router)
dp.include_router(registrator_handlers.router)
dp.include_router(member_handlers.router)
dp.include_router(candidate_handlers.router)
dp.include_router(reg_process_handlers.router)
dp.include_router(new_user_handlers.router)

dp.include_router(delegate_handlers.router)

dp.include_router(oll_users_handlers.router)

if __name__ == '__main__':
    dp.run_polling(bot)