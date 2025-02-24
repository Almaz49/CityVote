# logging_middleware.py  # Middleware для логгирования и обработки исключений
from aiogram import BaseMiddleware
from aiogram.types import Update
import logging
import traceback
from pprint import pformat
from data_base.telegram_bot_logic import member_id_tg

class LoggingAndErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        # logging.info(f"Data in LoggingAndErrorHandlingMiddleware: {pformat(data)}\n")
        logging.info('\n Middleware logging_middleware started work\n')
        try:
            if isinstance(event, Update):
                user = data['event_from_user']
                user_id = user.id
                # user_id = event.from_user.id if hasattr(event, "from_user") and event.from_user else "Unknown"
                event_type = event.__class__.__name__
                logging.info(f"Получено событие {event_type} от пользователя {user_id}") #:\n {pformat(event)}\n")

            club_id = data.get('club_id',None)
            member_id = await member_id_tg(user_id)

            if 'state' in data:
                 logging.info(f"Middleware detected FSM state before handler: {await data['state'].get_state()}\n")

            # Создаем ключ 'data', если его еще нет
            if 'data' not in data:
                data['data'] = {
                    'club_id':club_id,
                    'member_id':member_id

                    # Добавьте другие необходимые данные
                }
                logging.info(f'Создан словарь дата в мидлваре логирования {pformat(data["data"])}')



            response = await handler(event, data)

            # logging.info(f'Данные data после прохождения хэндлера: \n{pformat(data)}\n')
            if 'state' in data:
                 logging.info(f"\nMiddleware detected FSM state after handler: {await data['state'].get_state()}")
                 logging.info(f"Middleware detected FSM data after handler: {await data['state'].get_data()}\n")



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