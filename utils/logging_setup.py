# logging_setup.py

import logging

def setup_logger(
    debug_log_path='debug.log',
    info_log_path='info.log',
    warning_log_path='warning.log',
    error_log_path='error.log',
    console_level=logging.DEBUG,
    file_encoding='utf-8'
):
    """
    Настраивает логгирование с настраиваемыми параметрами.
    :param info_log_path: Путь к файлу для INFO и выше
    :param warning_log_path: Путь к файлу для WARNING и выше
    :param console_level: Уровень логирования для консоли
    :param file_encoding: Кодировка файлов
    :return: logger объект
    """
    # Настройка корневого логгера
    root_logger = logging.getLogger()  # Корневой логгер
    root_logger.setLevel(logging.DEBUG)

    # Handler для записи DEBUG и выше в файл debug.log
    debug_handler = logging.FileHandler(debug_log_path, encoding=file_encoding)
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Handler для записи INFO и выше в файл info.log
    info_handler = logging.FileHandler(info_log_path, encoding=file_encoding)
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Handler для записи WARNING и выше в файл warning.log
    warning_handler = logging.FileHandler(warning_log_path, encoding=file_encoding)
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Handler для записи ERRROR и выше в файл error.log
    error_handler = logging.FileHandler(error_log_path, encoding=file_encoding)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Handler для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Добавляем handlers к корневому логгеру
    # При желании отключить тот или иной хэндлер логирования - заккоментить соответсвующую строку
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(info_handler)
    root_logger.addHandler(warning_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    return root_logger