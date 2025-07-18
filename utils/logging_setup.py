# logging_setup.py
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
def setup_logger(
    debug_log_path="logs/debug.log",
    info_log_path="logs/info.log",
    warning_log_path="logs/warning.log",
    error_log_path="logs/error.log",
    console_level=logging.DEBUG,
    file_encoding="utf-8",
):
    """
    Настраивает логгирование с настраиваемыми параметрами.
    :param info_log_path: Путь к файлу для INFO и выше
    :param warning_log_path: Путь к файлу для WARNING и выше
    :param console_level: Уровень логирования для консоли
    :param file_encoding: Кодировка файлов
    :return: logger объект
    """
    # Убедись, что папка logs существует
    log_dir = os.path.dirname(info_log_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Настройка корневого логгера
    root_logger = logging.getLogger()  # Корневой логгер
    root_logger.setLevel(logging.DEBUG)

        # Удаляем старые хэндлеры
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)

    # Handler для записи DEBUG и выше в файл debug.log
    debug_handler = RotatingFileHandler(
        debug_log_path,
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=5,
        encoding=file_encoding
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s"
        )
    )

    # Handler для INFO
    info_handler = RotatingFileHandler(
        info_log_path,
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=5,
        encoding=file_encoding
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))


    # Handler для WARNING
    warning_handler = RotatingFileHandler(
        warning_log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding=file_encoding
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))


    # Handler для ERROR
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding=file_encoding
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))


    # Вывод в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))


    # Добавляем handlers к корневому логгеру
    # При желании отключить тот или иной хэндлер логирования - заккоментить соответсвующую строку
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(info_handler)
    root_logger.addHandler(warning_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    return root_logger

def cleanup_old_logs(logs_dir: str, days_to_keep: int = 7):
    """
    Удаляет лог-файлы старше N дней
    """
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        logger.warning(f"Папка с логами не найдена: {logs_dir}")
        return

    cutoff_time = datetime.now() - timedelta(days=days_to_keep)

    for log_file in logs_path.iterdir():
        if log_file.is_file() and log_file.suffix in [".log", ".log.1", ".log.gz"]:
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                try:
                    log_file.unlink()
                    logger.info(f"Удалён устаревший лог: {log_file.name}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении {log_file.name}: {e}")