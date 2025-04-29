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
from utils import log_handler_call, help_message
from LEXICON.LEXICON import LEXICON
from FSMs.FSMs import FSM_become_proxy, FSM_leave_club