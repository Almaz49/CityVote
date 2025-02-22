# Модуль utils.py
# Это файл с функциями и декораторами, которые используются другими модулями

import logging  # Добавляем импорт модуля logging
from functools import wraps



# Настройка логирования
logging.basicConfig(level=logging.INFO)



# Это декоратор, который каждую функцию объявляет в логах. Вызов происходит @log_function_call
def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Вызвана функция {func.__name__} из модуля {func.__module__} ")
        return func(*args, **kwargs)
    return wrapper

# Это декоратор, который каждый хэндлер объявляет в логах. Вызов происходит @log_function_call
def log_handler_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Вызван хэндлер {func.__name__} из модуля {func.__module__} \n")
        return func(*args, **kwargs)
    return wrapper
