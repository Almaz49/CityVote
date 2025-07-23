# logging_middleware.py  # Middleware для логгирования и обработки исключений

import logging
import traceback
from pprint import pformat

from aiogram import BaseMiddleware
from aiogram.types import Update

from data_base.db_func import extract_user_member_id
from keyboards.keyboards import return_to_main_menu_markup

logger = logging.getLogger(__name__)


class LoggingAndErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        logger.info("\n\n Начинаем работу с апдейтом. Middleware logging_middleware started work\n\n")
        try:
            # Логируем тип события и пользователя
            if isinstance(event, Update):
                user = data.get("event_from_user")
                tg_id = user.id if user else "Unknown"
                event_type = event.__class__.__name__
                logger.info(f"Получено событие {event_type} от пользователя {tg_id}")

            # Извлекаем instance_name из data
            instance_name = data.get("instance_name", None)
            if not instance_name:
                logger.warning(
                    "instance_name не определён. Не передано название бота."
                )
                return



            # Извлекаем club_id, user_id и member_id только если tg_id — целое число
            club_id = data.get("club_id", None)
            if not club_id:  # type: ignore
                logger.warning(
                    "club_id не определён. Пропущено извлечние user_id и member_id."
                )
                return
            if isinstance(tg_id, int):
                user_id, member_id = await extract_user_member_id(club_id, tg_id)
            else:
                user_id, member_id = None, None
                logger.warning(
                    "tg_id не определён или неверного типа. Пропущено извлечение user_id и member_id."
                )

            # Логируем состояние FSM перед обработкой
            if "state" in data:
                logger.info(
                    f"Middleware detected FSM state before handler: {await data['state'].get_state()}"
                )

            # Создаем ключ 'data', если его еще нет
            if "data" not in data:
                data["data"] = {
                    "club_id": club_id,
                    "user_id": user_id,
                    "member_id": member_id,
                    "instance_name": instance_name,
                }
                logger.info(
                    f'Создан словарь дата в мидлваре логирования {pformat(data["data"])}'
                )

            # Логируем текст сообщения или callback_data
            if hasattr(event, "message") and event.message:
                logger.info(f"\n\nПолучено текстовое сообщение: {event.message.text}\n\n")
            elif hasattr(event, "callback_query") and event.callback_query:
                logger.info(
                    f"\n\nПолучен callback_query с данными: {event.callback_query.data}\n\n"
                )
            else:
                logger.info(f"\n\nПолучено событие другого типа: {type(event)}")

            # Передаем управление следующему middleware или хэндлеру
            response = await handler(event, data)

            # Логируем состояние FSM после обработки
            if "state" in data:
                logger.info(
                    f"\nMiddleware detected FSM state after handler: {await data['state'].get_state()}"
                )
                logger.info(
                    f"Middleware detected FSM data after handler: {await data['state'].get_data()}"
                )

            return response

        except Exception as e:
            # Логируем полную трассировку ошибки
            tb = traceback.format_exc()
            user = data.get("event_from_user")
            tg_id = user.id if user else "Unknown"
            event_type = event.__class__.__name__

            logger.error(
                f"Необработанное исключение в хэндлере: {e}\n"
                f"Тип события: {event_type}\n"
                f"Пользователь: {tg_id}\n"
                f"Traceback:\n{tb}"
            )

            # Отправляем сообщение пользователю о возникшей ошибке
            # Only call user_menu if tg_id is an integer
            if isinstance(tg_id, int):
                try:
                    markup = return_to_main_menu_markup
                except Exception as menu_error:
                    logger.error(
                        f"Failed to generate user menu for tg_id {tg_id}: {menu_error}"
                    )
                    markup = None
            else:
                logger.warning(
                    f"Skipping user_menu generation: tg_id is '{tg_id}' (not an integer)."
                )
                markup = None

            if hasattr(event, "message") and event.message:
                await event.message.answer(
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
                    reply_markup=markup,
                )
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.message.answer(  # type: ignore
                    text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
                    reply_markup=markup,
                )
