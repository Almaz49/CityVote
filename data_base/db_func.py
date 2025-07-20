# Модуль db_func.py
# Это файл с функциями, которые используются другими файлами, работающими
# с базой данных
# This is a file with functions that are used by other files that work with
# the database.
import datetime
import logging  # Добавляем импорт модуля logging
from typing import Dict, List, Optional

import aiosqlite

from config_data.config import Config, load_config
from utils import fetch_as_dict, log_function_call

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config(".env")
path_db = config.db.path_db  # путь к базе данных


# Асинхронный контекстный менеджер для работы с базой данных
class AsyncDatabase:
    def __init__(self, db_name):
        self.db_name = db_name

    async def __aenter__(self):
        try:
            self.conn = await aiosqlite.connect(self.db_name)
            self.cursor = await self.conn.cursor()
            logger.debug(
                f"Асинхронное соединение с базой данных {self.db_name} установлено."
            )
            return self.cursor
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при установке асинхронного соединения с базой данных: {e}"
            )
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                await self.conn.commit()  # Если ошибок нет, подтвержаем изменения
                logger.debug("Асинхронные изменения подтверждены.")
            except aiosqlite.Error as e:
                logger.error(f"Ошибка при подтверждении асинхронных изменений: {e}")
                await self.conn.rollback()
        else:
            await self.conn.rollback()  # В случае ошибки откатываем изменения
            logger.error(f"Произошла асинхронная ошибка: {exc_val}")

        try:
            await self.conn.close()  # Закрываем соединение
            logger.debug("Асинхронное соединение с базой данных закрыто.")
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при закрытии асинхронного соединения: {e}")


# Функция редактирования полей в таблице table в строке где столбец key равен value.
# В поля вставляются значения словаря **cv,
# где ключ - имя столбца, а значение - значение поля
@log_function_call
async def db_update(table, key, value, **cv):
    params = list(cv.values()) + [value]
    columns = ", ".join([f"{k} = ?" for k in cv.keys()])
    qwery = f"UPDATE {table} SET {columns} WHERE {key} = ?"

    logger.info(f"Выполняется запрос: {qwery}")
    logger.info(f"Данные для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(qwery, params)
            logger.info("Запрос успешно выполнен.")
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise


@log_function_call
async def extract_user_id(tg_id):
    """
    Извлекает ID пользователя по его Telegram ID.
    :param tg_id: Telegram ID пользователя.
    :return: ID пользователя в базе данных или None, если пользователь не найден.
    """
    logger.info(f"Извлечение user_id для tg_id={tg_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                SELECT id FROM Users WHERE tg_id = ?
                """,
                (tg_id,),
            )
            result = await cursor.fetchone()
            if result:
                (user_id,) = result
                logger.info(f"Найден user_id={user_id} для tg_id={tg_id}")
                return user_id
            else:
                logger.info(f"Пользователь с tg_id={tg_id} не найден.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при извлечении user_id для tg_id={tg_id}: {e}")
            raise


@log_function_call
async def get_club_info(club_id):
    """
    Извлекает информацию о группе по её ID.
    :param club_id: ID группы.
    :return: Информация группы в базе данных или None, если имя не найдено.
    """
    logger.info(f"Извлечение информации о группе для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                SELECT *
                FROM Clubs WHERE id = ?
                """,
                (club_id,),
            )
            result = await fetch_as_dict(cursor)
            if result:
                logger.info(f"Найдена информация {result[0]} для club_id={club_id}")
                return result[0]
            else:
                logger.info(f"Информация о группе club_id={club_id} не найдено.")
                return None
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при извлечении информации о группе club_id={club_id}: {e}"
            )
            raise


@log_function_call
async def extract_member_id(club_id, user_id):
    """
    Извлекает ID участника группы по ID группы и ID пользователя.
    :param club_id: ID группы.
    :param user_id: ID пользователя.
    :return: ID участника группы в базе данных или None, если участник не найден.
    """
    logger.info(f"Извлечение member_id для club_id={club_id}, user_id={user_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                SELECT id FROM Members
                WHERE club_id = ? AND user_id = ?
                """,
                (club_id, user_id),
            )
            result = await cursor.fetchone()
            if result:
                (member_id,) = result
                logger.info(
                    f"Найден member_id={member_id} для club_id={club_id}, user_id={user_id}"
                )
                return member_id
            else:
                logger.info(
                    f"Участник с club_id={club_id}, user_id={user_id} не найден."
                )
                return None
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при извлечении member_id для club_id={club_id}, user_id={user_id}: {e}"
            )
            raise

# Функция извлечения user_id и member_id по tg_id
@log_function_call
async def extract_user_member_id(club_id:int, tg_id: int):  # Добавляем club_id как параметр
    try:
        user_id = await extract_user_id(tg_id)
        if user_id:
            member_id = await extract_member_id(club_id, user_id)
            logger.info(f"Извлечен member_id={member_id} для tg_id={tg_id}")
            return user_id, member_id
        else:
            logger.info(f"Пользователь с tg_id={tg_id} не найден.")
            return None, None
    except Exception as e:
        logger.error(f"Ошибка при извлечении member_id: {e}")
        return None, None

# Функция извлечения информации об участниках группы.
# Опционально можно указать статус участников, информация о которых требуется.
@log_function_call
async def list_of_members(club_id, status: str | list[str] = "all"):
    if isinstance(status, str):
        if status != "all":
            status = [status]
    elif isinstance(status, list):
        pass
    else:
        raise ValueError("Параметр status должен быть строкой или списком строк")
    # Получаем список участников с дополнительным полем info_level из таблицы Members
    query = """
    SELECT
        Users.first_name,
        Users.last_name,
        Users.tg_id AS tg_id,
        Users.tg_first_name,
        Users.tg_last_name,
        Users.username,
        Users.id AS user_id,
        Members.id AS member_id,
        Members.info_level,
        Tokens.token
    FROM Members
    INNER JOIN Users ON Users.id = Members.user_id
    LEFT JOIN Tokens ON Tokens.id = Members.token
    WHERE Members.club_id = ?
    """
    params = (club_id,)
    # Подзапрос проверяет, есть ли у участника указанный статус в таблице Status
    if status != "all":
        placeholders = ", ".join("?" for _ in status)
        query += f"""
        AND Members.id IN (
            SELECT member_id
            FROM Status
            WHERE status IN ({placeholders})
        )
        """
        params += tuple(status)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            result = await fetch_as_dict(cursor)
            logger.info("Запрос успешно выполнен.")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise


@log_function_call
async def list_of_proxy(club_id: int):
    """
    Возвращает список представителей (участников со статусом 'proxy') с их username и числом доверенных голосов,
    отсортированных по убыванию числа доверенных голосов.
    """
    if not club_id:
        raise ValueError("club_id не может быть пустым")

    async with AsyncDatabase(path_db) as cursor:
        try:
            logger.info(f"Запрос списка представителей для club_id={club_id}")
            await cursor.execute(
                """
                SELECT u.username, m.id AS member_id, m.description, COUNT(p.proxy) AS trusted_votes
                FROM Members m
                INNER JOIN Users u ON m.user_id = u.id
                LEFT JOIN Members p ON m.id = p.proxy
                INNER JOIN Status s ON m.id = s.member_id
                WHERE m.club_id = ? AND s.status = 'proxy'
                GROUP BY m.id
                ORDER BY trusted_votes DESC
            """,
                (club_id,),
            )
            proxies = await fetch_as_dict(cursor)
            return proxies
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при получении списка представителей: {e}")
            raise


@log_function_call
async def get_profile(member_id: int):
    """
    Возвращает информацию профиля участника по его member_id.
    :param member_id: ID участника в таблице Members
    """
    if not member_id:
        raise ValueError("member_id не может быть пустым")

    async with AsyncDatabase(path_db) as cursor:
        try:
            logger.info(f"Запрос информации о профиле для member_id={member_id}")
            await cursor.execute(
                """
                SELECT
                    u.id AS user_id,
                    u.username AS username,
                    u.email AS email,
                    u.first_name AS first_name,
                    u.last_name AS last_name,
                    m.description,
                    m.info_level,
                    t.token AS token,
                    proxy_user.username AS proxy_username
                FROM Members m
                INNER JOIN Users u ON m.user_id = u.id
                LEFT JOIN Tokens t ON m.token = t.id
                LEFT JOIN Users proxy_user ON m.proxy = proxy_user.id
                WHERE m.id = ?
            """,
                (member_id,),
            )
            profile = await fetch_as_dict(cursor)
            return profile[0] if profile else {}
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при получении информации о профиле: {e}")
            raise


# Функция выявления всех статусов, использующихся в группе.
# Нужна только для тестирования
@log_function_call
async def all_status():
    all_st = ["admin", "registrator", "member", "delegate", "proxy", "pre-registrator", "banned"]

    logger.info(f"Все статусы: {all_st}")
    return all_st


# Функция извлечения списка идущих голосований.
# В качестве аргументов принимает номер группы и список статусов голосований.
# Извлекаются голосования имеющие эти статусы
# Возвращает список кортежей из ID, названий и описаний голосовний
@log_function_call
async def list_of_votings(club_id, *voting_status):
    if voting_status:
        placeholders = ", ".join("?" for _ in voting_status)
        query = f"""
            SELECT * FROM Votings
            WHERE club_id = ? AND voting_status IN ({placeholders})
            """
        params = (club_id,) + voting_status
    else:
        query = """
            SELECT id, title, text FROM Votings
            WHERE club_id = ?
            """
        params = (club_id,)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            result = await fetch_as_dict(cursor)
            logger.info("Запрос успешно выполнен.")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise


# Функция извлечения списка вариантов голосования.
# В качестве аргументов принимает id голосования и список статусов вариантов.
# Извлекаются голосования имеющие эти статусы.
# Возвращает cписок кортежей из ID, названий вариантов и статусов вариантов
@log_function_call
async def list_of_variants(
    voting_id: int, *variant_status: str
) -> Optional[List[Dict]]:
    """
    Возвращает список вариантов голосования на основе voting_id и необязательного фильтра по variant_status.

    :param voting_id: ID голосования.
    :param variant_status: Список статусов вариантов (необязательный).
    :return: Список словарей с информацией о вариантах или None в случае ошибки.
    """
    if variant_status:
        placeholders = ", ".join("?" for _ in variant_status)
        query = f"""
            SELECT *
            FROM Variants
            WHERE voting_id = ? AND variant_status IN ({placeholders})
        """
        params = (voting_id,) + variant_status
    else:
        query = """
            SELECT *
            FROM Variants
            WHERE voting_id = ?
        """
        params = (voting_id,)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)  # ✅ Выполняем запрос
            result = await fetch_as_dict(cursor)  # Теперь там есть данные
            logger.info("Запрос успешно выполнен.")
            return result
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise


# Функция извлечения названия и текста варианта по его ID
@log_function_call
async def extract_variant_data(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        ins_str = """
            SELECT title, text, variant_status FROM Variants
            WHERE id = ?
        """
        try:
            await cursor.execute(ins_str, (variant_id,))
            result = await cursor.fetchone()
            logger.info("Запрос успешно выполнен.")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise


@log_function_call
async def extract_status(member_id):
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(
            "SELECT status FROM Status WHERE member_id = ?", (member_id,)
        )
        result = await cursor.fetchall()

        logger.info(
            f"Выполняется запрос: SELECT status FROM Status WHERE member_id = {member_id}"
        )
        logger.info(f"Полученные данные: {result}")

        if result:
            # Преобразуем результат в список уникальных статусов
            statuses = list(set(status[0] for status in result))
            if "member" not in statuses and "candidate" not in statuses:
                statuses.append("user")

            # Упорядочиваю статусы для будущего меню
            st_sort = ["member", "delegate", "admin", "owner", "proxy"]
            ordered_statuses = []

            for item in st_sort:
                if item in statuses:
                    ordered_statuses.append(item)
                    statuses.remove(item)

            # Добавляем оставшиеся статусы в конец списка
            ordered_statuses += statuses

            logger.info(f"Упорядоченные статусы: {ordered_statuses}")
            return ordered_statuses
        else:
            logger.info("Статусы не найдены, возвращается ['user']")
            return ["user"]


# Функция проверяет уникальность присланного username. Возвращает True если он уникален
@log_function_call
async def is_username_uniq(username: str):
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute("SELECT username FROM Users")
        result = await cursor.fetchall()
        if result is None:
            return True
        username_list = [item[0] for item in result]
        return username not in username_list


"""
Функции администрирования бота
"""


@log_function_call
async def update_club_name(club_id: int, new_name: str):
    """
    Обновляет имя группы (club_name) в таблице Clubs.
    :param club_id: ID группы.
    :param new_name: Новое имя группы.
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Обновление имени группы для club_id={club_id} на '{new_name}'")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                UPDATE Clubs SET name = ? WHERE id = ?
                """,
                (new_name, club_id),
            )
            logger.info(
                f"Имя группы успешно обновлено на '{new_name}' для club_id={club_id}"
            )
            return f"Имя группы успешно изменено на '{new_name}'."
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при обновлении имени группы для club_id={club_id}: {e}"
            )
            return "Произошла ошибка при изменении имени группы."


@log_function_call
async def update_club_description(club_id: int, new_description: str):
    """
    Обновляет описание группы (description) в таблице Clubs.
    :param club_id: ID группы.
    :param new_description: Новое описание группы.
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Обновление описания группы для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                UPDATE Clubs SET description = ? WHERE id = ?
                """,
                (new_description, club_id),
            )
            logger.info(f"Описание группы успешно обновлено для club_id={club_id}")
            return "Описание группы успешно изменено."
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при обновлении описания группы для club_id={club_id}: {e}"
            )
            return "Произошла ошибка при изменении описания группы."


@log_function_call
async def update_club_conditions(club_id: int, new_conditions: str):
    """
    Обновляет условия участия в группе (conditions_of_entry) в таблице Clubs.
    :param club_id: ID группы.
    :param new_conditions: Новые условия участия.
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Обновление условий участия для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                UPDATE Clubs SET conditions_of_entry = ? WHERE id = ?
                """,
                (new_conditions, club_id),
            )
            logger.info(f"Условия участия успешно обновлены для club_id={club_id}")
            return "Условия участия успешно изменены."
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при обновлении условий участия для club_id={club_id}: {e}"
            )
            return "Произошла ошибка при изменении условий участия."


@log_function_call
async def update_quenstios_for_the_candidate(club_id: int, new_questions: str):
    """
    Обновляет вопросы кандидатам в группе (conditions_of_entry) в таблице Clubs.
    :param club_id: ID группы.
    :param new_questions: Новые вопросы кандидатам.
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Обновление условий участия для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                UPDATE Clubs SET quenstios_for_the_candidate = ? WHERE id = ?
                """,
                (new_questions, club_id),
            )
            logger.info(
                f"Вопросы для кандидатов успешно обновлены для club_id={club_id}"
            )
            return "Вопросы для кандидатов успешно изменены."
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при обновлении вопросов для кандидатов для club_id={club_id}: {e}"
            )
            return "Произошла ошибка при изменении вопросов для кандидатов."


@log_function_call
async def update_stage_duration(
    club_id: int,
    duration_add_variants=2,
    duration_first_stage=2,
    duration_final=1,
    duration_confirmation=1,
):
    """
    Обновляет продолжительность этапов голосования (в сутках) в группе в таблице Clubs.
    :param club_id: ID группы.
    :param duration_add_variants: продолжительность этапа добавления вариантов
    :param duration_first_st: продолжительность этапа голосования с несколькими вариантами
    :param duration_final: продолжительность финала (этап с двумя вариантами)
    :param duration_confirmation: продолжительность этапа утверждения итога голосования
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Обновление условий участия для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                UPDATE Clubs SET duration_add_variants = ?, duration_first_stage = ?, duration_final = ?, duration_confirmation =? WHERE id = ?
                """,
                (
                    duration_add_variants,
                    duration_first_stage,
                    duration_final,
                    duration_confirmation,
                    club_id,
                ),
            )
            logger.info(
                f"Продолжительность этапов успешно обновлена для club_id={club_id}"
            )
            return "Продолжительность этапов успешно изменена."
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при обновлении продолжительность этапов для club_id={club_id}: {e}"
            )
            return "Произошла ошибка при изменении продолжительности этапов."


@log_function_call
async def update_thresholds(
    club_id: int, threshold_in_voices=None, threshold_in_percent=None
):
    """
    Обновляет пороги доверенных голосов для группы в таблице Clubs.
    :param club_id: ID группы.
    :param threshold_in_voices: Порог в абсолютных голосах (REAL).
    :param threshold_in_percent: Порог в процентах от общего числа голосов (REAL).
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Обновление порогов доверенных голосов для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            if threshold_in_voices is not None and threshold_in_percent is not None:
                await cursor.execute(
                    """
                    UPDATE Clubs
                    SET threshold_in_voices = ?, threshold_in_percent = ?
                    WHERE id = ?
                    """,
                    (threshold_in_voices, threshold_in_percent, club_id),
                )
                logger.info(f"Пороги успешно обновлены для club_id={club_id}")
                return "Пороги доверенных голосов успешно изменены."
            else:
                logger.error(
                    f"Ошибка: Необходимо указать оба параметра для club_id={club_id}"
                )
                return "Произошла ошибка: Необходимо указать оба порога."
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при обновлении порогов для club_id={club_id}: {e}")
            return "Произошла ошибка при изменении порогов."


@log_function_call
async def add_telegram_channel(
    club_id: int, tg_id: int, name: str, type: str, invite_link=None
):
    """
    Добавляет телеграм-канал или чат в таблицу TgChats.
    :param club_id: ID группы.
    :param tg_id: Telegram ID канала/чата.
    :param name: Название канала/чата.
    :param type: Тип (канал или чат)
    :param invite_link: Ссылка на канал или чат
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(
        f"Добавление телеграм-канала/чата с tg_id={tg_id} для club_id={club_id}"
    )
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                INSERT OR IGNORE INTO TgChats (club_id, tg_id, name, channel_type, invite_link) VALUES (?, ?, ?, ?, ?)
                """,
                (club_id, tg_id, name, type, invite_link),
            )
            logger.info(
                f"Телеграм-канал/чат с tg_id={tg_id} успешно добавлен для club_id={club_id}"
            )
            return {"success": True, "message": "Телеграм-канал/чат успешно добавлен."}
        except aiosqlite.IntegrityError as e:
            logger.error(f"Ошибка при добавлении телеграм-канала/чата: {e}")
            return {
                "success": False,
                "message": "Такой телеграм-канал/чат уже существует.",
            }
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при добавлении телеграм-канала/чата: {e}")
            return {
                "success": False,
                "message": "Произошла ошибка при добавлении телеграм-канала/чата.",
            }


@log_function_call
async def remove_telegram_channel(club_id: int, tg_id: int):
    """
    Удаляет телеграм-канал или чат из таблицы TgChats.
    :param tg_id: Telegram ID канала/чата.
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Удаление телеграм-канала/чата с tg_id={tg_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                DELETE FROM TgChats WHERE club_id = ? AND tg_id = ?
                """,
                (club_id, tg_id),
            )
            if cursor.rowcount > 0:
                logger.info(f"Телеграм-канал/чат с tg_id={tg_id} успешно удален.")
                return {
                    "success": True,
                    "message": "Телеграм-канал/чат успешно удален.",
                }
            else:
                logger.info(f"Телеграм-канал/чат с tg_id={tg_id} не найден.")
                return {"success": False, "message": "Телеграм-канал/чат не найден."}
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при удалении телеграм-канала/чата: {e}")
            return {
                "success": False,
                "message": "Произошла ошибка при удалении телеграм-канала/чата.",
            }


@log_function_call
async def set_main_channel(club_id: int, channel_link: str):
    """
    Устанавливает основной телеграм-канал в таблице Clubs.
    :param club_id: ID группы.
    :param channel_link: Ссылка на канал.
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Установка основного канала для club_id={club_id}: {channel_link}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                UPDATE Clubs SET channel_link = ? WHERE id = ?
                """,
                (channel_link, club_id),
            )
            logger.info(f"Основной канал успешно установлен для club_id={club_id}")
            return {"success": True, "message": "Основной канал успешно установлен."}
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при установке основного канала для club_id={club_id}: {e}"
            )
            return {
                "success": False,
                "message": "Произошла ошибка при установке основного канала.",
            }


@log_function_call
async def list_of_channel(club_id: int):
    """
    Извлекает список телеграм-каналов и чатов из таблицы ТgChats.
    :param club_id: ID группы.
    :return: список словарей с информацией о каналах
    """

    query = """
    SELECT *  FROM TgChats
    WHERE club_id = ?
    """
    params = (club_id,)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            result = await fetch_as_dict(cursor)
            logger.debug(
                f"Извлечение списка каналов и чатов, связанных с группой club_id={club_id}: {result}"
            )
            logger.info("Запрос успешно выполнен.")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise


async def registration_entry(
    registrator, object_type, object_id, status, token_id=None
):
    """
    Функция записи в журнал регистраций.
    :param registrator: ID регистратора в таблице Members
    :param object_type: тип объекта, над которым произведено действие
    :param object_id: ID объекта в соответствующей таблице
    :param status: присвоенный объекту статус
    :param token_id: ID токена, если он использовался
    """

    time_reg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with AsyncDatabase(path_db) as cursor:
        try:
            # Делаем запись в таблице регистраций
            await cursor.execute(
                """INSERT INTO Registrations(registrator, object_type, object_id, status, token_id, time_reg)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (registrator, object_type, object_id, status, token_id, time_reg),
            )
            return True
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе со статусом: {e}")
            return False
            raise


# Функция подсчета числа членов группы
@log_function_call
async def count_member(club_id):
    """
    Подсчитывает число участников группы.
    :param club_id: ID группы
    :return: число участников группы
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                SELECT COUNT(*)
                FROM Members m
                INNER JOIN Status s ON m.id = s.member_id
                WHERE m.club_id = ? AND s.status = 'member'
            """,
                (club_id,),
            )
            result = await cursor.fetchone()
            if result:
                (amount,) = result
                logger.info(f"Количество участников в группе {club_id}: {amount}")
                return int(amount)
            else:
                logger.info(f"В группе {club_id} нет участников.")
                return None
        except aiosqlite.Error as e:
            logger.error(
                f"Ошибка при подсчете количества участников с правом голоса: {e}"
            )
            raise


@log_function_call
async def threshold_in_voices(club_id):
    """
    Определяет текущий электоральный порог для присвоения статуса делегата в голосах
    :param club_id: ID группы
    :return: число доверенных голосов, необходимых для получения статуса делегата
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                SELECT threshold_in_voices, threshold_in_percent FROM Clubs WHERE id = ?
            """,
                (club_id,),
            )
            result = await cursor.fetchone()
            if result:
                threshold_in_voices, threshold_in_percent = result
            else:
                logger.info(
                    f"Не определен электоральный порог для делегатов в группе {club_id}"
                )
                return 0
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при извлечении электорального порога: {e}")
            raise
        amount = await count_member(club_id)
        if not amount:
            return threshold_in_voices
        result = max(threshold_in_voices, threshold_in_percent * amount / 100)
        logger.debug(f"Электоральный порог для группы {club_id}: {result}")
        return result


async def check_member_status(member_id: int, target_status: str) -> bool:
    """
    Проверяет, есть ли у пользователя с указанным member_id заданный статус.

    :param member_id: ID пользователя (member_id) для проверки.
    :param target_status: Статус, который нужно проверить (например, 'admin', 'member' и т.д.).
    :return: True, если статус найден, иначе False.
    """
    # Используем контекстный менеджер для работы с базой данных
    async with AsyncDatabase("your_database_name.db") as cursor:
        try:
            # SQL-запрос для проверки наличия статуса
            query = """
                SELECT EXISTS (
                    SELECT 1
                    FROM Status
                    WHERE member_id = ? AND status = ?
                )
            """
            # Выполняем запрос с параметрами
            await cursor.execute(query, (member_id, target_status))
            # Получаем результат (первый элемент кортежа)
            result = await cursor.fetchone()
            # Если результат 1, значит запись существует
            if result:
                return True
            else:
                return False
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса к базе данных: {e}")
            raise
