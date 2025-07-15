# Файл config.py

import os
from dataclasses import dataclass

from environs import Env


@dataclass
class DatabaseConfig:
    # database: str         # Название базы данных
    path_db: str  # URL-адрес базы данных
    # db_user: str          # Username пользователя базы данных
    # db_password: str      # Пароль к базе данных


@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту
    club_id: int  # id группы, которую администрирует бот (группа в БД, а не в телеграм)
    admin_ids: list  # Список id администраторов бота
    timezone: str  # Часовой пояс группы


@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig


def load_config(path: str|None = None, instance_name: str|None = None) -> Config:
    env = Env()
    if instance_name:
        config_path = f"configs/{instance_name}.env"
        if os.path.exists(config_path):
            env.read_env(config_path)
        else:
            raise FileNotFoundError(f"Конфиг {config_path} не найден")
    else:
        env.read_env(path or ".env")
    admin_ids_raw = env.list("ADMIN_IDS", default=[])
    if not admin_ids_raw:
        raise ValueError("Не указаны id администраторов")
    if admin_ids_raw and not admin_ids_raw[0].isdigit():  # Если в переменной ADMIN_IDS не только числа, то выкидываем ошибку
        raise ValueError("Некорректный формат переменной ADMIN_IDS")
    admin_ids = [int(x) for x in admin_ids_raw if x.strip()]

    return Config(
        tg_bot=TgBot(
            token=env("BOT_TOKEN"),
            club_id=int(env("CLUB_ID")),
            admin_ids=admin_ids,
            timezone=env("TIMEZONE", default="Asia/Novosibirsk"),
        ),
        db=DatabaseConfig(
            path_db=env("path_db")
        )
    )
