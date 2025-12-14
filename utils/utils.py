# Модуль utils.py
# Это файл с функциями и декораторами, которые используются другими модулями

import asyncio
import logging  # Добавляем импорт модуля logging
from functools import wraps
from typing import Any, Dict, List
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiosqlite import Cursor

# Настройка логирования
logger = logging.getLogger(__name__)




def log_function_call(func):
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        args_str = ", ".join([repr(a) for a in args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        logger.debug(
            f"\nВызвана функция {func.__name__} из модуля {func.__module__}\n"
            f"Аргументы: ({args_str}) {{{kwargs_str}}}"
        )
        return func(*args, **kwargs)

    async def async_wrapper(*args, **kwargs):
        args_str = ", ".join([repr(a) for a in args])
        kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        logger.debug(
            f"\nВызвана АСИНХРОННАЯ функция {func.__name__} из модуля {func.__module__}\n"
            f"Аргументы: ({args_str}) {{{kwargs_str}}}"
        )
        return await func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper




def log_handler_call(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"\n\nВызван хэндлер {func.__name__} из модуля {func.__module__}\n\n")
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в хэндлере {func.__name__}: {e}")
            raise

    return wrapper




def check_fsm_data(func):
    """
    Универсальный декоратор проверяет, есть ли FSM data и для Message и для Callback,
    если нет - отправляет сообщение, что сессия устарела
    """

    @wraps(func)
    async def wrapper(
        event: Message | CallbackQuery, state: FSMContext, *args, **kwargs,
    ):
        # Определяем, как получить объект сообщения
        if isinstance(event, Message):
            message = event
        elif isinstance(event, CallbackQuery):
            message = event.message
        else:
            logger.warning(f"Неизвестный тип события: {type(event)}")
            return await func(event, state, *args, **kwargs)

        # Проверяем наличие FSM-данных
        fsm_data = await state.get_data()
        if not fsm_data:
            await message.answer("Сессия устарела. Пожалуйста, начните заново.")  # type: ignore
            return

        return await func(event, state, *args, **kwargs)

    return wrapper


def check_fsm_data_callback(func):
    """
    Декоратор для Callback, проверяет, есть ли FSM data, если нет - отправляет сообщение, что сессия устарела
    """

    @wraps(func)
    async def wrapper(callback: CallbackQuery, state: FSMContext, *args, **kwargs):
        fsm_data = await state.get_data()
        if not fsm_data:
            await callback.message.answer("Сессия устарела. Пожалуйста, начните заново.")  # type: ignore
            return
        return await func(callback, state, *args, **kwargs)

    return wrapper


def check_fsm_data_message(func):
    """
    Декоратор для Message, проверяет, есть ли FSM data, если нет - отправляет сообщение, что сессия устарела
    """

    @wraps(func)
    async def wrapper(message: Message, state: FSMContext, *args, **kwargs):
        fsm_data = await state.get_data()
        if not fsm_data:
            await message.answer("Сессия устарела. Пожалуйста, начните заново.")
            return
        return await func(message, state, *args, **kwargs)

    return wrapper


async def fetch_as_dict(cursor: Cursor) -> List[Dict[str, Any]]:
    """
    Преобразует результат SQL-запроса в список словарей,
    где ключи — это названия столбцов, а значения — данные из строк.

    :param cursor: объект курсора после выполнения запроса
    :return: список словарей с данными
    """
    try:
        logger.debug("Начинаем обработку результата запроса через fetch_as_dict")

        # Проверяем, есть ли данные
        if cursor.description is None:
            logger.warning("Запрос не вернул данных. cursor.description == None")
            return []

        # Получаем названия столбцов
        columns = [column[0] for column in cursor.description]
        logger.debug(f"Получены столбцы: {columns}")

        # Получаем все строки
        rows = await cursor.fetchall()
        rows_list = list(rows)
        logger.debug(f"Получено {len(rows_list)} строк данных")

        # Формируем результат
        result = [dict(zip(columns, row)) for row in rows]
        logger.debug(f"Сформирован результат с {len(result)} записями")

        return result

    except Exception as e:
        logger.error(f"Ошибка при обработке результата запроса: {e}", exc_info=True)
        raise


# Пример использования:
#     async with AsyncDatabase(path_db) as cursor:
#         try:
#             await cursor.execute(query, params)
#             # Преобразуем результат в список словарей
#             result = await fetch_as_dict(cursor)
#             logger.info("Запрос успешно выполнен.")
#             return result
#         except aiosqlite.Error as e:
#             logger.error(f"Ошибка при выполнении запроса: {e}")
#             raise


# Функция для разделения списка на страницы
def paginate(items, page, items_per_page=10):
    start = (page - 1) * items_per_page
    end = start + items_per_page
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    return items[start:end], total_pages


async def safe_edit(callback: CallbackQuery, text: str, reply_markup=None, parse_mode=None):
    """
    Функция для замены edit_text на answer в том случае,
    если сообщение, которое надо редатировать устарело (не подлежит редатированию) или не найдено.
    В случае, если сообщение не изменилось, то ничего не отправляем
    """
    # 🔹 Проверяем, что сообщение существует
    if not callback.message:
        logger.warning("CallbackQuery не содержит сообщение — невозможно редактировать или ответить")
        return
    try:
        # 🔹 Проверяем, изменилось ли сообщение
        if (callback.message.text == text and  # type: ignore
            callback.message.reply_markup == reply_markup): # type: ignore
            # logger.debug("Сообщение не изменилось — пропускаем редактирование")
            return  # Просто выходим

        await callback.message.edit_text( # type: ignore
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Уже обработали выше, но на всякий случай
            return
        elif "message to edit not found" in str(e):
            # Сообщение устарело — отправляем новое
            await callback.message.answer(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            logger.error(f"Неизвестная ошибка при редактировании: {e}")
            raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании: {e}")
        await callback.message.answer(text=text, reply_markup=reply_markup, parse_mode=parse_mode)

def normalize_token(token: str) -> str:
    """
    Нормализует токен, удаляя пробелы и дефисы
    """
    return token.strip().replace(" ", "").replace("-", "")
