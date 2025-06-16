# Модуль filters
import logging
from typing import Union

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

# Настройка логирования
logger = logging.getLogger(__name__)


"""
ФИЛЬТРЫ
"""


# Универсальный фильтр для проверки статуса пользователя
class StatusFilter(BaseFilter):
    def __init__(self, required_status: list):
        self.required_status = required_status

    async def __call__(self, event: Union[Message, CallbackQuery], data: dict) -> bool:
        # Логируем тип события
        if isinstance(event, Message):
            logging.debug("Фильтр вызван для Message")
        elif isinstance(event, CallbackQuery):
            logging.debug("Фильтр вызван для CallbackQuery")
        else:
            logging.info(f"Не определилось событие {event} при вызове фильтра")

        # Извлекаем user_status из словаря data
        user_status = data.get("user_status", [])

        logging.debug(f"Фильтр получил статус пользователя {user_status}")

        # Проверяем статус пользователя
        if not user_status:
            logging.warning("user_status не найден в данных middleware!")
            return False

        result = any(status in user_status for status in self.required_status)
        logging.info(
            f"Проверка статуса: требуется {self.required_status}, текущий статус {user_status} → {result}"
        )
        return result


# Фильтр проверяющий, свой ли контакт прислал пользователь
class ContactFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        try:
            # Проверка наличия контакта и совпадения user_id
            if message.contact is None or message.from_user is None:
                return False

            return message.contact.user_id == message.from_user.id
        except Exception as e:
            logging.error(f"Ошибка в фильтре ContactFilter: {e}")
            return False
