# Модуль db_func.py
# Это файл с функциями, которые используются другими файлами, работающими
# с базой данных
# This is a file with functions that are used by other files that work with
# the database.
import sqlite3
import aiosqlite
import logging  # Добавляем импорт модуля logging
from config_data.config import Config, load_config
from functools import wraps


def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Вызвана функция {func.__name__}")
        return func(*args, **kwargs)
    return wrapper



# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
path_db = config.db.path_db  # путь к базе данных

# Это декоратор, который каждую функцию объявляет в логах
def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Вызвана функция {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

# Создаем контекстный менеджер для работы с базой данных
class Database:
    def __init__(self, db_name):
        self.db_name = db_name

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            logging.info(f"Соединение с базой данных {self.db_name} установлено.")
            return self.cursor
        except sqlite3.Error as e:
            logging.error(f"Ошибка при установке соединения с базой данных: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                self.conn.commit()  # Если ошибок нет, подтвержаем изменения
                logging.info("Изменения подтверждены.")
            except sqlite3.Error as e:
                logging.error(f"Ошибка при подтверждении изменений: {e}")
                self.conn.rollback()
        else:
            self.conn.rollback()  # В случае ошибки откатываем изменения
            logging.error(f"Произошла ошибка: {exc_val}")

        try:
            self.conn.close()  # Закрываем соединение
            logging.info("Соединение с базой данных закрыто.")
        except sqlite3.Error as e:
            logging.error(f"Ошибка при закрытии соединения: {e}")

# Асинхронный контекстный менеджер для работы с базой данных
class AsyncDatabase:
    def __init__(self, db_name):
        self.db_name = db_name

    async def __aenter__(self):
        try:
            self.conn = await aiosqlite.connect(self.db_name)
            self.cursor = await self.conn.cursor()
            logging.info(f"Асинхронное соединение с базой данных {self.db_name} установлено.")
            return self.cursor
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при установке асинхронного соединения с базой данных: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            try:
                await self.conn.commit()  # Если ошибок нет, подтвержаем изменения
                logging.info("Асинхронные изменения подтверждены.")
            except aiosqlite.Error as e:
                logging.error(f"Ошибка при подтверждении асинхронных изменений: {e}")
                await self.conn.rollback()
        else:
            await self.conn.rollback()  # В случае ошибки откатываем изменения
            logging.error(f"Произошла асинхронная ошибка: {exc_val}")

        try:
            await self.conn.close()  # Закрываем соединение
            logging.info("Асинхронное соединение с базой данных закрыто.")
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при закрытии асинхронного соединения: {e}")

#Функция выборки данных из БД из таблицы table, c выборкой по столбцу key
#со значением value. *с - названия столбцов, значения из которых нужны
# данные. При отсутствии *с - извлекаются все данные.

# def db_select(table,key=None,value=None,*c):
#     cols = ''
#     for col in c:
#         cols += f'{col}, ' # формирую часть строки запроса из имен столбцов
#     cols = cols[: -2] # отрезаю последнюю запятую и пробел
#     if not cols:
#         cols = '*'
#     ins_str = f"SELECT {cols} FROM {table} WHERE {key} = '{value}'"
# #     print(ins_str)
#     with Database(path_db) as cursor:
#         cursor.execute(ins_str)
#         answ = cursor.fetchall()
#         return(answ)

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

    logging.info(f"Выполняется запрос: {ins_str}")
    logging.info(f"Данные для запроса: {data}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(ins_str, data)
            logging.info("Запрос успешно выполнен.")
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при выполнении запроса: {e}")
            raise

@log_function_call
async def extract_user_id(tg_id):
    """
    Извлекает ID пользователя по его Telegram ID.
    :param tg_id: Telegram ID пользователя.
    :return: ID пользователя в базе данных или None, если пользователь не найден.
    """
    logging.info(f"Извлечение user_id для tg_id={tg_id}")
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
                logging.info(f"Найден user_id={user_id} для tg_id={tg_id}")
                return user_id
            else:
                logging.info(f"Пользователь с tg_id={tg_id} не найден.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при извлечении user_id для tg_id={tg_id}: {e}")
            raise


@log_function_call
async def extract_member_id(club_id, user_id):
    """
    Извлекает ID участника группы по ID группы и ID пользователя.
    :param club_id: ID группы.
    :param user_id: ID пользователя.
    :return: ID участника группы в базе данных или None, если участник не найден.
    """
    logging.info(f"Извлечение member_id для club_id={club_id}, user_id={user_id}")
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
                logging.info(f"Найден member_id={member_id} для club_id={club_id}, user_id={user_id}")
                return member_id
            else:
                logging.info(f"Участник с club_id={club_id}, user_id={user_id} не найден.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при извлечении member_id для club_id={club_id}, user_id={user_id}: {e}")
            raise

# Функция извлечения списка участников с определенным статусом, или всех,
# если статус указан 'all'
@log_function_call
async def list_of_members(club_id, status):
    # Получаем список имен участников из БД
    query = '''
    SELECT first_name, last_name, tg_id, tg_first_name, tg_last_name FROM Users
    WHERE id IN (SELECT user_id FROM Members
    WHERE club_id = ?)
    '''
    params = (club_id,)

    if status != 'all':
        query += '''
        AND id IN (SELECT member_id FROM Status
        WHERE status = ?)
        '''
        params += (status,)

    logging.info(f"Выполняется запрос: {query}")
    logging.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            answ = await cursor.fetchall()
            logging.info("Запрос успешно выполнен.")
            return answ
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при выполнении запроса: {e}")
            raise

#Функция извлечения ID пользователя по телеграм ID
# def extract_user_id(tg_id):
#     with Database(path_db) as cursor:
#         cursor.execute(
#             '''
#             SELECT id FROM Users WHERE tg_id = ?
#             ''', (tg_id,)
#                 )
#         answ = cursor.fetchone()
#             #print(answ)
#         if answ:
#             user_id, = answ
#             return(user_id)
#         else: return None

# Функция извлечения данных о пользователе. *c - список столбцов, данные из которых
# извлекаются.
@log_function_call
async def extract_user_data(user_id, *c):
    cols = ', '.join(c) if c else '*'  # формирую часть строки запроса из имен столбцов или '*'

    ins_str = f"SELECT {cols} FROM Users WHERE id = ?"

    logging.info(f"Выполняется запрос: {ins_str}")
    logging.info(f"Параметры для запроса: {(user_id,)}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(ins_str, (user_id,))
            answ = await cursor.fetchone()
            logging.info("Запрос успешно выполнен.")
            return answ
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при выполнении запроса: {e}")
            raise

# Функция выявления всех статусов, использующихся в группе.
# Нужна только для тестирования
@log_function_call
async def all_status():
    async with AsyncDatabase(path_db) as cursor:
        # Извлекаем из БД неповторяющиеся статусы
        await cursor.execute(
            '''
            SELECT DISTINCT status FROM Status
            '''
        )
        answ = await cursor.fetchall()

        # Добавляем те статусы, которые в принципе предусматриваются
        predefined_statuses = [('admin',), ('registrator',), ('member',),
                               ('delegate',), ('proxy',), ('moderator',)]
        all_st = list(set(answ + predefined_statuses))

        # Преобразуем список кортежей просто в список
        all_st = [status[0] for status in all_st]

        logging.info(f"Все статусы: {all_st}")
        return all_st

# Функция извлечения списка идущих голосований.
# В качестве аргументов принимает номер группы и список статусов голосований.
# Извлекаются голосования имеющие эти статусы
# Возвращает список кортежей из ID и названий
@log_function_call
async def list_of_votes(club_id, *vote_status):
    if vote_status:
        placeholders = ', '.join('?' for _ in vote_status)
        query = f'''
            SELECT id, title FROM Votes
            WHERE club_id = ? AND vote_status IN ({placeholders})
            '''
        params = (club_id,) + vote_status
    else:
        query = '''
            SELECT id, title FROM Votes
            WHERE club_id = ?
            '''
        params = (club_id,)

    logging.info(f"Выполняется запрос: {query}")
    logging.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            ans = await cursor.fetchall()
            logging.info("Запрос успешно выполнен.")
            return ans
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при выполнении запроса: {e}")
            raise

# Функция извлечения списка вариантов голосования.
# В качестве аргументов принимает id голосования и список статусов вариантов.
# Извлекаются голосования имеющие эти статусы.
# Возвращает cписок кортежей из ID, названий вариантов и статусов вариантов
@log_function_call
async def list_of_variants(vote_id, *variant_status):
    if variant_status:
        placeholders = ', '.join('?' for _ in variant_status)
        query = f'''
            SELECT id, title, variant_status FROM Variants
            WHERE vote_id = ? AND variant_status IN ({placeholders})
            '''
        params = (vote_id,) + variant_status
    else:
        query = '''
            SELECT id, title, variant_status FROM Variants
            WHERE vote_id = ?
            '''
        params = (vote_id,)

    logging.info(f"Выполняется запрос: {query}")
    logging.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            ans = await cursor.fetchall()
            logging.info("Запрос успешно выполнен.")
            return ans
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при выполнении запроса: {e}")
            raise

# Извлечение статусов участника группы (отдает список статусов)
# def extract_status(member_id):
#     with Database(path_db) as cursor:
# #         print(member_id)
#         cursor.execute(
#         'SELECT status FROM Status WHERE member_id = ?',
#         (member_id,)
#         )
#         result = cursor.fetchall()
#         if result:
#             answ = list(list(zip(*set(result)))[0])
#             st_list = []
#             # Упорядочиваю статусы для будущего меню
#             st_sort = ['member','delegate','admin','owner','proxy']
#             for item in st_sort:
#                 if item in answ:
#                     st_list.append(item)
#                     answ.remove(item)
#             st_list += answ
#             return(st_list)
#         else:
#             return(['user'])

@log_function_call
async def extract_status(member_id):
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(
            'SELECT status FROM Status WHERE member_id = ?',
            (member_id,)
        )
        result = await cursor.fetchall()

        logging.info(f"Выполняется запрос: SELECT status FROM Status WHERE member_id = {member_id}")
        logging.info(f"Полученные данные: {result}")

        if result:
            # Преобразуем результат в список уникальных статусов
            statuses = list(set(status[0] for status in result))

            # Упорядочиваю статусы для будущего меню
            st_sort = ['member', 'delegate', 'admin', 'owner', 'proxy']
            ordered_statuses = []

            for item in st_sort:
                if item in statuses:
                    ordered_statuses.append(item)
                    statuses.remove(item)

            # Добавляем оставшиеся статусы в конец списка
            ordered_statuses += statuses

            logging.info(f"Упорядоченные статусы: {ordered_statuses}")
            return ordered_statuses
        else:
            logging.info("Статусы не найдены, возвращается ['user']")
            return ['user']


"""
for i in range(5):
    a = count_directly_votes(i+1)

    b = count_proxy_votes(i+1)

    print('вариант ',i+1,': всего голосов - ', a+b, ', отданных напрямую - ', a,
          ', через преставителя',b, ', голосов неголосующх - ', count_directly_empty_votes(i+2))
"""
# print(list_of_variants(3))
# votist(10)

# добавляем пользователей в бд
"""


# Добавляем участников в группу 1
with Database(path_db) as cursor:
    for i in range(100):
        cursor.execute('''INSERT INTO Members
        (club_id, user_id, proxy)  VALUES (?,?,?)''',
        (1, i+6,  random.randint(1,5))
                       )

# Присваиваем части участникам статус member, другим - candidate
with Database(path_db) as cursor:
    for i in range(100):
        cursor.execute('''INSERT INTO Status
        (member_id, status)  VALUES (?,?)''',
        (i+6,
         'member' if random.randint(1,5) < 5 else 'candidate'
         )
                       )


# Голосуем за участников
with Database(path_db) as cursor:
    for i in range(100):
        if random.randint(1,5) > 4:
            cursor.execute('''INSERT INTO Elections
        (member_id, variant_id, time_election)  VALUES (?,?,?)''',
        (i+2,
         random.randint(2,5),
         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
         )
                       )
            time.sleep(2)
            print( 'участник ', i+2, ' выбрал вариант ')


# Добавляем статус в голосования участников
with Database(path_db) as cursor:
    for i in range(100):
        variant_id = past_choise(i+1, 1)
        if variant_id:
            cursor.execute('''UPDATE Elections SET
        status = ?
        WHERE variant_id = ? AND  member_id = ?
        ''',
        ('valid',variant_id, i+1)
         )
            print( 'участник ', i+1, ' выбрал вариант ', variant_id)

"""
