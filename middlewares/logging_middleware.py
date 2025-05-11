# logging_middleware.py  # Middleware для логгирования и обработки исключений

import logging
import traceback
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from pprint import pformat
from data_base.telegram_bot_logic import extract_user_member_id
from keyboards.keyboards import user_menu

logger = logging.getLogger(__name__)

class LoggingAndErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        logger.info('\n Middleware logging_middleware started work\n')
        try:
            # Логируем тип события и пользователя
            if isinstance(event, Update):
                user = data.get('event_from_user')
                tg_id = user.id if user else "Unknown"
                event_type = event.__class__.__name__
                logger.info(f"Получено событие {event_type} от пользователя {tg_id}")

            # Извлекаем club_id, user_id и member_id
            club_id = data.get('club_id', None)
            user_id, member_id = await extract_user_member_id(tg_id)

            # Логируем состояние FSM перед обработкой
            if 'state' in data:
                logger.info(f"Middleware detected FSM state before handler: {await data['state'].get_state()}")

            # Создаем ключ 'data', если его еще нет
            if 'data' not in data:
                data['data'] = {
                    'club_id': club_id,
                    'user_id': user_id,
                    'member_id': member_id
                }
                logger.info(f'Создан словарь дата в мидлваре логирования {pformat(data["data"])}')

            # Логируем текст сообщения или callback_data
            if hasattr(event, "message") and event.message:
                logger.info(f"\n\nПолучено текстовое сообщение: {event.message.text}")
            elif hasattr(event, "callback_query") and event.callback_query:
                logger.info(f"\n\nПолучен callback_query с данными: {event.callback_query.data}")
            else:
                logger.info(f"\n\nПолучено событие другого типа: {type(event)}")

            # Передаем управление следующему middleware или хэндлеру
            response = await handler(event, data)

            # Логируем состояние FSM после обработки
            if 'state' in data:
                logger.info(f"\nMiddleware detected FSM state after handler: {await data['state'].get_state()}")
                logger.info(f"Middleware detected FSM data after handler: {await data['state'].get_data()}")

            return response

        except Exception as e:
            # Логируем полную трассировку ошибки
            tb = traceback.format_exc()
            logger.error(f"Необработанное исключение в хэндлере: {e}\n{tb}")

            # Добавляем информацию о месте возникновения ошибки
            error_info = traceback.extract_tb(e.__traceback__)
            for frame in error_info:
                logger.error(
                    f"Ошибка произошла в файле: {frame.filename}, строка: {frame.lineno}, "
                    f"функция: {frame.name}, код: {frame.line}"
                )

            # Попытка определить пользователя для отправки сообщения об ошибке
            try:
                user = data.get('event_from_user')
                tg_id = user.id if user else "Unknown"
                markup = await user_menu(tg_id)
            except:
                markup = None

            # Отправляем сообщение пользователю о возникшей ошибке
            if hasattr(event, "message") and event.message:
                await event.message.answer(
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
                    reply_markup=markup
                )
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.message.answer(
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
                    reply_markup=markup
                )



# from aiogram import BaseMiddleware
# from aiogram.types import Update, Message, CallbackQuery
# import logging
# import traceback
# from pprint import pformat
# from data_base.telegram_bot_logic import extract_user_member_id
# from keyboards.keyboards import user_menu

# logger = logging.getLogger(__name__)

# class LoggingAndErrorHandlingMiddleware(BaseMiddleware):
#     async def __call__(self, handler, event: Update, data: dict):
#         # logger.info(f"Data in LoggingAndErrorHandlingMiddleware: {pformat(data)}\n")
#         logger.info('\n Middleware logging_middleware started work\n')
#         try:
#             if isinstance(event, Update):
#                 user = data['event_from_user']
#                 tg_id = user.id
#                 # tg_id = event.from_user.id if hasattr(event, "from_user") and event.from_user else "Unknown"
#                 event_type = event.__class__.__name__
#                 logger.info(f"Получено событие {event_type} от пользователя {tg_id}") #:\n {pformat(event)}\n")

#             club_id = data.get('club_id',None)
#             user_id, member_id = await extract_user_member_id(tg_id)

#             if 'state' in data:
#                  logger.info(f"Middleware detected FSM state before handler: {await data['state'].get_state()}\n")

#             # Создаем ключ 'data', если его еще нет
#             if 'data' not in data:
#                 data['data'] = {
#                     'club_id':club_id,
#                     'user_id':user_id,
#                     'member_id':member_id

#                     # Добавьте другие необходимые данные
#                 }
#                 logger.info(f'Создан словарь дата в мидлваре логирования {pformat(data["data"])}')

#             # Логируем callback_data или текст сообщения
#             if hasattr(event, "message") and event.message:
#                 logger.info(f"\n\nПолучено текстовое сообщение: {event.message.text}")
#             elif hasattr(event, "callback_query") and event.callback_query:
#                 logger.info(f"\n\nПолучен callback_query с данными: {event.callback_query.data}")
#             else:
#                 logger.info(f"\n\nПолучено событие другого типа: {type(event)}")


#             response = await handler(event, data)

#             # logger.info(f'Данные data после прохождения хэндлера: \n{pformat(data)}\n')
#             if 'state' in data:
#                  logger.info(f"\nMiddleware detected FSM state after handler: {await data['state'].get_state()}")
#                  logger.info(f"Middleware detected FSM data after handler: {await data['state'].get_data()}\n")



#             return response


#         except Exception as e:
#             logger.error(f"Необработанное исключение в хэндлере: {e}\n{traceback.format_exc()}")
#             try:
#                 user = data['event_from_user']
#                 tg_id = user.id
#                 markup = await user_menu(tg_id)
#             except:
#                 markup = None

#             if hasattr(event, "message") and event.message:
#                 await event.message.answer(
#                     text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
#                     reply_markup=markup
#                 )
#             elif hasattr(event, "callback_query") and event.callback_query:
#                 await event.callback_query.message.answer(
#                     text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
#                     reply_markup=markup
#                 )