# 📜safe_edit_middleware.py  # Middleware для замены edit_text на answer в том случае,
# если сообщение, которое надо редактировать устарело (не подлежит редактированию) или не найдено
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest  # Обрати внимание на новый путь
import logging

class SafeEditMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data: dict):
        logging.info(f"Data in SafeEditMiddleware: {data}\n")
        try:
            # Создаем ключ 'data', если его еще нет
            if 'data' not in data:
                data['data'] = {

                    # Добавьте другие необходимые данные
                }
            logging.info(f'Создан словарь дата в мидлваре исправления едит на ансвер \n\n')

            result = await handler(event, data)
            print('Снова data:', data,'\n')
            return result
        except TelegramBadRequest as e:
            if "message is not modified" in str(e) or "message to edit not found" in str(e):
                if isinstance(event, CallbackQuery):
                    logging.warning("Переход на message.answer из-за ошибки при редактировании сообщения")
                    text = data.get('response_text', 'Произошла ошибка при обновлении сообщения')
                    reply_markup = data.get('reply_markup', None)
                    await event.message.answer(text=text, reply_markup=reply_markup)
                else:
                    logging.error("Необработанное событие при редактировании сообщения")
            else:
                logging.error(f"Ошибка при редактировании сообщения: {e}")
                raise