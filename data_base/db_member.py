# ФУНКЦИИ БАЗЫ ДАННЫХ ПО РАБОТЕ С УЧАСТНИКАМИ

import datetime
import os

from data_base.db_func import *


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
            '''INSERT INTO Registrations(registrator, object_type, object_id,
            status,token_id,time_reg)
            VALUES (?,?,?,?,?,?)''',(registrator,'member',member_id,status,token_id,time_reg)
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
        # Добавляем в строку члена запись о представителе в таблицу Members
        cursor.execute(
            '''
            UPDATE Members SET proxy = ? WHERE id = ?
            ''', (proxy,member_id)
                )

        # Добавляем статус 'votist' члену (если он член группы и не имел этого статуса)
        cursor.execute(
            '''
         SELECT id FROM Status WHERE member_id = ? AND status = 'member'
            ''', (member_id,)
                )
        result = cursor.fetchone()
        print(result)
        if result:
            cursor.execute(
            '''
          INSERT OR IGNORE INTO Status (member_id, status) VALUES (?,?)
            ''',(member_id, 'votist')
            )

        # Добавляем запись в "журнал доверенностей" - таблицу Trusts
        cursor.execute(
            '''
          INSERT INTO Trusts (member_id, proxy_id, time_trust) VALUES (?,?,?)
            ''',(member_id, proxy, time_trust)
            )





#       //////////////////////////////////////
#           Проверяем работу функций
#       \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

# print('losers: ', vote_final(3))
# print(vote_finish(3))


# c='tg_id','last_name'
#new_status(1,2,'not_status')
#print(extract_member_id(101))
#print(extract_user_id(24))
# print(extract_status(1))
# new_status(1,2,'registrator')
#new_vote(1, 2,'Важное голосование')
#cv = {'first_name':'Василий'}

# print(extract_user_id(101))
#print(extract_member_id(1,101))
# print(extract_user_data(3))
# print(all_status())
# print(list_of_registrators(1))
# print(list_of_members(1,'proxy'))
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




"""