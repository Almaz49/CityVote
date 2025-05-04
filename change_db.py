import sqlite3
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("db_migration.log"),  # Лог в файл
        logging.StreamHandler()  # Лог в консоль
    ]
)

def main():
    sql_file = "change.sql"
    db_path = "dbg1.db"

    try:
        # Проверяем существование файла
        if not os.path.exists(sql_file):
            logging.error(f"Файл {sql_file} не найден")
            return

        # Читаем SQL-скрипт
        logging.info(f"Чтение файла: {sql_file}")
        with open(sql_file, "r", encoding="utf-8") as file:
            sql_script = file.read()

        # Подключаемся к БД
        logging.info(f"Подключение к базе данных: {db_path}")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            try:
                # Выполняем скрипт
                logging.info("Выполнение SQL-скрипта...")
                cursor.executescript(sql_script)
                conn.commit()
                logging.info("SQL-скрипт успешно выполнен")

                # Удаляем файл при успехе
                os.remove(sql_file)
                logging.info(f"Файл {sql_file} удален")

            except sqlite3.Error as e:
                logging.error(f"Ошибка выполнения SQL: {e}")
                conn.rollback()
                raise  # Пробрасываем ошибку дальше

    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        raise  # Можно убрать, если не нужно прерывать выполнение при ошибке

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.error("Выполнение прервано из-за ошибок")
