# logging_middleware.py  # Middleware для логгирования и обработки исключений
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
import logging
import traceback
from pprint import pformat
from data_base.telegram_bot_logic import extract_user_member_id
from keyboards.keyboards import user_menu

class LoggingAndErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        # logging.info(f"Data in LoggingAndErrorHandlingMiddleware: {pformat(data)}\n")
        logging.info('\n Middleware logging_middleware started work\n')
        try:
            if isinstance(event, Update):
                user = data['event_from_user']
                tg_id = user.id
                # tg_id = event.from_user.id if hasattr(event, "from_user") and event.from_user else "Unknown"
                event_type = event.__class__.__name__
                logging.info(f"Получено событие {event_type} от пользователя {tg_id}") #:\n {pformat(event)}\n")

            club_id = data.get('club_id',None)
            user_id, member_id = await extract_user_member_id(tg_id)

            if 'state' in data:
                 logging.info(f"Middleware detected FSM state before handler: {await data['state'].get_state()}\n")

            # Создаем ключ 'data', если его еще нет
            if 'data' not in data:
                data['data'] = {
                    'club_id':club_id,
                    'user_id':user_id,
                    'member_id':member_id

                    # Добавьте другие необходимые данные
                }
                logging.info(f'Создан словарь дата в мидлваре логирования {pformat(data["data"])}')

            # Логируем callback_data или текст сообщения
            if hasattr(event, "message") and event.message:
                logging.info(f"\n\nПолучено текстовое сообщение: {event.message.text}")
            elif hasattr(event, "callback_query") and event.callback_query:
                logging.info(f"\n\nПолучен callback_query с данными: {event.callback_query.data}")
            else:
                logging.info(f"\n\nПолучено событие другого типа: {type(event)}")


            response = await handler(event, data)

            # logging.info(f'Данные data после прохождения хэндлера: \n{pformat(data)}\n')
            if 'state' in data:
                 logging.info(f"\nMiddleware detected FSM state after handler: {await data['state'].get_state()}")
                 logging.info(f"Middleware detected FSM data after handler: {await data['state'].get_data()}\n")



            return response


        except Exception as e:
            logging.error(f"Необработанное исключение в хэндлере: {e}\n{traceback.format_exc()}")
            try:
                user = data['event_from_user']
                tg_id = user.id
                marcup = await user_menu(tg_id)
            except:
                marcup = None

            if hasattr(event, "message") and event.message:
                await event.message.answer(
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
                    reply_markup=marcup
                )
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.message.answer(
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
                    reply_markup=marcup
                )