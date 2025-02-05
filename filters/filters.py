# Модуль filters
import logging
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery, Message, PhotoSize
from data_base.telegram_bot_logic import status_member

# Настройка логирования
logging.basicConfig(level=logging.INFO)

"""
ФИЛЬТРЫ
"""





# Универсальный фильтр от Qwen
async def filter_by_status(message: Message, required_status: str) -> bool:
    try:
        status = await status_member(message.from_user.id)
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False
        return required_status in [s.lower() for s in status]
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Пример использования универсального фильра:
async def filter_isAdmin(message: Message) -> bool:
    return await filter_by_status(message, 'admin')

async def filter_isOwner(message: Message) -> bool:
    return await filter_by_status(message, 'owner')

async def filter_isRegistrator(message: Message) -> bool:
    return await filter_by_status(message, 'registrator')



# Фильтр на статус участника
async def filter_isMember(message: Message) -> bool:
    return await filter_by_status(message, 'member')


# Фильтр на статус делегата
async def filter_isDelegate(message: Message) -> bool:
    return await filter_by_status(message, 'delegate')


# Фильтр на статус представителя
async def filter_isProxy(message: Message) -> bool:
    return await filter_by_status(message, 'proxy')


# Фильтр на статус кандидата
async def filter_isCandidate(message: Message) -> bool:
    return await filter_by_status(message, 'candidate')


# Фильтр на статус пользователя
async def filter_isUser(message: Message) -> bool:
    return await filter_by_status(message, 'user')



# Фильтр на контакт message.contact.user_id == message.from_user.id
async def filter_contact(message: Message) -> bool:
    try:
        return message.contact and message.contact.user_id == message.from_user.id
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False