from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from data_base.telegram_bot_logic import status_member
import logging

class StatusMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        logging.info('\nMiddleware StatusMiddleware начала работу\n')
        try:
            user = data['event_from_user']
            user_id = user.id

            logging.info(f'Processing event of type: {type(event)}')
            logging.info(f'User ID: {user_id}')

            # Получаем статус пользователя
            status = await status_member(user_id)
            logging.info(f'Получены статусы юзера: {status}')

            if status is None:
                logging.warning(f"Status for user {user_id} is None")
                status = []  # Если статус отсутствует, используем пустой список
            else:
                status = [s.lower() for s in status]  # Нормализуем статусы к нижнему регистру

            # Добавляем статус в пользовательский словарь data
            data['data']['user_status'] = status
            logging.info(f'Создан список статусов в пользовательском словаре data: {status}')

            # Продолжаем обработку события
            return await handler(event, data)
        except Exception as e:
            logging.error(f"An error occurred in StatusMiddleware: {e}")
            logging.error(f"Event type: {type(event)}, Event data: {event}")
            return await handler(event, data)