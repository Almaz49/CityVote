# Модуль db_member
# ФУНКЦИИ БАЗЫ ДАННЫХ ПО РАБОТЕ С УЧАСТНИКАМИ
import datetime
from data_base.db_func import *
from utils import log_function_call
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Запись нового пользователя в базу данных из телеграм-бота
# (того, который первый раз им воспользовался)
@log_function_call
async def new_user_tg(tg_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                'INSERT OR IGNORE INTO Users(tg_id) VALUES(?)',
                (tg_id,)
            )
            logging.info(f"Добавлен новый пользователь с tg_id: {tg_id}")
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при добавлении нового пользователя: {e}")
            raise

# Запись нового участника в группу
@log_function_call
async def new_member(club_id, user_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                'INSERT OR IGNORE INTO Members(club_id, user_id) VALUES(?, ?)',
                (club_id, user_id)
            )
            logging.info(f"Добавлен новый участник в группу {club_id} с user_id: {user_id}")
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при добавлении нового участника: {e}")
            raise

# Запись нового статуса (registrator - member_id того, кто присвоил статус,
# member_id кому, какой статус, подтверждающий токен)
# Если переан статус в виде 'not_status', соответствующий статус удаляется
@log_function_call
async def new_status(registrator, member_id, status, token_id=None):
    time_reg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Запись нового статуса: registrator={registrator}, member_id={member_id}, status={status}, token_id={token_id}, time_reg={time_reg}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            # Делаем запись в таблице регистраций
            await cursor.execute(
                '''INSERT INTO Registrations(registrator, object_type, object_id, status, token_id, time_reg)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (registrator, 'member', member_id, status, token_id, time_reg)
            )

            # Проверяем, не удаляется ли статус (не начинается ли с 'not')
            status1 = status.split('_')
            if status1[0] == 'not':
                await cursor.execute(
                    '''DELETE FROM Status WHERE member_id = ? AND status = ?''',
                    (member_id, status1[1])
                )
                logging.info(f"Статус '{status1[1]}' удален для member_id: {member_id}")
            else:
                await cursor.execute(
                    '''INSERT OR IGNORE INTO Status(member_id, status) VALUES (?, ?)''',
                    (member_id, status)
                )
                logging.info(f"Добавлен новый статус '{status}' для member_id: {member_id}")
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при работе со статусом: {e}")
            raise


# Функция выбора представителя. Передается id участника, id выбранного им представителя.
# Производится запись id представителя в колонку proxy таблицы Members
# Производится запись в таблицу Trusts, фиксирующая делегирование голоса
@log_function_call
async def trust(member_id, proxy):
    time_trust = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Запись доверия: member_id={member_id}, proxy={proxy}, time_trust={time_trust}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            # Добавляем в строку члена запись о представителе в таблицу Members
            await cursor.execute(
                '''
                UPDATE Members SET proxy = ? WHERE id = ?
                ''', (proxy, member_id)
            )
            logging.info(f"Добавлена запись о представителе для member_id: {member_id}")

            # Проверяем, является ли участник членом группы и не имеет ли уже статус 'votist'
            await cursor.execute(
                '''
                SELECT id FROM Status WHERE member_id = ? AND status = 'member'
                ''', (member_id,)
            )
            result = await cursor.fetchone()

            if result:
                await cursor.execute(
                    '''
                    INSERT OR IGNORE INTO Status (member_id, status) VALUES (?, ?)
                    ''', (member_id, 'votist')
                )
                logging.info(f"Добавлен статус 'votist' для member_id: {member_id}")

            # Добавляем запись в "журнал доверенностей" - таблицу Trusts
            await cursor.execute(
                '''
                INSERT INTO Trusts (member_id, proxy_id, time_trust) VALUES (?, ?, ?)
                ''', (member_id, proxy, time_trust)
            )
            logging.info(f"Добавлена запись в журнал доверенностей для member_id: {member_id}")
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при работе с доверием: {e}")
            raise

# Функция проверяет, имеет ли пользователь право голоса и дает ему или отбирает статус 'votist' в зависимости от результата
@log_function_call
async def is_votist(member_id):
    async with Database(path_db) as cursor:
        try:
            await cursor.execute(
                'SELECT status FROM Status WHERE member_id = ?',
                (member_id,)
            )
            status = cursor.fetchall()
            votist = 'votist' in status #выявляем текущий статус
            if ('member',) in status:
                if ('proxy',) in status:
                    flag = True
                else:
                    await cursor.execute(
                        '''SELECT status FROM Status WHERE member_id in (
                        SELECT proxy FROM Members WHERE id = ?
                        )''',
                        (member_id,)
                    )
                    result = cursor.fetchall()
                    if ('proxy',) in result:
                        flag = True
                    else:
                        flag = False
            else:
                flag =  False
            if votist != flag: # Если статус надо поменять
                response = 'votist' if flag else 'not_votist'
                await new_status(registrator=None, member_id=member_id, status=response)

            logging.info(f"Участник с member_id {member_id} имеет ли право голоса: {flag}")
            return flag

        except aiosqlite.Error as e:
            logging.error(f"Ошибка при определении права голоса: {e}")
            raise