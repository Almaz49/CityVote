# Модуль main.py - основной цикл бота

import logging
from logging.handlers import RotatingFileHandler
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Message
from aiogram.methods import GetChatMember
from aiogram.fsm.storage.memory import MemoryStorage
from config_data.config import Config, load_config
from middlewares import LoggingAndErrorHandlingMiddleware, SafeEditMiddleware, StatusMiddleware
from handlers import (
    admin_handlers, candidate_handlers, member_handlers, delegate_handlers, owner_handlers,
    new_user_handlers, registrator_handlers, oll_users_handlers, reg_process_handlers,
    chat_member_handlers, last_handlers
)
from data_base import data_base
from filters import filters
from keyboards import keyboards
from LEXICON.LEXICON import LEXICON

# Загружаем конфигурацию из файла .env

config: Config = load_config('.env')

# Проверяем наличие обязательных параметров в конфигурации
if not config.tg_bot.token or not config.db.path_db or not config.tg_bot.club_id:
    raise ValueError("Необходимо указать все обязательные параметры в конфигурации")

path_db = config.db.path_db  # путь к базе данных
club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)

# Инициализируем бот и диспетчер
bot = Bot(token=config.tg_bot.token)
dp = Dispatcher(storage=MemoryStorage())

# Записываем путь к базе данных и id группы в словарь-хранилище диспетчера для доступа в других модулях
dp['path_db'] = path_db
dp['club_id'] = club_id



# Настраиваем базовую конфигурацию логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)

# Тестовое сообщение
logger.info("Логгирование настроено в main.py")





# Регистрируем middleware
dp.update.middleware(LoggingAndErrorHandlingMiddleware())  # Первым идет логгирование
dp.update.middleware(StatusMiddleware())
dp.update.middleware(SafeEditMiddleware())  # Затем middleware для safe_edit

# Регистрируем роутеры
routers = [
    member_handlers.router,
    new_user_handlers.router,
    delegate_handlers.router,
    registrator_handlers.router,
    admin_handlers.router,
    owner_handlers.router,
    candidate_handlers.router,
    reg_process_handlers.router,
    oll_users_handlers.router,
    chat_member_handlers.router,
    last_handlers.router
]


for router in routers:
    if router is not None:
        dp.include_router(router)

async def main():
    try:
        await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "chat_member",  "my_chat_member","commands"]
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())