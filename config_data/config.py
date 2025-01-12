from dataclasses import dataclass
from environs import Env
import sqlite3

@dataclass
class DatabaseConfig:
    #database: str         # Название базы данных
    path_db: str          # URL-адрес базы данных
    #db_user: str          # Username пользователя базы данных
    #db_password: str      # Пароль к базе данных
    

@dataclass
class TgBot:
    token: str            # Токен для доступа к телеграм-боту
    club_id: int # id группы, которую администрирует бот (групп в БД, а не в телеграм)
    admin_ids: list  # Список id администраторов бота
    


@dataclass
class Config:
    tg_bot: TgBot
    db: DatabaseConfig



def load_config(path: str) -> Config:
    env = Env()
    env.read_env(path)
    path_db=env('path_db')
    club_name=env('CLUB_NAME')
    with sqlite3.connect(path_db) as connection:
        cursor = connection.cursor()
        cursor.execute('INSERT OR IGNORE INTO Clubs(name) VALUES(?)', (club_name,)) # Добавляем группу в список групп, если ее там еще нет
        cursor.execute('SELECT id FROM Clubs WHERE name = ?', (club_name,)) #Извлекаем id группы
        club_id, = cursor.fetchone()
        club_id = int(club_id)
    return Config(
        tg_bot=TgBot(
        token=env('BOT_TOKEN'),
        club_id = club_id,
        admin_ids=list(map(int, env.list('ADMIN_IDS'))),
         ),
        db=DatabaseConfig(path_db)
        )

"""
Потом надо будет сделать отдельный скрипт под создание новой группы, который будет создавать уникальное название
и записывать в .env сразу id группы, id админов и название тг-бота.
Чтобы не назначить ненароком адмминов в старую группу
"""
