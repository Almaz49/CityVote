# Файл config.py

import logging
import os
from dataclasses import dataclass

from environs import Env

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    # database: str         # Название базы данных
    path_db: str  # URL-адрес базы данных
    # db_user: str          # Username пользователя базы данных
    # db_password: str      # Пароль к базе данных


@dataclass
class TgBot:
    token: str|None  # Токен для доступа к телеграм-боту
    club_id: int|None  # id группы, которую администрирует бот (группа в БД, а не в телеграм)
    admin_ids: list  # Список id администраторов бота
    timezone: str  # Часовой пояс группы
    language: str  # Язык


@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig


def load_config(path: str | None = None, instance_name: str | None = None) -> Config:
    env = Env()

    # Загружаем основной .env файл
    if instance_name:
        config_path = f"configs/{instance_name}.env"
        if os.path.exists(config_path):
            env.read_env(config_path)
        else:
            raise FileNotFoundError(f"Конфиг {config_path} не найден")
    else:
        env.read_env(path or ".env")

    # Читаем обязательные поля
    db_path = env("path_db")
    timezone = env("TIMEZONE", default="Asia/Novosibirsk")

    # Читаем опциональные поля
    token = env("BOT_TOKEN", None)
    club_id_str = env("CLUB_ID", None)
    language = env("LANGUAGE", default="en")
    admin_ids_raw = env.list("ADMIN_IDS", default=[])

    # Парсим CLUB_ID
    club_id = None
    if club_id_str and club_id_str.isdigit():
        club_id = int(club_id_str)
    elif club_id_str:
        logger.warning(f"CLUB_ID должен быть числом, получено: {club_id_str}")

    # Парсим ADMIN_IDS
    admin_ids = []
    invalid_found = False
    for idx, item in enumerate(admin_ids_raw): # type: ignore
        item = item.strip()
        if not item.isdigit():
            logger.warning(f"Элемент #{idx} в ADMIN_IDS не является числом: {item}")
            invalid_found = True
        else:
            admin_ids.append(int(item))
    if invalid_found:
        logger.warning("Некоторые значения в ADMIN_IDS были проигнорированы из-за некорректного формата")

    return Config(
        tg_bot=TgBot(
            token=token,
            club_id=club_id,
            language=language,
            admin_ids=admin_ids,
            timezone=timezone
        ),
        db=DatabaseConfig(path_db=db_path)
    )