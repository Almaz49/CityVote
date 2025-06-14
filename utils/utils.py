# Модуль utils.py
# Это файл с функциями и декораторами, которые используются другими модулями

import asyncio
import logging  # Добавляем импорт модуля logging
from functools import wraps
from typing import Any, Dict, List
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiosqlite import Cursor





# Настройка логирования
logger = logging.getLogger(__name__)



# Это декоратор, который каждую функцию объявляет в логах. Вызов происходит @log_function_call
# def log_function_call(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         logger.debug(f"Вызвана функция {func.__name__} из модуля {func.__module__} ")
#         return func(*args, **kwargs)
#     return wrapper

def log_function_call(func):
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        args_str = ', '.join([repr(a) for a in args])
        kwargs_str = ', '.join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        logger.info(
            f"Вызвана функция {func.__name__} из модуля {func.__module__}\n"
            f"Аргументы: ({args_str}) {{{kwargs_str}}}"
        )
        return func(*args, **kwargs)

    async def async_wrapper(*args, **kwargs):
        args_str = ', '.join([repr(a) for a in args])
        kwargs_str = ', '.join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        logger.info(
            f"Вызвана АСИНХРОННАЯ функция {func.__name__} из модуля {func.__module__}\n"
            f"Аргументы: ({args_str}) {{{kwargs_str}}}"
        )
        return await func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Это декоратор, который каждый хэндлер объявляет в логах. Вызов происходит @log_function_call
# def log_handler_call(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         logger.info(f"Вызван хэндлер {func.__name__} из модуля {func.__module__} \n")
#         return func(*args, **kwargs)
#     return wrapper

def log_handler_call(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"Вызван хэндлер {func.__name__} из модуля {func.__module__}\n")
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в хэндлере {func.__name__}: {e}")
            raise
    return wrapper

# Декоратор, который проверяет наличие FSM data. При ее отсуствии отправляет сообщение, что сессия устарела.
# Пример использования:
# @router.callback_query(F.data == "ConfirmOK")
# @check_fsm_data
# async def process_new_voting_yes_confirm_press(callback: CallbackQuery, state: FSMContext):
#     fsm_data = await state.get_data()
#     title = fsm_data['title']
#     description = fsm_data['description']
#     # ... остальная логика ...

def check_fsm_data(func):
    """
    Универсальный декоратор проверяет, есть ли FSM data и для Message и для Callback,
    если нет - отправляет сообщение, что сессия устарела
    """
    @wraps(func)
    async def wrapper(event: Message | CallbackQuery, state: FSMContext, *args, **kwargs):
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
            await message.answer("Сессия устарела. Пожалуйста, начните заново.") # type: ignore
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
            await callback.message.answer("Сессия устарела. Пожалуйста, начните заново.") # type: ignore
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