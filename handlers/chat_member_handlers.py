# Модуль chat_member_handlers
# В нем хэндлеры, которые работают для изменения статуса бота в чатах и телеграм - каналах
# либо статусов пользователей
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.text_decorations import html_decoration as html
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from data_base.data_base import *
from keyboards.keyboards import user_menu, remove_markup, create_inline_kb, confirm_markup, return_to_main_menu_markup
from services.services import not_votist_because_proxy_quit, votist_because_proxy_returned, leave_club
from config_data.config import Config, load_config
import logging
from utils import log_handler_call
from LEXICON.LEXICON import LEXICON
from FSMs.FSMs import FSM_become_proxy, FSM_leave_club


# Настройка логирования
logger = logging.getLogger(__name__)

# # Загружаем конфиг в переменную config
# config: Config = load_config('.env')

# Инициализируем роутер уровня модуля
router = Router()

# Хэндлер для события изменения статуса члена чата
@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
)
@log_handler_call
async def handle_user_unblock(event: ChatMemberUpdated):
    """
    Срабатывает, когда пользователь разблокирует бота.
    """
    tg_id = event.from_user.id  # ID пользователя
    logger.info(f"Пользователь {tg_id} разблокировал бота.")

    # Обновляем статус пользователя в базе данных
    await mark_user_as_available(tg_id)

# Хэндлер для события блокировки бота
@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION)
)
@log_handler_call
async def handle_user_block(event: ChatMemberUpdated):
    """
    Срабатывает, когда пользователь блокирует бота.
    """
    tg_id = event.from_user.id  # ID пользователя
    logger.warning(f"Пользователь {tg_id} заблокировал бота.")

    # Обновляем статус пользователя в базе данных
    await mark_user_as_unavailable(tg_id, reason="Бот заблокирован")