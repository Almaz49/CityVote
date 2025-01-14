# Это файл с функциями, которые используются другими файлами, работающими
# с базой данных

# This is a file with functions that are used by other files that work with
# the database.

import sqlite3
from config_data.config import Config, load_config

# Загружаем конфиг в переменную config
config: Config = load_config('.env')

if __name__ == '__main__':
    path_db = r'C:\Users\Alex\progs\CityVote\dbg1.db'
else:
    path_db = config.db.path_db #путь к базе данных


#Создаем контекстный менеджер для работы с базой данных
class Database:
    def __init__(self, db_name):
        self.db_name = db_name

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit() # Если ошибок нет, подтверждаем изменения
        else:
            self.conn.rollback() # В случае ошибки откатываем изменения
#             self.exc_val = exc_val
#             print(exc_val)
#             return(exc_val)
            #print('type:',exc_type, ' value:', exc_val, 'traceback: ', exc_tb)
            #return(exc_val)
        self.conn.close() # Закрываем соединение





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

#функция редактирования полей в таблице table в строке где столбец key равен value.
#В поля вставляются значения словаря **cv,
#где ключ - имя солбца, а значение - значение поля
def db_update(table,key,value, **cv):
    data =  list(cv.values()) + [value]
    column = list(cv.keys())
    #print(data)
    l = len(cv)
    cols = ''
    qw = ''
    for i in range(l):
        cols += f'{column[i]} = ?, ' # формирую часть строки запроса из имен столбцов и вопросов
    cols = cols[: -2] # отрезаю последнюю запятую и пробел
    ins_str = f'UPDATE {table} SET {cols} WHERE {key} = ?' # сформирована строка запроса
#     print(ins_str)
#     print(data)
    with Database(path_db) as cursor:
        cursor.execute(ins_str, data)


# Функция извлечения списка участников с определенным статусом, или всех,
# если статус указан 'all'
def list_of_members(club_id, status):
    #Получаем список имен участников из БД
    with Database(path_db) as cursor:
        if status == 'all':
            cursor.execute(
            '''
            SELECT first_name, last_name, tg_id, tg_first_name, tg_last_name FROM Users
            WHERE id IN (SELECT user_id FROM Members
            WHERE club_id = ? )
            ''',(club_id,)
                )
            answ = cursor.fetchall()
        else:
            cursor.execute(
            '''
            SELECT first_name, last_name, tg_id, tg_first_name, tg_last_name FROM Users
            WHERE id IN (SELECT user_id FROM Members
            WHERE club_id = ? AND id IN (SELECT member_id FROM Status
            WHERE status = ?))
            ''',(club_id,status)
                )
            answ = cursor.fetchall()
        return(answ)


#Функция извлечения ID пользователя по телеграм ID
def extract_user_id(tg_id):
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT id FROM Users WHERE tg_id = ?
            ''', (tg_id,)
                )
        answ = cursor.fetchone()
            #print(answ)
        if answ:
            user_id, = answ
            return(user_id)
        else: return None


#Функция извлечения ID участника группы по телеграм id
def extract_member_id(club_id, user_id):
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT id FROM Members
            WHERE club_id = ? AND user_id IN (SELECT id FROM Users
            WHERE user_id = ?)
            ''', (club_id, user_id)
                )
        answ = cursor.fetchone()
        if answ:
            member_id, = answ
            return(member_id)
        else:
            return(None)


#Функция извлечения данных о пользователе. *с - список столбцов, данные из которых
# извлекаются.
def extract_user_data(user_id,*c):
    cols = ''
    for col in c:
        cols += f'{col}, ' # формирую часть строки запроса из имен столбцов
    cols = cols[: -2] # отрезаю последнюю запятую и пробел
    if not cols:
        cols = '*'
    ins_str = f"SELECT {cols} FROM Users WHERE id = ?"
#     print(ins_str)
    with Database(path_db) as cursor:
        cursor.execute(ins_str,(user_id,))
        answ = cursor.fetchone()
        return(answ)



# Функция выявления всех статусов, использующихся в группе.
# Нужна только для тестирования
def all_status():
    with Database(path_db) as cursor:
#         извлекаем из БД неповторяющиеся статусы
        cursor.execute(
            '''
            SELECT DISTINCT status FROM Status
            '''
                )
#         добавляем те статусы, которые в принципе предусматриваются
        answ = cursor.fetchall() + [('admin',),('registrator',),('member',),
                                    ('delegate',),('proxy',),('moderator',)]
#         print(answ)
# удаляем повторяющиеся элементы и првращаем список кортежей просто в список
        all_st = list(list(zip(*set(answ)))[0])
#         print(all_st)
        return(all_st)


# Функция извлечения списка идущих голосований.
# В качестве аргументов принимает номер группы и список статусов голосований.
# Извлекаются голосования имеющие эти статусы
# Возвращает список кортежей из ID и названий
def list_of_votes(club_id,*vote_status):
    if vote_status:
        query = ''
        for status in vote_status:
            query += "'" + status + "', "
        query = query[:-2]
        query = f'''
            SELECT id, title FROM Votes
            WHERE club_id = ? AND vote_status IN ({query})
            '''
    else:
        query = '''
            SELECT id, title FROM Votes
            WHERE club_id = ?
            '''
    # print('Запрос:', query)
    with Database(path_db) as cursor:
        cursor.execute(query, (club_id,) )
        ans = cursor.fetchall()
        # print(ans)
        return(ans)
#         if ans:
#             list_id = list(zip(*ans))[0]
#             list_title = list(zip(*ans))[1]
#             return(list_id,list_title)


# Функция извлечения списка вариантов голосования.
# В качестве аргументов принимает id голосования и список статусов вариантов.
# Извлекаются голосования имеющие эти статусы.
# Возвращает писок кортежей из ID и названий вариантов
def list_of_variants(vote_id,*variant_status):
    if variant_status:
        query = ''
        for status in variant_status:
            query += "'" + status + "', "
        query = query[:-2]
        query = f'''
            SELECT id, title FROM Variants
            WHERE vote_id = ? AND varaiant_status IN ({query})
            '''
    else:
        query = '''
            SELECT id, title FROM Variants
            WHERE vote_id = ?
            '''
    print('Запрос:', query)
    with Database(path_db) as cursor:
        cursor.execute(query, (vote_id,) )
        ans = cursor.fetchall()
        print(ans)
        return(ans)
#         if ans:
#             list_id = list(zip(*ans))[0]
#             list_title = list(zip(*ans))[1]
#             return(list_id,list_title)


# Извлечение статусов участника группы (отдает список статусов)
def extract_status(member_id):
    with Database(path_db) as cursor:
#         print(member_id)
        cursor.execute(
        'SELECT status FROM Status WHERE member_id = ?',
        (member_id,)
        )
        ans = cursor.fetchall()
        if ans:
            answ = list(list(zip(*set(ans)))[0])
            return(answ)
        else:
            return(['user'])
