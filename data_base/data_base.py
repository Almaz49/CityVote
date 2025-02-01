import random
import time
from data_base.db_member import *
from data_base.db_vote import *
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Функция выдачи или отнятия права голоса участнику (присвоение статуса 'votist')
async def votist(member_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT status FROM Status
                WHERE member_id = ?
            ''', (member_id,))
            result = await cursor.fetchall()
            logging.info(f"Проверка статусов для member_id={member_id}: {result}")

            # Если у участника нет статуса члена, лишаем его права голоса (если было)
            if ('member',) not in result:
                vot = False
            else:
                # Если участник член и представитель - имеет право голоса
                if ('proxy',) in result:
                    vot = True
                else:
                    # Если член не представитель, проверяем, есть ли у него представитель
                    # и имеет ли этот представитель статус представителя
                    await cursor.execute('''
                        SELECT status FROM Status WHERE member_id IN
                        (SELECT proxy FROM Members WHERE id = ?)
                    ''', (member_id,))
                    st_pr = await cursor.fetchall()
                    logging.info(f"Статус представителя для member_id={member_id}: {st_pr}")
                    if ('proxy',) in st_pr:
                        vot = True
                    else:
                        vot = False

            if vot:
                await cursor.execute('''
                    INSERT OR IGNORE INTO Status(member_id, status) VALUES (?, 'votist')
                ''', (member_id,))
                logging.info(f"Присвоен статус 'votist' для member_id={member_id}")
            else:
                await cursor.execute('''
                    DELETE FROM Status WHERE member_id = ? AND status = 'votist'
                ''', (member_id,))
                logging.info(f"Отобран статус 'votist' для member_id={member_id}")

        except aiosqlite.Error as e:
            logging.error(f"Ошибка при работе с правом голоса: {e}")
            raise



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
