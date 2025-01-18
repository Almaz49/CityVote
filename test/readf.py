import sqlite3
import random

with open('names.txt',encoding="UTF-8") as f:
    stroka = f.read()
print(stroka)
spisok = stroka.splitlines()
print(spisok)
i = 1
for FIO in spisok:
    i = i+1
    fam,im,otch = FIO.split(' ')
    print(fam, im)
    tg_id = random.randint(1,1000000000)
    phone = random.randint(100000000,999999999)
    birth = random.randint(1935,2009)
    with sqlite3.connect('dbg1.db') as connection:
        cursor = connection.cursor()
        cursor.execute('''INSERT OR IGNORE INTO Users
    (tg_id, tg_phone_number, tg_first_name, tg_last_name, first_name, middle_name, last_name, birth_year)
            VALUES(?,?,?,?,?,?,?,?)''',
            (tg_id, phone, im, fam, im, otch, fam, birth))
        cursor.execute('INSERT OR IGNORE INTO Members (user_id,club_id) VALUES (?,?)', (i,1))
