# Модуль last_handlers
# В нем хэндлеры, которые работают для всех пользователей
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from data_base.data_base import list_of_votings, list_of_variants, extract_voting_status
from keyboards.keyboards import user_menu, remove_markup, create_inline_kb, confirm_markup
from services.services import not_votist_because_proxy_quit, votist_because_proxy_returned, leave_club
from config_data.config import Config, load_config
import logging
from utils import log_handler_call
from LEXICON.LEXICON import LEXICON
from FSMs.FSMs import FSM_become_proxy, FSM_leave_club


# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')

# Инициализируем роутер уровня модуля
router = Router()

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#       В самом конце !
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


# Хэндлер для текстовых сообщений, не являющихся командами
@router.message()
@log_handler_call
async def send_echo(message: Message,data:dict):
    """
    Обработчик эхо-сообщений.
    Отправляет обратно текстовые сообщения пользователя.
    """
    logger.info(f"Пользователь {message.from_user.id} отправил сообщение: {message.text}.")
    await message.answer(
        text=f'Вы написали: "{message.text}".\n'
        'Ваше сообщение не было обработано\n'
             'Если вам нужна помощь, используйте команду /help.',
        reply_markup = await user_menu(message.from_user.id,data['user_status'])
    )

# Хэндлер для нажатия на кнопку не пойманную другими хэндлерами
@router.callback_query()
@log_handler_call
async def send_echo_cb(callback: CallbackQuery,data:dict):
    """
    Обработчик эхо-сообщений.
    Отправляет обратно текстовые сообщения пользователя.
    """
    logger.info(f"Пользователь {callback.from_user.id} нажал кнопку: {callback.data}.")
    await callback.message.answer(
        text=f'Вы нажали кнопку: "{callback.data}".\n'
        'Она не была обработана'
             'Если вам нужна помощь, используйте команду /help.',
        reply_markup = await user_menu(callback.from_user.id,data['user_status'])
    )