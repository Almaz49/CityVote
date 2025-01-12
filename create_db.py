import sqlite3

# Открываем файл с SQL на чтение
with open("votebot.sql", "r") as file:
    db_sql = file.read()
    print(db_sql)
# Устанавливаем соединение с базой данных
    with sqlite3.connect('dbg1.db') as connection:
        cursor = connection.cursor()
# Исполняем SQL скрипт
        cursor.executescript(db_sql)






