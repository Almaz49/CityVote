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

# Фильтр на статус администратора или владельца
async def filter_isAdmin(message: Message) -> bool:
    try:
        status = await status_member(message.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False

        return 'admin' in status.lower() or 'owner' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на статус регистратора
async def filter_isRegistrator(message: Message) -> bool:
    try:
        status = await status_member(message.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False

        return 'registrator' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на статус регистратора (для callback)
async def filter_isRegistrator_call(callback: CallbackQuery) -> bool:
    try:
        status = await status_member(callback.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {callback.from_user.id} is None")
            return False

        return 'registrator' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на статус участника
async def filter_isMember(message: Message) -> bool:
    try:
        status = await status_member(message.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False

        return 'member' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на статус делегата
async def filter_isDelegate(message: Message) -> bool:
    try:
        status = await status_member(message.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False

        return 'delegate' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на статус представителя
async def filter_isProxy(message: Message) -> bool:
    try:
        status = await status_member(message.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False

        return 'proxy' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на статус кандидата
async def filter_isCandidate(message: Message) -> bool:
    try:
        status = await status_member(message.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False

        return 'candidate' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на статус пользователя
async def filter_isUser(message: Message) -> bool:
    try:
        status = await status_member(message.from_user.id)

        # Проверка на None
        if status is None:
            logging.warning(f"Status for user {message.from_user.id} is None")
            return False

        return 'user' in status.lower()
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False

# Фильтр на контакт message.contact.user_id == message.from_user.id
async def filter_contact(message: Message) -> bool:
    try:
        return message.contact and message.contact.user_id == message.from_user.id
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return False