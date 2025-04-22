# 📜safe_edit_middleware.py  # Middleware для замены edit_text на answer в том случае,
# если сообщение, которое надо редактировать устарело (не подлежит редактированию) или не найдено
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest  # Обрати внимание на новый путь
import logging
from pprint import pformat

logger = logging.getLogger(__name__)

class SafeEditMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict):
        # logger.info(f"Data in SafeEditMiddleware: \n{pformat(data)}\n")
        logger.info('\nMiddleware SafeEditMiddleware начала работу\n')
        try:
            # Создаем ключ 'data', если его еще нет
            if 'data' not in data:
                data['data'] = {

                    # Добавьте другие необходимые данные
                }
                logger.info(f'Создан словарь дата в мидлваре исправления едит на ансвер')

            result = await handler(event, data)
            logger.info(f"Данные пользовательской data после прохождения хэндлера: {pformat(data['data'])}")
            return result
        except TelegramBadRequest as e:
            if "message is not modified" in str(e) or "message to edit not found" in str(e):
                if isinstance(event, CallbackQuery):
                    logger.warning("Переход на message.answer из-за ошибки при редактировании сообщения")
                    text = data.get('response_text', 'Произошла ошибка при обновлении сообщения')
                    reply_markup = data.get('reply_markup', None)
                    await event.message.answer(text=text, reply_markup=reply_markup)
                else:
                    logger.error("Необработанное событие при редактировании сообщения")
            else:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                raise