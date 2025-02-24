# Модуль filters
import logging
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram import Bot, Dispatcher, F
from aiogram.types import CallbackQuery, Message, PhotoSize
from aiogram.filters import BaseFilter
from data_base.telegram_bot_logic import status_member

# Настройка логирования
logging.basicConfig(level=logging.INFO)



"""
ФИЛЬТРЫ
"""

# Универсальный фильтр для проверки статуса пользователя

class StatusFilter(BaseFilter):
    def __init__(self, required_status: list[str]):
        """
        Инициализация фильтра с требуемым статусом.
        :param required_status: Требуемый статус (например, "admin", "member").
        """
        self.required_status = required_status

    async def __call__(self, event: Message, data: dict) -> bool:
        """
        Проверяет, содержит ли список статусов пользователя требуемый статус.
        :param event: Объект события (например, Message).
        :param data: Словарь данных, содержащий user_status.
        :return: True, если статус найден, иначе False.
        """
        # Извлекаем user_status из словаря data
        user_status = data.get("user_status", [])
        logging.info(f"Проверка статуса в фильтре: требуется {self.required_status}, текущий статус {user_status}")
        flag = False
        for status in self.required_status:
            if status in user_status:
                flag = True
        return flag

# # Фильтр на статус администратора
# class filter_isAdmin(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="admin")


# # Фильтр на статус владельца
# class filter_isOwner(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="owner")


# # Фильтр на статус регистратора
# class filter_isRegistrator(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="registrator")


# # Фильтр на статус участника
# class filter_isMember(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="member")


# # Фильтр на статус делегата
# class filter_isDelegate(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="delegate")


# # Фильтр на статус представителя
# class filter_isProxy(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="proxy")


# # Фильтр на статус кандидата
# class filter_isCandidate(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="candidate")


# # Фильтр на статус пользователя
# class filter_isUser(StatusFilter):
#     def __init__(self):
#         super().__init__(required_status="user")


# Фильтр на контакт (message.contact.user_id == message.from_user.id)
class filter_contact(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        """
        Проверяет, соответствует ли контакт отправителю сообщения.
        :param message: Объект сообщения.
        :return: True, если контакт совпадает с отправителем, иначе False.
        """
        try:
            return message.contact and message.contact.user_id == message.from_user.id
        except Exception as e:
            logging.error(f"An error occurred in ContactFilter: {e}")
            return False