from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from filters.filters import filter_isUser
from keyboards.keyboards import reg_keyboard, contact_keyboard, remove_keyboard
from config_data.config import Config, load_config

#инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(filter_isUser)

#Хэндлер на кманду "старт"  
@router.message(Command(commands=["start"]))
async def process_start_command5(message: Message):
    await bot.send_message(message.from_user.id, '''Привет, Новичок!\nЭто бот клуба избирателей!\n
С моей помощью ты сможешь участвовать\n в голосованиях клуба. \n
Чтобы получить все права участия, надо зарегистрироваться''',
                         reply_markup = reg_keyboard)