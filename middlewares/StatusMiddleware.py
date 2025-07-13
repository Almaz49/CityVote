# модуль StatusMiddleware
import logging

from aiogram import BaseMiddleware

from data_base.db_member import (is_user_available,
                                          mark_user_as_available,
                                          extract_status_tg_id)

logger = logging.getLogger(__name__)


class StatusMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        logger.info("\nMiddleware StatusMiddleware начала работу\n")

        # Инициализируем data['data'], если его нет
        if "data" not in data:
            data["data"] = {}
        club_id = data.get("club_id")
        if not club_id:
            logger.error("club_id не найден в data")
            return
        try:
            # Проверяем наличие user в data

            if "event_from_user" not in data:
                logger.error("event_from_user не найден в data")
                return  # Прерываем обработку
            user = data["event_from_user"]
            user_id = user.id

            logger.debug(f"Processing event of type: {type(event)}")
            logger.info(f"User ID: {user_id}")

            # Проверяем, доступен ли пользователь
            is_available = await is_user_available(user_id)
            logger.debug(f"Пользователь {user_id} доступен: {is_available}")

            # Если пользователь был недоступен, но теперь взаимодействует с ботом, помечаем его как доступного
            if not is_available:
                logger.info(
                    f"Пользователь {user_id} ранее был недоступен, но теперь взаимодействует с ботом. Меняем статус на доступен."
                )
                await mark_user_as_available(user_id)

            # Получаем статус пользователя
            status = await extract_status_tg_id(club_id, user_id)
            logger.debug(f"Получены статусы юзера: {status}")

            if status is None:
                logger.warning(f"Status for user {user_id} is None")
                status = []  # Если статус отсутствует, используем пустой список
            else:
                status = [
                    s.lower() for s in status
                ]  # Нормализуем статусы к нижнему регистру

            # Добавляем статус в пользовательский словарь data
            data["data"]["user_status"] = status
            logger.info(
                f"Создан список статусов в пользовательском словаре data: {status}"
            )

            # Передаём управление следующему middleware/хэндлеру
            return await handler(event, data)

        except Exception as e:
            logger.error(f"An error occurred in StatusMiddleware: {e}")
            logger.warning(f"Event type: {type(event)}, Event data: {event}")
            raise  # Передаем исключение
