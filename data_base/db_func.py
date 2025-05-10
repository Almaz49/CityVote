# Модуль db_func.py
# Это файл с функциями, которые используются другими файлами, работающими
# с базой данных
# This is a file with functions that are used by other files that work with
# the database.
import sqlite3
import aiosqlite
import datetime
import logging  # Добавляем импорт модуля logging
from config_data.config import Config, load_config
from functools import wraps
from utils import log_function_call, fetch_as_dict



# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
path_db = config.db.path_db  # путь к базе данных


# Асинхронный контекстный менеджер для работы с базой данных
class AsyncDatabase:
    def __init__(self, db_name):
        self.db_name = db_name

    async def __aenter__(self):
        try:
            self.conn = await aiosqlite.connect(self.db_name)
            self.cursor = await self.conn.cursor()
            logger.info(f"Асинхронное соединение с базой данных {self.db_name} установлено.")
            return self.cursor
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при установке асинхронного соединения с базой данных: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                await self.conn.commit()  # Если ошибок нет, подтвержаем изменения
                logger.info("Асинхронные изменения подтверждены.")
            except aiosqlite.Error as e:
                logger.error(f"Ошибка при подтверждении асинхронных изменений: {e}")
                await self.conn.rollback()
        else:
            await self.conn.rollback()  # В случае ошибки откатываем изменения
            logger.error(f"Произошла асинхронная ошибка: {exc_val}")

        try:
            await self.conn.close()  # Закрываем соединение
            logger.info("Асинхронное соединение с базой данных закрыто.")
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при закрытии асинхронного соединения: {e}")



# Функция редактирования полей в таблице table в строке где столбец key равен value.
# В поля вставляются значения словаря **cv,
# где ключ - имя столбца, а значение - значение поля
@log_function_call
async def db_update(table, key, value, **cv):
    data = list(cv.values()) + [value]
    column = list(cv.keys())
    l = len(cv)
    cols = ''
    for i in range(l):
        cols += f'{column[i]} = ?, '  # формирую часть строки запроса из имен столбцов и вопросов
    cols = cols[:-2]  # отрезаю последнюю запятую и пробел
    ins_str = f'UPDATE {table} SET {cols} WHERE {key} = ?'  # сформирована строка запроса

    logger.info(f"Выполняется запрос: {ins_str}")
    logger.info(f"Данные для запроса: {data}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(ins_str, data)
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
                '''
                SELECT id FROM Users WHERE tg_id = ?
                ''', (tg_id,)
            )
            result = await cursor.fetchone()
            if result:
                user_id, = result
                logger.info(f"Найден user_id={user_id} для tg_id={tg_id}")
                return user_id
            else:
                logger.info(f"Пользователь с tg_id={tg_id} не найден.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при извлечении user_id для tg_id={tg_id}: {e}")
            raise

@log_function_call
async def extract_club_info(club_id):
    """
    Извлекает информацию о группе по её ID.
    :param club_id: ID группы.
    :return: Информация группы в базе данных или None, если имя не найдено.
    """
    logger.info(f"Извлечение информации о группе для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                SELECT *
                FROM Clubs WHERE id = ?
                ''', (club_id,)
            )
            result = await fetch_as_dict(cursor)
            if result:
                logger.info(f"Найдена информация {result[0]} для club_id={club_id}")
                return result[0]
            else:
                logger.info(f"Информация о группе club_id={club_id} не найдено.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при извлечении информации о группе club_id={club_id}: {e}")
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
                '''
                SELECT id FROM Members
                WHERE club_id = ? AND user_id = ?
                ''', (club_id, user_id)
            )
            result = await cursor.fetchone()
            if result:
                member_id, = result
                logger.info(f"Найден member_id={member_id} для club_id={club_id}, user_id={user_id}")
                return member_id
            else:
                logger.info(f"Участник с club_id={club_id}, user_id={user_id} не найден.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при извлечении member_id для club_id={club_id}, user_id={user_id}: {e}")
            raise

# Функция извлечения информации об участниках группы.
# Опционально можно указать статус участников, информация о которых требуется.
@log_function_call
async def list_of_members(club_id, status='all'):
    # Получаем список участников с дополнительным полем info_level из таблицы Members
    query = '''
    SELECT
        Users.first_name,
        Users.last_name,
        Users.tg_id,
        Users.tg_first_name,
        Users.tg_last_name,
        Users.username,
        Members.info_level
    FROM Users
    INNER JOIN Members ON Users.id = Members.user_id
    WHERE Members.club_id = ?
    '''
    params = (club_id,)

    if status != 'all':
        query += '''
        AND Users.id IN (
            SELECT member_id
            FROM Status
            WHERE status = ?
        )
        '''
        params += (status,)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            result = await cursor.fetchall()
            logger.info("Запрос успешно выполнен.")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise

# # Функция извлечения списка участников с определенным статусом, или всех,
# # если статус указан 'all'
# @log_function_call
# async def list_of_members(club_id, status = 'all'):
#     # Получаем список имен участников из БД
#     query = '''
#     SELECT first_name, last_name, tg_id, tg_first_name, tg_last_name, username FROM Users
#     WHERE id IN (SELECT user_id FROM Members
#     WHERE club_id = ?)
#     '''
#     params = (club_id,)

#     if status != 'all':
#         query += '''
#         AND id IN (SELECT member_id FROM Status
#         WHERE status = ?)
#         '''
#         params += (status,)

#     logger.info(f"Выполняется запрос: {query}")
#     logger.info(f"Параметры для запроса: {params}")

#     async with AsyncDatabase(path_db) as cursor:
#         try:
#             await cursor.execute(query, params)
#             answ = await cursor.fetchall()
#             logger.info("Запрос успешно выполнен.")
#             return answ
#         except aiosqlite.Error as e:
#             logger.error(f"Ошибка при выполнении запроса: {e}")
#             raise



# Функция извлечения данных о пользователе. *c - список столбцов, данные из которых
# извлекаются.
@log_function_call
async def extract_user_data(user_id, *columns):
    cols = ', '.join(columns) if columns else '*'  # формирую часть строки запроса из имен столбцов или '*'

    ins_str = f"SELECT {cols} FROM Users WHERE id = ?"

    logger.info(f"Выполняется запрос: {ins_str}")
    logger.info(f"Параметры для запроса: {(user_id,)}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(ins_str, (user_id,))
            answ = await cursor.fetchone()
            logger.info("Запрос успешно выполнен.")
            return answ
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise

# Функция выявления всех статусов, использующихся в группе.
# Нужна только для тестирования
@log_function_call
async def all_status():
    # async with AsyncDatabase(path_db) as cursor:
    #     # Извлекаем из БД неповторяющиеся статусы
    #     await cursor.execute(
    #         '''
    #         SELECT DISTINCT status FROM Status
    #         '''
    #     )
    #     answ = await cursor.fetchall()

    #     # Добавляем те статусы, которые в принципе предусматриваются
    #     predefined_statuses = [('admin',), ('registrator',), ('member',),
    #                            ('delegate',), ('proxy',), ('moderator',)]
    #     all_st = list(set(answ + predefined_statuses))

    #     # Преобразуем список кортежей просто в список
    #     all_st = [status[0] for status in all_st]

        all_st = ['admin','registrator', 'member','delegate', 'proxy', 'pre-registrator']

        logger.info(f"Все статусы: {all_st}")
        return all_st

# Функция извлечения списка идущих голосований.
# В качестве аргументов принимает номер группы и список статусов голосований.
# Извлекаются голосования имеющие эти статусы
# Возвращает список кортежей из ID, названий и описаний голосовний
@log_function_call
async def list_of_votings(club_id, *voting_status):
    if voting_status:
        placeholders = ', '.join('?' for _ in voting_status)
        query = f'''
            SELECT id, title, text FROM Votings
            WHERE club_id = ? AND voting_status IN ({placeholders})
            '''
        params = (club_id,) + voting_status
    else:
        query = '''
            SELECT id, title, text FROM Votings
            WHERE club_id = ?
            '''
        params = (club_id,)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            ans = await cursor.fetchall()
            logger.info("Запрос успешно выполнен.")
            return ans
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise

# Функция извлечения списка вариантов голосования.
# В качестве аргументов принимает id голосования и список статусов вариантов.
# Извлекаются голосования имеющие эти статусы.
# Возвращает cписок кортежей из ID, названий вариантов и статусов вариантов
@log_function_call
async def list_of_variants(voting_id, *variant_status):
    if variant_status:
        placeholders = ', '.join('?' for _ in variant_status)
        query = f'''
            SELECT id, title, variant_status, text FROM Variants
            WHERE voting_id = ? AND variant_status IN ({placeholders})
            '''
        params = (voting_id,) + variant_status
    else:
        query = '''
            SELECT id, title, variant_status, text FROM Variants
            WHERE voting_id = ?
            '''
        params = (voting_id,)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            result = await cursor.fetchall()
            logger.info("Запрос успешно выполнен.")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise

# Функция извлечения названия и текста варианта по его ID
@log_function_call
async def extract_variant_data(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        ins_str = '''
            SELECT title, text, variant_status FROM Variants
            WHERE id = ?
        '''
        try:
            await cursor.execute(ins_str,(variant_id,))
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
            'SELECT status FROM Status WHERE member_id = ?',
            (member_id,)
        )
        result = await cursor.fetchall()

        logger.info(f"Выполняется запрос: SELECT status FROM Status WHERE member_id = {member_id}")
        logger.info(f"Полученные данные: {result}")

        if result:
            # Преобразуем результат в список уникальных статусов
            statuses = list(set(status[0] for status in result))
            if 'member' not in statuses and 'candidate' not in statuses:
                statuses.append('user')

            # Упорядочиваю статусы для будущего меню
            st_sort = ['member', 'delegate', 'admin', 'owner', 'proxy']
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
            return ['user']

# Функция проверяет уникальность присланного username. Возвращает True если он уникален
@log_function_call
async def is_username_uniq(username:str):
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(
            'SELECT username FROM Users'
        )
        result = await cursor.fetchall()
        return (username,) not in result

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
                '''
                UPDATE Clubs SET name = ? WHERE id = ?
                ''', (new_name, club_id)
            )
            logger.info(f"Имя группы успешно обновлено на '{new_name}' для club_id={club_id}")
            return f"Имя группы успешно изменено на '{new_name}'."
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при обновлении имени группы для club_id={club_id}: {e}")
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
                '''
                UPDATE Clubs SET description = ? WHERE id = ?
                ''', (new_description, club_id)
            )
            logger.info(f"Описание группы успешно обновлено для club_id={club_id}")
            return "Описание группы успешно изменено."
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при обновлении описания группы для club_id={club_id}: {e}")
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
                '''
                UPDATE Clubs SET conditions_of_entry = ? WHERE id = ?
                ''', (new_conditions, club_id)
            )
            logger.info(f"Условия участия успешно обновлены для club_id={club_id}")
            return "Условия участия успешно изменены."
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при обновлении условий участия для club_id={club_id}: {e}")
            return "Произошла ошибка при изменении условий участия."

@log_function_call
async def add_telegram_channel(club_id: int, tg_id: int, name: str, type: str, invite_link:str = None):
    """
    Добавляет телеграм-канал или чат в таблицу TgChats.
    :param club_id: ID группы.
    :param tg_id: Telegram ID канала/чата.
    :param name: Название канала/чата.
    :param type: Тип (канал или чат)
    :param invite_link: Ссылка на канал или чат
    :return: Сообщение об успешности или неудачности операции.
    """
    logger.info(f"Добавление телеграм-канала/чата с tg_id={tg_id} для club_id={club_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                INSERT OR IGNORE INTO TgChats (club_id, tg_id, name, channel_type, invite_link) VALUES (?, ?, ?, ?, ?)
                ''', (club_id, tg_id, name, type, invite_link)
            )
            logger.info(f"Телеграм-канал/чат с tg_id={tg_id} успешно добавлен для club_id={club_id}")
            return {
                "success": True,
                "message": "Телеграм-канал/чат успешно добавлен."
            }
        except aiosqlite.IntegrityError as e:
            logger.error(f"Ошибка при добавлении телеграм-канала/чата: {e}")
            return {
                "success": False,
                "message":"Такой телеграм-канал/чат уже существует."
            }
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при добавлении телеграм-канала/чата: {e}")
            return {
                "success": False,
                "message":"Произошла ошибка при добавлении телеграм-канала/чата."
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
                '''
                DELETE FROM TgChats WHERE club_id = ? AND tg_id = ?
                ''', (club_id, tg_id)
            )
            if cursor.rowcount > 0:
                logger.info(f"Телеграм-канал/чат с tg_id={tg_id} успешно удален.")
                return {
                "success": True,
                "message": "Телеграм-канал/чат успешно удален."
                }
            else:
                logger.info(f"Телеграм-канал/чат с tg_id={tg_id} не найден.")
                return {
                "success": False,
                "message":"Телеграм-канал/чат не найден."
                }
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при удалении телеграм-канала/чата: {e}")
            return {
                "success": False,
                "message":"Произошла ошибка при удалении телеграм-канала/чата."
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
                '''
                UPDATE Clubs SET channel_link = ? WHERE id = ?
                ''', (channel_link, club_id)
            )
            logger.info(f"Основной канал успешно установлен для club_id={club_id}")
            return {
                "success": True,
                "message": "Основной канал успешно установлен."
            }
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при установке основного канала для club_id={club_id}: {e}")
            return {
                "success": False,
                "message":"Произошла ошибка при установке основного канала."
            }

@log_function_call
async def list_of_channel(club_id: int):
    """
    Извлекает список телеграм-каналов и чатов из таблицы ТgChats.
    :param club_id: ID группы.
    :return: список словарей с информацией о каналах
    """

    query = '''
    SELECT *  FROM TgChats
    WHERE club_id = ?
    '''
    params = (club_id,)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            result = await fetch_as_dict(cursor)
            logger.debug(f"Извлечение списка каналов и чатов, связанных с группой club_id={club_id}: {result}")
            logger.info("Запрос успешно выполнен.")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise

async def registration_entry(registrator, object_type, object_id, status, token_id=None):
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
                '''INSERT INTO Registrations(registrator, object_type, object_id, status, token_id, time_reg)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (registrator, object_type, object_id, status, token_id, time_reg)
            )
            return True
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе со статусом: {e}")
            return False
            raise