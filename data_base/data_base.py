import sqlite3
from config_data.config import Config, load_config
import datetime
import random
import time

"""
БАЗА ДАННЫХ
Здесь функции взаимодействия с БД исходя из user_id и member_id пользователей.
Функции универсальны независимо от платформы.
Специфика телеграм-бота вынесена в telegram_bot_logic.
То есть, телеграм-бот взаимодействует с БД и data_base только через telegram_bot_logic (пока это не так, но надо стремиться наверно)
А data_base ничего "не знает" о телеграм-боте
"""

# Загружаем конфиг в переменную config
config: Config = load_config('.env')

if __name__ == '__main__':
    path_db = r'C:\Users\Алексей\Documents\telebot\registrator\dbg1.db'
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
        

"""
#Функция выборки данных из БД из таблицы table, c выборкой по столбцу key
#со значением value. *с - названия столбцов, значения из которых нужны
# данные. При отсутствии *с - извлекаются все данные.

def db_select(table,key=None,value=None,*c):
    cols = ''
    for col in c:
        cols += f'{col}, ' # формирую часть строки запроса из имен столбцов 
    cols = cols[: -2] # отрезаю последнюю запятую и пробел
    if not cols:
        cols = '*'
    ins_str = f"SELECT {cols} FROM {table} WHERE {key} = '{value}'"
#     print(ins_str)
    with Database(path_db) as cursor:
        cursor.execute(ins_str)
        answ = cursor.fetchall()
        return(answ)
"""
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
    #Получаем список имен модераторов из БД
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

# Функция извлечения списка регистраторов 
def list_of_registrators(club_id):
    #Получаем список имен модераторов из БД
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT first_name, last_name, tg_id, tg_first_name, tg_last_name FROM Users
            WHERE id IN (SELECT user_id FROM Members
            WHERE club_id = ? AND id IN (SELECT member_id FROM Status
            WHERE status = 'registrator'))
            ''',(club_id,)
                )
        answ = cursor.fetchall()
        return(answ)

# Функция извлечения списка представителей 
def list_of_proxy(club_id):
    #Получаем список имен и tg_id представителей из БД
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT first_name, last_name,  tg_id, tg_first_name, tg_last_name FROM Users
            WHERE id IN (SELECT user_id FROM Members
            WHERE club_id = ? AND id IN (SELECT member_id FROM Status
            WHERE status = 'proxy'))
            ''',(club_id,)
                )
        answ = cursor.fetchall()
        return(answ)


# Функция извлечения списка делегатов 
def list_of_delegates(club_id):
    #Получаем список имен и tg_id представителей из БД
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT first_name, last_name,  tg_id, tg_first_name, tg_last_name FROM Users
            WHERE id IN (SELECT user_id FROM Members
            WHERE club_id = ? AND id IN (SELECT member_id FROM Status
            WHERE status = 'delegate'))
            ''',(club_id,)
                )
        answ = cursor.fetchall()
        return(answ)

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
    print('Запрос:', query)
    with Database(path_db) as cursor:
        cursor.execute(query, (club_id,) )
        ans = cursor.fetchall()
        print(ans)
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

# запись нового пользователя в базу данных из телеграм-бота
# (того, который первый раз им воспользовался)
def new_user_tg(tg_id):
    with Database(path_db) as cursor:
        cursor.execute(
            'INSERT OR IGNORE INTO Users(tg_id) VALUES(?)',
                       (tg_id,)
            )

# запись нового учатника в группу
def new_member(club_id,user_id):
    with Database(path_db) as cursor:
        cursor.execute(
            'INSERT OR IGNORE INTO Members(club_id,user_id) VALUES(?,?)',
                       (club_id, user_id)
            )


#Запись нового статуса (registrator - member_id того, кто присвоил статус, member_id кому, какой статус, подтверждающий токен)
# Если переан статус в виде 'not_status', соответствующий статус удаляется
def new_status(registrator,member_id,status,token_id=None):
    time_reg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     print(registrator, member_id, status, time_reg)
    with Database(path_db) as cursor:
            #Делаем запись в таблице регистраций
        cursor.execute(
            '''INSERT INTO Registrations(registrator,member_id,status,token_id,time_reg)
            VALUES (?,?,?,?,?)''',(registrator,member_id,status,token_id,time_reg)
            )
        #Проверяем, не удаляется ли статус (не начинается лли с 'not')
        status1 = status.split('_') 
        if status1[0] == 'not':
            cursor.execute(
                '''DELETE FROM STATUS WHERE member_id = ? AND status = ?''',
                (member_id,status1[1])
                )
        else:
            cursor.execute(
                '''INSERT OR IGNORE INTO STATUS(member_id,status) VALUES (?,?)''',
                (member_id,status)
                )
      
# Создание нового голосования. Создается название голосования и описание, также
# может быть введен тип голосования и ссылка. Варианты добавляются позже.
def new_vote(club_id, creator, title, text = None, 
             vote_type = 'usual', vote_status = None, link_id = None):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(title) > 40:
        flag = False
        answ_str = ('Название не должо быть длиннее 40 символов'
                    'Придумайте другое название')
    
    else:
        with Database(path_db) as cursor:
            cursor.execute(
            """
            SELECT title FROM Votes WHERE club_id = ? AND vote_status <> 'finished'
            """,(club_id,)
            )
            titles = cursor.fetchall()
            if (title,) not in titles:
                print('Такого голосования еще нет')
                cursor.execute(
            '''INSERT INTO Votes(club_id, creator, title, text, time_create, vote_type, vote_status, link_id)
            VALUES (?,?,?,?,?,?,?,?)''',(club_id, creator, title, text, time_create, vote_type, vote_status, link_id)
            )
                answ_str = 'Голосование добавлено'
                flag = True
            else:
                answ_str = ('Уже есть идущее голосование с таким названием.'
                       'Придумайте другое название')
                flag = False 
    print(flag, answ_str)
    return (flag,answ_str)

# Создание варианта для голосования. Добавляется только в голосования
# со статусом ожидания вариантов.
# В БД вносится автор (member_id)  заголовок варианта, текст варианта,
# если есть  - ссылка
# Возвращает комментарий по итогам добавления
def new_variant(vote_id, author, title, text = None, link_id = None):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if len(title) > 40:
        flag,answ_str = 'too_long','Название не должо быть длиннее 40 символов'
    else:
        with Database(path_db) as cursor:
            cursor.execute(
            """
            SELECT vote_status FROM Votes WHERE id = ?
            """,(vote_id,)
            )
            status, = cursor.fetchone()
            if status == 'add_variants':
                print('Добавление вариантов у голосования возможно')
                cursor.execute(
            """
         SELECT title FROM Variants WHERE vote_id = ?
            """,
            (vote_id,)
            )
                titles = cursor.fetchall()
                print(titles)
                if (title,) not in titles:
                    print('Такого варианта еще нет')
                    cursor.execute(
            '''
            INSERT INTO Variants(vote_id, author, title, text, time_create, link_id)
            VALUES (?,?,?,?,?,?)
            ''',(vote_id, author, title, text, time_create, link_id)
            )
                    answ_str = 'Вариант добавлен'
                    flag = 'OK' 
                else:
                    answ_str = '''Вариант с таким названием уже существует.
Придумайте другое название'''
                    flag = 'double' 
                    print(answ_str)
            else:
                answ_str = 'К этому голосованию нельзя добавить варианты'
                flag = 'too_late' 
                print(answ_str)
    return(flag,answ_str)





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


# Функция выбора представителя. Передается id участника, id выбранного им представителя.
# Производится запись id представителя в колонку proxy таблицы Members
# Производится запись в таблицу Trusts, фиксирующая делегирование голоса

def trust(member_id, proxy):
    time_trust = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            UPDATE Members SET proxy = ? WHERE memder_id = ?
            ''', (proxy,member_id)
                )
        cursor.execute(
            '''
          INSERT INTO Trusts (member_id, proxy_id, time_trust) VALUES (?,?,?)
            ''',(member_id, proxy, time_trust)
            )

    

# Функция старта голосования. Меняем статус голосования на 'ongoing'
# Указываем, кто запустил голосование (если не автоматически)

def vote_start(vote_id, starter = None):
    time_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            UPDATE Votes SET vote_status = ?, starter = ?, time_start = ?
            WHERE id = ?
            ''', ('ongoing', starter, time_start, vote_id)
                )
    
   
    
# Функция возвращает ID голосования по ID варианта
def extract_vote_id(variant_id):
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT vote_id FROM Variants WHERE id = ?
            ''', (variant_id,)
                )
        result = cursor.fetchone()
            #print(answ)
        if result:
            vote_id, = result
            return(vote_id)
        else: return None

# Функция выясняет, за какой вариант в данном голосовании голосовал (лично) пользователь
# Возвращает ID варианта или None
def past_choise(member_id, vote_id):
    with Database(path_db) as cursor:
        cursor.execute('''
        SELECT id FROM Elections
        WHERE member_id = ? AND variant_id IN
        (SELECT id FROM Variants 
        WHERE vote_id = ?) AND status = 'valid'
            '''
            ,(member_id, vote_id)
            )
        result = cursor.fetchall()
        print(result)
        return result 
        
# Функция выдачи или отнятия права голоса участнику (присвоение статуса 'votist')
# Применялась при тестировании
def votist(member_id):
    with Database(path_db) as cursor:
        cursor.execute('''
        SELECT status FROM Status
        WHERE member_id = ? 
            '''
            ,(member_id,)
            )
        result = cursor.fetchall()
        print(result)
#     Если у участника нет статуса члена, лишаем его права голоса (если было)
        if ('member',) not in result:
            vot = False 
        else:
#        Если участник член и представитель - имеет право голоса
            if ('proxy',) in result:
                vot = True 
#         Если член не пресдатвитель, проверяем, есть ли у него представитель и
#         имеет ли этот представитель статус представителя
            else:
                cursor.execute(
            '''SELECT status FROM Status WHERE member_id IN
            (SELECT proxy FROM Members WHERE id = ?)
            ''',
            (member_id,)
            )
#           Если есть настоящий представитель, даем статус голосующего
                st_pr = cursor.fetchall()
                print('статус представителя: ', st_pr) 
                if ('proxy',) in st_pr:
                    vot = True 
#             Если представителя нет или он не настоящий - отбираем статус голсоующего
                else:
                    vot = False 
        if vot:
            cursor.execute(
            '''INSERT OR IGNORE INTO Status(member_id,status) VALUES(?,'votist')
            ''',
                       (member_id,)
            )
        else:
            cursor.execute(
            '''DELETE FROM Status WHERE member_id = ? AND status = "votist"''',
            (member_id,)
            )
        
# Функция подсчета голосов, отданых за вариант лично теми, кто имеет право голоса
def count_directly_votes(variant_id):
    with Database(path_db) as cursor:
        cursor.execute('''
           SELECT COUNT (*) FROM Members WHERE id IN
           (SELECT member_id FROM Elections WHERE variant_id = ? AND status = 'valid')
           AND id IN
           (SELECT member_id FROM  Status WHERE status  = 'votist')
           '''
            ,(variant_id, )
            )
        result = cursor.fetchone()
            #print(answ)
        if result:
            amount, = result
            return(int(amount))
        else: return None


# Функция подсчета голосов, отданых за вариант лично теми, кто не имеет право голоса
def count_directly_empty_votes(variant_id):
    with Database(path_db) as cursor:
        cursor.execute('''
           SELECT COUNT (*) FROM Members WHERE id IN
           (SELECT member_id FROM Elections WHERE variant_id = ? AND status = 'valid')
           AND id NOT IN
           (SELECT member_id FROM  Status WHERE status = 'votist')
           '''
            ,(variant_id, )
            )
        result = cursor.fetchone()
            #print(answ)
        if result:
            amount, = result
            return(int(amount))
        else: return None

# Функция подсчета голосов, отданых за вариант через представителей
def count_proxy_votes(variant_id):
    with Database(path_db) as cursor:
        cursor.execute('''
            SELECT COUNT (*) FROM Members WHERE proxy IN
            (SELECT member_id FROM Elections WHERE variant_id = ?
            AND status = 'valid') 
            AND id NOT IN            
            (SELECT member_id FROM Elections WHERE status = 'valid'
            AND variant_id IN
           (SELECT id FROM Variants WHERE Vote_id IN
           (SELECT vote_id FROM Variants WHERE id = ?)))
            AND id IN
            (SELECT member_id FROM  Status WHERE status  = 'votist')
      
            '''
            ,(variant_id,variant_id)
            )
        result = cursor.fetchone()
            #print(answ)
        if result:
            amount, = result
            return(int(amount))
        else: return None 
        
# Функция выбора варианта при голосовании
def election(member_id,variant_id):
    time_election = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vote_id = extract_vote_id(variant_id)
    old_elect = past_choise(member_id, vote_id)
    with Database(path_db) as cursor:
        cursor.execute(''' SELECT vote_status FROM Votes WHERE id = ?
            '''
            ,(vote_id,)
            )
        result = cursor.fetchone()
        print(result)
        vote_status, = result
        if vote_status == 'add_variants':
            answer = (False, 'Голосование ещё не началось')
        elif vote_status == 'closed':
            answer = (False, 'Голосование уже закончилось')
        elif vote_status == 'ongoing':
            cursor.execute(
            '''
          SELECT variant_status FROM Variants WHERE id = ?
            '''
            ,(variant_id,)
            )
            variant_status, = cursor.fetchone()
            if variant_status == 'loser':
                answer = (False, 'Этот вариант уже выбыл из голосования')
            else:
#            Делаем запись о голосовании в таблицу выборов     
                cursor.execute(
            '''
            INSERT INTO Elections(member_id, variant_id, time_election,status)
            VALUES (?,?,?,?)
            ''',(member_id, variant_id, time_election, 'valid')
            )
#             Меняем статус предыдущего выбора на 'invalid'
                if old_elect:
                    for item in old_elect:
                        cursor.execute(
            '''
            UPDATE Elections SET status = 'invalid' WHERE id = ?
            ''',(item[0],)
            )
                answer = (True, 'Ваш голос принят')
        else:
            answer = (False , 'Непонятен статус голосования')
    if 'votist' not in extract_status(member_id):
        str1 = answer[1]+'''\n Обращаем ваше внимание на то, что ваш голос не учитывается при подсчете.
Возможно, ваша личность не подтверждена регистратором.
Или вы не выбрали представителя.'''
        flag = answer[0]
        answer = (flag, str1)
    return answer



"""
Проверяем работу функций
"""
# c='tg_id','last_name'
#new_status(1,2,'not_status')
#print(extract_member_id(101))
#print(extract_user_id(24))
# print(extract_status(1))
# new_status(1,2,'registrator')
#new_vote(1, 2,'Важное голосование')
#cv = {'first_name':'Василий'}

#print(extract_user_id(101))
#print(extract_member_id(1,101))
# print(extract_user_data(3))
# print(all_status())
# print(list_of_registrators(1))
#print(list_of_votes(1,'bbbb'))
# print(new_variant(1,1,'за всё','cjdctv'))
# print('я работаю')
# print(path_db)
# trust(1,4)
# vote_start(3,1)
# print(past_choise(15,3))
# print(count_directly_votes(1))
# print(count_directly_empty_votes(4))
# print(count_proxy_votes(1))
# print(extract_status(102))
# print(election(102,1))
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
with open('names.txt',encoding="UTF-8") as f:
    stroka = f.read()
spisok = stroka.splitlines()

with Database(path_db) as cursor:
    for FIO in spisok:
        fam,im,otch = FIO.split(' ')
        tg_id = random.randint(100000,999999)
        tg_phone_number = random.randint(100000000,999999999)
        bithyear = random.randint(1928,2008)
        cursor.execute('''INSERT INTO Users
        (tg_id, tg_phone_number,tg_first_name,tg_last_name, first_name,middle_name,
        last_name,bithyear) VALUES (?,?,?,?,?,?,?,?)''',
        (tg_id,tg_phone_number,im,fam,im,otch,fam,bithyear))

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
        (i+6,
         random.randint(2,5),
         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
         )
                       )
            time.sleep(2)
            print( 'участник ', i+6, ' выбрал вариант ')


# Добавляем статус в голосования участников
with Database(path_db) as cursor:
    for i in range(105):
        variant_id = past_choise(i+1, 1)
        if variant_id:
            cursor.execute('''UPDATE Elections SET
        status = ?
        WHERE variant_id = ? AND  member_id = ?
        ''',
        ('valid',variant_id, i+1)
         )
            print( 'участник ', i+1, ' выбрал вариант ', variant_id)

# Присваиваем статус голосующего всем участникам группы, кто имеет право голосовать
for i in range(105):
    votist(i+1)
"""