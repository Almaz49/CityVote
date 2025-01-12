"""
Этот файл создает начальные настройки - добавляет в базу данных группы с указанными номерами и телеграм-id админов группы
"""

import sqlite3
from config_data.config import Config, load_config


# Загружаем конфиг в переменную config
config: Config = load_config('.env')
path_db = config.db.path_db #путь к базе данных
admin_ids = config.tg_bot.admin_ids # список tg_id админов бота
club_id = config.tg_bot.club_id # id группы в БД (не телеграм)
print(f'Путь к дб: {path_db},\n Админы: {admin_ids},\n Группа: {club_id}')
print(config)

with sqlite3.connect(path_db) as connection:
    cursor = connection.cursor()
    # Делаю из списка tg_id админов список user_id админов
    adm_ids = []
    for item in admin_ids:
        print(item)
        cursor.execute('INSERT OR IGNORE INTO Users(tg_id) VALUES(?)', (item,)) #записываем админа в таблицу Users, если еще не записан
        cursor.execute('SELECT id FROM Users WHERE tg_id = ?', (item,))  # Извлекаем его id
        adm, = cursor.fetchone()
        print('admin_id = ',adm)
        adm_ids.append(adm) # Добавляем id в список
    print(adm_ids)

with sqlite3.connect(path_db) as connection:
    cursor = connection.cursor()
    for ad in adm_ids:
        print('id админа',ad)
        cursor.execute('INSERT OR IGNORE INTO Members(user_id, club_id) VALUES(?,?)', (ad, club_id)) #Добвляем админов в список участников группы, если еще не добавлены
        cursor.execute('SELECT id FROM Members WHERE user_id = ? AND club_id = ?', (ad, club_id)) # извлекаем memder_id админа
        m_id, =  cursor.fetchone()
        cursor.execute('INSERT OR IGNORE INTO Status(member_id, status) VALUES(?,?)', (m_id,'admin')) #присваем статус админа в соотвествующей группе

"""
Надо сделать обраотку если запрос выдал None
"""