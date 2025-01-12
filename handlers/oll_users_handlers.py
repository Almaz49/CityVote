from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from keyboards.keyboards import reg_keyboard, contact_keyboard, remove_keyboard
from config_data.config import Config, load_config

#инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()

#Этот хэндлер срабатывает, если участнк почему-то оказалася без известного статуса.
#Вообще-то не должен срабатывать
@router.message(Command(commands=["start"]))
async def process_start_command6(message: Message):
    await bot.send_message(message.from_user.id,'Привет, Незнакомец!\nМеня зовут Эхо-бот!\nНапиши мне что-нибудь')





# Этот хэндлер будет срабатывать на команду "/help"
@router.message(Command(commands=['help']))
async def process_help_command(message: Message):
    await bot.send_message(message.from_user.id,
        'Напиши мне что-нибудь и в ответ '
        'я пришлю тебе твое сообщение'
    )


# Этот хэндлер будет срабатывать на команду "/cancel" в состоянии
# по умолчанию и сообщать, что эта команда работает внутри машины состояний
@router.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    await message.answer(
        text='Отменять нечего. Вы вне машины состояний',
        reply_markup=remove_keyboard
    )


# Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# кроме состояния по умолчанию, и отключать машину состояний
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из машины состояний',
        reply_markup=remove_keyboard
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()

# Этот хэндлер будет срабатывать на любые ваши текстовые сообщения,
# кроме команд "/start" и "/help"
@router.message()
async def send_echo(message: Message):
    await bot.send_message(message.from_user.id, message.text)
    

