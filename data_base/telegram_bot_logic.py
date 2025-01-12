import sqlite3
from config_data.config import Config, load_config
if __name__ == '__main__':
    from data_base import *
else:
    from data_base.data_base import *
"""
ЛОГИКА ТЕЛЕГРАМ БОТА
Здесь логика взаимодействия телеграм-бота с базой данных.
Все запросы с tg_id приходят сюда. Отсюда в data_base уходят запросы с member_id
"""

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
path_db = config.db.path_db #путь к базе данных
club_id = config.tg_bot.club_id # id группы в БД (не телеграм)



#Функция выяснения статуса участника по tg_id. Если участник с таким телеграм id не обнаружен,
# заносит его в БД в таблицы Users и Members (в колонкe club_id записывается id группы данного бота),
#без статуса (что равнозначно статусю user). Если пользователь обнаружен, но не является участником группы -
# он заносится в список участников группы, которую облуживает телеграм-бот.
#Возвращает список кортежей типа [(admin,),(registrator,)]
# В каждом кортеже только один элемент. Кортежей столько, сколько статусов у участника.
# Функция используется в фильтрах для хендлеров

def status_member(tg_id):
# Извлекаем ID льзователя из БД по его телеграм ID
    user_id = extract_user_id(tg_id)
# Если пользовтеля с таким телеграм ID нет, создаем его.
# А также добавляем такого участника в группу.
# Записываем, что его статус в группе "пользователь", что означает отсутствие статуса
    if not user_id:
        new_user_tg(tg_id)
        new_user_id = extract_user_id(tg_id)
        new_member(club_id,new_user_id)
        status = ['user']
    else:
# Извлекаем ИД участника группы
        member_id = extract_member_id(club_id, user_id)
# Если нет такого пользователя в группе, записываем его, опять с "нулевым статусом"
        if not member_id:
            new_member(club_id,user_id)
            status = ['user']
        else:
            status = extract_status(member_id)
    return(status)
    
  

 #Функци извлечения данных о пользователе по его tg_id
# *c - список (точнее кортеж) колонок, из которых извлекатся данные.
# При отсутсивии *c извлекаются все данные.
def extract_user_data_tg(tg_id,*c):
    user_id = extract_user_id(tg_id)
#     print(user_id)
    if user_id:
        return extract_user_data(user_id,*c)
    
# Функция извлечения member_id по tg_id    
def member_id_tg(tg_id):
    user_id = extract_user_id(tg_id)
    if user_id:
        return(extract_member_id(club_id,user_id))

 #Функци извлечения данных о пользователе по его tg_id
# Используется при создании нового администратора
# Вщзвращает (flag, ans_str). Если flag == true, значит участник может быть
# назначен регистратором.
# ans_str - комментарий который выдается по итогу извлечения данных
def extract_new_registrator_data(tg_id):
    user_id = extract_user_id(tg_id)
    member_id = extract_member_id(club_id, user_id)
#     Если участника с таким tg_id нет, завершаем работу функции и сообщаем
    if not member_id:
        flag = False
        ans_str = 'Нет такого участника. Попробуйте снова'
        return(flag,ans_str)
#     Если такой участник есть, извлекаем его данные
    user_data = extract_user_data_tg(tg_id,'id', 'tg_first_name',
                         'tg_last_name', 'tg_phone_number')
    ans_str = f'Имя: {user_data[1]}, Фамилия: {user_data[2]},\n Телефон: {user_data[3]}'
#     print(ans_str)
    status =  extract_status(member_id)
    if status: # если у пользователя есть хоть какой-то статус
        if ('registrator',) in status: #если пользователь уже регистратор
            flag = False
            ans_str += '\nЭтот участник уже регистратор'
        else:
            flag = True
    else: #если пользователь подал заявку но еще не зарегистрирован как участник группы
        flag = False
        ans_str += '\nЭтот участник еще не зарегистрирован в группе'

    


#Присвоение нового статуса - в качестве аргументов функции tg_id регистратора и
    #участника группы
def new_status_tg(registrator_tg_id, member_tg_id, status, token_id=None):
    ans_str = ''
    registrator_user_id = extract_user_id(registrator_tg_id)
    registrator = extract_member_id(club_id, registrator_user_id)
    if not registrator:
        ans_str +='Нет такого регистратора.'
    user_id = extract_user_id(member_tg_id)
    member_id = extract_member_id(club_id, user_id)
    if not member_id:
        ans_str +='Нет такого участника'
        return(ans_str)
    new_status(registrator,member_id,status,token_id)
    if ans_str:
        return(ans_str)

# Создание нового голосования    
def new_vote_tg(creator_tg_id, title, text = None, vote_type = 'usual',
                vote_status = 'add_variants', link_id = None):
    creator_user_id = extract_user_id(creator_tg_id)
    creator = extract_member_id(club_id, creator_user_id)
    new_vote(club_id, creator, title, text = text, vote_type = vote_type,
             vote_status = vote_status, link_id = link_id)

# Создание варианта для голосования. Добавляется в голосования со статусом ожидания вариантов.
# В БД вносится автор, заголовок варианта, текст варианта, если есть и мб - ссылка
def new_variant_tg(vote_id, tg_id, title, text = None, link_id = None):
    user_id = extract_user_id(tg_id)
    author = extract_member_id(club_id, user_id)
    new_variant(vote_id, author, title, text, link_id)
    

# Извлечение статусов участника группы (отдает список статусов)
def extract_status_tg(tg_id):
    user_id = extract_user_id(tg_id)
    if not user_id: return(None)
    member_id = extract_member_id(club_id,user_id)
    if not member_id: return(None)
    status = extract_status(member_id)
    return(status)

# Функция извлечения списка идущих голосований
def list_of_votes_tg(*vote_status):
    return(list_of_votes(club_id,*vote_status))

#Функция извлечения списка регистраторов
def list_of_registrators_tg():
    return(list_of_registrators(club_id))


#Функция извлечения списка представителей
def list_of_proxy_tg():
    return(list_of_proxy(club_id))

#Функция извлечения списка регистраторов
def list_of_delegates_tg():
    return(list_of_delegates(club_id))




"""
Проверяем работу функций
"""
#print(new_status_tg(101,103,'not_status'))
#print(extract_member_id(1,101))
#print(extract_user_id(101))
#print(extract_new_registrator_data(101))
#new_status_tg(101,103,'status')
#new_vote_tg(1,101,'Очень важное голосование')
#print(extract_user_data_tg(101))
# print(status_member(12345))
# print(extract_status_tg(12345))


