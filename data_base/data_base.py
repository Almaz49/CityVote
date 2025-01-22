import random
import time


if __name__ == '__main__':
    from db_member import *
    from db_vote import *
else:
    from data_base.db_member import *
    from data_base.db_vote import *


# БАЗА ДАННЫХ
# Первоначальный файл разбит на три, которые импортируются сюда.
# db_func - файл с функциями, которые используются другими функциями
# В частности, класс для работы с БД
# db_memder - функции работы с участниками
# db_vote - функции работы с голосованиями
# Здесь функции взаимодействия с БД исходя из user_id и member_id пользователей.
# Функции универсальны независимо от платформы.
# Специфика телеграм-бота вынесена в telegram_bot_logic.
# То есть, телеграм-бот взаимодействует с БД и data_base только через telegram_bot_logic (пока это не так, но надо стремиться наверно)
# А data_base ничего "не знает" о телеграм-боте



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



# # Присваиваем статус голосующего всем участникам группы, кто имеет право голосовать
# for i in range(101):
#     votist(i+1)
