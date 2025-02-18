# logging_middleware.py  # Middleware для логгирования и обработки исключений
from aiogram import BaseMiddleware
from aiogram.types import Update
import logging
import traceback
from pprint import pformat

class LoggingAndErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        # logging.info(f"Data in LoggingAndErrorHandlingMiddleware: {data}\n")
        try:
            if isinstance(event, Update):
                user_id = event.from_user.id if hasattr(event, "from_user") and event.from_user else "Unknown"
                event_type = event.__class__.__name__
                logging.info(f"Получено событие {event_type} от пользователя {user_id}: {event}\n")

            # Создаем ключ 'data', если его еще нет
            if 'data' not in data:
                data['data'] = {

                    # Добавьте другие необходимые данные
                }
                logging.info(f'Создан словарь дата в мидлваре логировани \n\n')



            response = await handler(event, data)

            logging.info(f'Данные data после прохождения хэндлера: \n{pformat(data)}\n')



            return response


        except Exception as e:
            logging.error(f"Необработанное исключение в хэндлере: {e}\n{traceback.format_exc()}")

            if hasattr(event, "message") and event.message:
                await event.message.answer(
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
                )
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.message.answer(
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
                )