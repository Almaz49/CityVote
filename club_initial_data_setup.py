"""
файл club_initial_data_setup.py
запускается так:
python club_initial_data_setup.py bot01
вместо bot01 укажите имя соотвествующего файла конфигурации без расширения .env

Этот файл создаёт начальные настройки группы и владельцев.
Если группа уже существует — ничего не делает.
- Добавляет группу (club) в БД
- Регистрирует пользователей по их Telegram ID
- Создаёт участников (members)
- Назначает статусы 'owner' и 'member'
- Генерирует токены для владельцев
- Привязывает токены к владельцам
"""

import sys
import sqlite3
import asyncio
import logging
from typing import List, Optional
from config_data.config import load_config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if len(sys.argv) < 2:
    print("При запуске этого файла укажите имя экземпляра бота, например: python club_initial_data_setup.py bot01")
    sys.exit(1)

instance_name = sys.argv[1]
# Загрузка конфига
config = load_config(instance_name=instance_name)


path_db = config.db.path_db  # путь к базе данных
admin_ids: List[int] = config.tg_bot.admin_ids  # список tg_id админов бота
club_id: Optional[int] = config.tg_bot.club_id  # id группы в БД (не телеграм)

# Подключение к БД
from data_base.db_token_service import auto_approve_by_token, create_tokens_without_lot, is_valid_token


def ensure_club_exists(club_id: int, connection: sqlite3.Connection) -> bool:
    """Проверяет, существует ли группа с заданным ID."""
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM Clubs WHERE id = ?", (club_id,))
    return cursor.fetchone() is not None


def create_club(club_id: int, connection: sqlite3.Connection):
    """Создаёт группу, если её ещё нет."""
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO Clubs (id, name) VALUES (?, ?)",
            (club_id, f"Club {club_id}")
        )
        connection.commit()
        logger.info(f"Создана группа с id={club_id}")
    except Exception as e:
        logger.error(f"Ошибка при создании группы: {e}")
        raise


def register_admins(admin_ids: List[int], club_id: int, connection: sqlite3.Connection) -> List[int]:
    """
    Регистрирует админов как Users и Members.
    Возвращает список member_id админов.
    """
    cursor = connection.cursor()
    admin_member_ids = []

    for tg_id in admin_ids:
        try:
            # Добавляем пользователя, если ещё не добавлен
            cursor.execute("INSERT OR IGNORE INTO Users (tg_id) VALUES (?)", (tg_id,))
            connection.commit()

            # Получаем user_id
            cursor.execute("SELECT id FROM Users WHERE tg_id = ?", (tg_id,))
            result = cursor.fetchone()
            if not result:
                logger.error(f"Не удалось получить user_id для tg_id={tg_id}")
                continue
            user_id, = result

            # Добавляем пользователя в группу (Members)
            cursor.execute(
                "INSERT OR IGNORE INTO Members (user_id, club_id) VALUES (?, ?)",
                (user_id, club_id)
            )
            connection.commit()

            # Получаем member_id
            cursor.execute(
                "SELECT id FROM Members WHERE user_id = ? AND club_id = ?",
                (user_id, club_id)
            )
            result = cursor.fetchone()
            if not result:
                logger.error(f"Не удалось получить member_id для user_id={user_id}, club_id={club_id}")
                continue
            member_id, = result
            admin_member_ids.append(member_id)

            # Назначаем статусы
            cursor.execute(
                "INSERT OR IGNORE INTO Status (member_id, status) VALUES (?, ?)",
                (member_id, "owner")
            )
            cursor.execute(
                "INSERT OR IGNORE INTO Status (member_id, status) VALUES (?, ?)",
                (member_id, "member")
            )
            connection.commit()

            logger.info(f"Админ с tg_id={tg_id} зарегистрирован в группе {club_id} как owner")

        except Exception as e:
            logger.error(f"Ошибка при регистрации админа tg_id={tg_id}: {e}")
            continue

    return admin_member_ids


async def setup_admin_tokens(club_id: int, admin_member_ids: List[int]):
    """Создаёт токены для владельцев и привязывает их."""
    for member_id in admin_member_ids:
        try:
            tokens = await create_tokens_without_lot(
                club_id=club_id,
                comment="Token for owner",
                count=1,
                time_of_action_months=1200,
                creator_id=member_id
            )
            if not tokens:
                logger.warning(f"Не удалось создать токен для member_id={member_id}")
                continue

            token = tokens[0]
            logger.info(f"Создан токен '{token}' для member_id={member_id}")

            token_info = await is_valid_token(token, club_id)
            if not token_info:
                logger.warning(f"Токен '{token}' недействителен для группы {club_id}")
                continue

            token_id = token_info.get('token_id')
            if not token_id:
                logger.warning(f"Неверные данные токена: {token_info}")
                continue

            success, message = await auto_approve_by_token(member_id, token_id)
            if not success:
                logger.warning(f"Не удалось привязать токен к админу: {message}")
            else:
                logger.info(f"Токен успешно привязан к админу {member_id}")

        except Exception as e:
            logger.error(f"Ошибка при работе с токеном для member_id={member_id}: {e}")


async def main():
    if not club_id:
        logger.error("club_id не задан в .env")
        return

    try:
        with sqlite3.connect(path_db) as conn:
            if ensure_club_exists(club_id, conn):
                logger.info(f"Группа с id={club_id} уже существует. Инициализация остановлена.")
                return

            create_club(club_id, conn)
            admin_member_ids = register_admins(admin_ids, club_id, conn)

        if not admin_member_ids:
            logger.warning("Не найдены или не зарегистрированы администраторы")
            return

        await setup_admin_tokens(club_id, admin_member_ids)

    except Exception as e:
        logger.error(f"Критическая ошибка при инициализации: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Скрипт остановлен вручную")