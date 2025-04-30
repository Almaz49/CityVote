# Модуль utils.py
# Это файл с функциями и декораторами, которые используются другими модулями

import logging  # Добавляем импорт модуля logging
from functools import wraps
from LEXICON.LEXICON import LEXICON



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
    def wrapper(*args, **kwargs):
        args_str = ', '.join([repr(a) for a in args])
        kwargs_str = ', '.join([f"{k}={repr(v)}" for k, v in kwargs.items()])

        logger.debug(
            f"Вызвана функция {func.__name__} из модуля {func.__module__}\n"
            f"Аргументы: ({args_str}) {{{kwargs_str}}}"
        )
        return func(*args, **kwargs)
    return wrapper


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

# def help_message(status_list:list):
#     status = set(status_list) - set(['votist'])
#     text = ''
#     for item in status:
#         text += LEXICON.get(item+'_help', f'Для статуса {item} нет справки\n\n')
#     logger.debug(f'Сформирована справка:\n{text}')
#     return text

def help_message(status_list: list):
    status = set(status_list) - {'votist'}  # Исключаем статус 'votist'
    text = "<b>Справка по вашим ролям:</b>\n\n"  # Заголовок

    for item in sorted(status):  # Сортируем роли для удобства
        role_help = LEXICON.get(item + '_help', f'Для статуса {item} пока нет справки.')
        text += f"📌 <b>{LEXICON.get(item, item.capitalize())}:</b>\n{role_help}\n\n"

    logger.debug(f'Сформирована справка:\n{text}')
    return text

def greetings_message(channel_link=None, club_name: str = None):
    description = f"<b>👋 Привет! Я — бот для голосований группы {club_name}.</b>" + LEXICON.get('greetings','Это бот для голсоований')
    if channel_link:
        description = description + f"<a href='{channel_link}'>[Подпишитесь на наш канал, чтобы быть в курсе всех событий:]</a>"
    return description