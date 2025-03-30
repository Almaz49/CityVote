# Модуль utils.py
# Это файл с функциями и декораторами, которые используются другими модулями

import logging  # Добавляем импорт модуля logging
from functools import wraps



# Настройка логирования
logging.basicConfig(level=logging.DEBUG)



# Это декоратор, который каждую функцию объявляет в логах. Вызов происходит @log_function_call
# def log_function_call(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         logging.debug(f"Вызвана функция {func.__name__} из модуля {func.__module__} ")
#         return func(*args, **kwargs)
#     return wrapper

def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_str = ', '.join([repr(a) for a in args])
        kwargs_str = ', '.join([f"{k}={repr(v)}" for k, v in kwargs.items()])

        logging.debug(
            f"Вызвана функция {func.__name__} из модуля {func.__module__}\n"
            f"Аргументы: ({args_str}) {{{kwargs_str}}}"
        )
        return func(*args, **kwargs)
    return wrapper


# Это декоратор, который каждый хэндлер объявляет в логах. Вызов происходит @log_function_call
# def log_handler_call(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         logging.info(f"Вызван хэндлер {func.__name__} из модуля {func.__module__} \n")
#         return func(*args, **kwargs)
#     return wrapper

def log_handler_call(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logging.info(f"Вызван хэндлер {func.__name__} из модуля {func.__module__}\n")
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Ошибка в хэндлере {func.__name__}: {e}")
            raise
    return wrapper