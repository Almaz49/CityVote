from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from filters.filters import StatusFilter
from keyboards.keyboards import reg_markup, contact_markup, remove_markup
from config_data.config import Config, load_config

#инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status = 'user'))

# #Хэндлер на кманду "старт"
# @router.message(Command(commands=["start"]))
# async def process_start_command5(message: Message):
#     await bot.send_message(message.from_user.id, '''Привет, Новичок!\nЭто бот клуба избирателей!\n
# С моей помощью ты сможешь участвовать\n в голосованиях клуба. \n
# Чтобы получить все права участия, надо зарегистрироваться''',
#                          reply_markup = reg_markup)