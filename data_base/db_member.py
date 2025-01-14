# ФУНКЦИИ БАЗЫ ДАННЫХ ПО РАБОТЕ С УЧАСТНИКАМИ

import datetime

from db_func import *

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