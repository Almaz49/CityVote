from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery
from aiogram.methods import GetChatMember
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)

from data_base.telegram_bot_logic import status_member

"""
ФИЛЬТРЫ

Надо исправить фильтры
"""

#Фильтры на статус:

def filter_isAdmin (message: Message) -> bool:
    return 'admin' in status_member(message.from_user.id) 

def filter_isRegistrator (message: Message) -> bool:
    return 'registrator' in  status_member(message.from_user.id)

def filter_isRegistrator_call (callback: CallbackQuery) -> bool:
    return 'registrator' in  status_member(callback.from_user.id)

#[callback.from_user.id]

def filter_isMember (message: Message) -> bool:
    return 'member' in  status_member(message.from_user.id)

def filter_isDelegate (message: Message) -> bool:
    return 'delegate' in  status_member(message.from_user.id)

def filter_isProxy (message: Message) -> bool:
    return 'proxy' in  status_member(message.from_user.id)

def filter_isCandidate (message: Message) -> bool:
    return 'candidate' in  status_member(message.from_user.id)

def filter_isUser (message: Message) -> bool:
    return 'user' in  status_member(message.from_user.id)

#Фильтр на контакт message.contact.user_id == message.from_user.id
def filter_contact (message: Message) -> bool:
    return message.contact.user_id == message.from_user.id

