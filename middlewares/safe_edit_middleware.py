# 📜safe_edit_middleware.py  # Middleware для замены edit_text на answer в том случае,
# если сообщение, которое надо редактировать устарело (не подлежит редактированию) или не найдено
import logging
from pprint import pformat

from aiogram import BaseMiddleware
from aiogram.exceptions import \
    TelegramBadRequest  # Обрати внимание на новый путь
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


class SafeEditMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict):
        # logger.info(f"Data in SafeEditMiddleware: \n{pformat(data)}\n")
        logger.info("\nMiddleware SafeEditMiddleware начала работу\n")
        try:
            # Создаем ключ 'data', если его еще нет
            if "data" not in data:
                data["data"] = {
                    # Добавьте другие необходимые данные
                }
                logger.info(
                    f"Создан словарь дата в мидлваре исправления едит на ансвер"
                )

            result = await handler(event, data)
            logger.info(
                f"Данные пользовательской data после прохождения хэндлера: {pformat(data['data'])}"
            )
            return result
        except TelegramBadRequest as e:
            if "message to edit not found" in str(e):
                if isinstance(event, CallbackQuery):
                    logger.warning("Сообщение для редактирования не найдено — возможно, устарело")
                    text = data.get(
                        "response_text", "Произошла ошибка при обновлении сообщения"
                    )
                    reply_markup = data.get("reply_markup", None)
                    await event.message.answer(text=text, reply_markup=reply_markup)  # type: ignore
                else:
                    logger.error("Необработанное событие при редактировании сообщения")
            elif "message is not modified" in str(e):
                # Это нормально, можно просто проигнорировать
                logger.debug("Пропущено редактирование — сообщение не изменилось")
                return None
            else:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                raise
            return None  # Прекращаем дальнейшую обработку


class SafeCallbackMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, CallbackQuery):
            try:
                return await handler(event, data)
            except TelegramBadRequest as e:
                if "query is too old" in str(e):
                    logger.info("Игнорируем устаревший callback от %s", event.from_user.id)
                    return None
                else:
                    raise
        else:
            return await handler(event, data)