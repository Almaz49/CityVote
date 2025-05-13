# logging_setup.py

import logging

def setup_logger(
    debug_log_path = 'debug.log',
    info_log_path='info.log',
    warning_log_path='warning.log',
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
    # Создаем logger
    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.DEBUG)

    # Handler для записи DEBUG и выше в файл debug.log
    info_handler = logging.FileHandler(debug_log_path, encoding=file_encoding)
    info_handler.setLevel(logging.DEBUG)
    info_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Handler для записи INFO и выше в файл info.log
    info_handler = logging.FileHandler(info_log_path, encoding=file_encoding)
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Handler для записи WARNING и выше в файл warning.log
    warning_handler = logging.FileHandler(warning_log_path, encoding=file_encoding)
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Handler для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'))

    # Добавляем handlers к logger
    logger.addHandler(info_handler)
    logger.addHandler(warning_handler)
    logger.addHandler(console_handler)

    return logger