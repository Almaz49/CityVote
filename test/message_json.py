import asyncio
import logging
import re
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import GetChatMember
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton,
                           KeyboardButtonPollType, Message, PhotoSize,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config_data.config import Config, load_config

# from data_base.telegram_bot_logic import *
# from keyboards.keyboards import *


# from data_base.telegram_bot_logic import (extract_new_registrator_data,
# new_status_tg, all_status)
# from keyboards.keyboards import *
# from config_data.config import Config, load_config

# from aiogram import types


# Загружаем конфиг в переменную config
config: Config = load_config(".env")
path_db = "dbg1.db"  # путь к базе данных
# Инициализируем бот и диспетчер
bot = Bot(token=config.tg_bot.token)
dp = Dispatcher()
# Настраиваем базовую конфигурацию логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] #%(levelname)-8s %(filename)s:"
    "%(lineno)d - %(name)s - %(message)s",
)

# Инициализируем логгер модуля
logger = logging.getLogger(__name__)


"""
Ниже - экспериментальный код
"""
"""
Буду изучать разные апдейты
"""


# Хэндлер для команды /start
@dp.message(Command(commands=["start"]))
async def process_start_command(message: Message, data: dict):
    """
    Обработчик команды /start.
    Отправляет приветственное сообщение и главное меню.
    """
    try:
        text = "Привет!\nЭто бот для проведения голосований.\n"
        # Клавиатура для отправки контакта
        contact_btn = KeyboardButton(text="Отправить телефон", request_contact=True)
        markup = ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True, keyboard=[[contact_btn]]
        )

        await message.answer(text=text, reply_markup=markup)
        logging.info(f"Пользователь {message.from_user.id} начал работу с ботом.")
    except Exception as e:
        logging.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer(text="Произошла ошибка при загрузке главного меню.")


# Этот хэндлер будет срабатывать на любой апдейт и распечатывать его


@dp.message()
async def process_new_status(message: Message):
    print(message.model_dump_json(indent=4, exclude_none=True))


#     print(message.contact.user_id)


"""
Конец экспериментального кода
"""


if __name__ == "__main__":
    dp.run_polling(bot)
