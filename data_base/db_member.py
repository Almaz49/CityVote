# Модуль db_member
# ФУНКЦИИ БАЗЫ ДАННЫХ ПО РАБОТЕ С УЧАСТНИКАМИ
import datetime
from data_base.db_func import *
from utils import log_function_call
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

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
            logger.info(f"Добавлен новый пользователь с tg_id: {tg_id}")
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при добавлении нового пользователя: {e}")
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
            logger.info(f"Добавлен новый участник в группу {club_id} с user_id: {user_id}")
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при добавлении нового участника: {e}")
            raise

# Запись нового статуса (registrator - member_id того, кто присвоил статус,
# member_id кому, какой статус, подтверждающий токен)
# Если переан статус в виде 'not_status', соответствующий статус удаляется
# status в данном случае - не список статусов, а один из статусов
# Если статус прислан в виде AppointAs_'status', то записывается 'status'.
# Если в другом - то записвается как прислан
@log_function_call
async def new_status(registrator, member_id, status, token_id=None):
    time_reg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Запись нового статуса: registrator={registrator}, member_id={member_id}, status={status}, token_id={token_id}, time_reg={time_reg}")

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
                status2 = status[4:]
                await cursor.execute(
                    '''DELETE FROM Status WHERE member_id = ? AND status = ?''',
                    (member_id, status2)
                )
                logger.info(f"Статус '{status2}' удален для member_id: {member_id}")
            else:
                if status1[0] == 'AppointAs':
                    new_st = status[10:]
                else:
                    new_st = status

                await cursor.execute(
                    '''INSERT OR IGNORE INTO Status(member_id, status) VALUES (?, ?)''',
                    (member_id, new_st)
                )
                # Если присваевается статус member, удаляем статус candidate
                if new_st == 'member':
                    await cursor.execute(
                    '''DELETE FROM Status WHERE member_id = ? AND status = ?''',
                    (member_id, 'candidate')
                )
                    logger.info(f"Статус '{'candidate'}' удален для member_id: {member_id}")
                # Если присваевается статус candidate, удаляем статус member
                if new_st == 'candidate':
                    await cursor.execute(
                    '''DELETE FROM Status WHERE member_id = ? AND status = ?''',
                    (member_id, 'member')
                )
                    logger.info(f"Статус '{'member'}' удален для member_id: {member_id}")
                logger.info(f"Добавлен новый статус '{status}' для member_id: {member_id}")

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе со статусом: {e}")
            raise


# Функция выбора представителя. Передается id участника, id выбранного им представителя.
# Производится запись id представителя в колонку proxy таблицы Members
# Производится запись в таблицу Trusts, фиксирующая делегирование голоса
@log_function_call
async def trust(member_id, proxy):
    time_trust = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Запись доверия: member_id={member_id}, proxy={proxy}, time_trust={time_trust}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            # Добавляем в строку члена запись о представителе в таблицу Members
            await cursor.execute(
                '''
                UPDATE Members SET proxy = ? WHERE id = ?
                ''', (proxy, member_id)
            )
            logger.info(f"Добавлена запись о представителе для member_id: {member_id}")

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
                logger.info(f"Добавлен статус 'votist' для member_id: {member_id}")

            # Добавляем запись в "журнал доверенностей" - таблицу Trusts
            await cursor.execute(
                '''
                INSERT INTO Trusts (member_id, proxy_id, time_trust) VALUES (?, ?, ?)
                ''', (member_id, proxy, time_trust)
            )
            logger.info(f"Добавлена запись в журнал доверенностей для member_id: {member_id}")
            return "Представитель успешно назначен!"
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе с доверием: {e}")
            raise

# Функция проверяет, имеет ли пользователь право голоса и дает ему или отбирает статус 'votist' в зависимости от результата
@log_function_call
async def is_votist(member_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                'SELECT status FROM Status WHERE member_id = ?',
                (member_id,)
            )
            status = await cursor.fetchall()
            votist = ('votist',) in status #выявляем текущий статус
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
                    result = await cursor.fetchall()
                    if ('proxy',) in result:
                        flag = True
                    else:
                        flag = False
            else:
                flag =  False
            if votist != flag: # Если статус надо поменять
                response = 'votist' if flag else 'not_votist'
                await new_status(registrator=None, member_id=member_id, status=response)

            logger.info(f"Участник с member_id {member_id} имеет ли право голоса: {flag}")
            return flag

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при определении права голоса: {e}")
            raise


# Функция выхода из группы. Передается id участника.
# Производится стирание всех статусов (что анаогично статусу user).
@log_function_call
async def member_leave_club (member_id,status):
    time_leave = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Запись выхода из группы member_id={member_id}")
    # Если уходит владелец, оставляем за ним статус владельца
    if 'owner' in status:
        status.remove('owner')

    # По очереди удаляем каждый статус
    for st in status:
        request = 'not_'+st
        await new_status(member_id,member_id,request)



    async with AsyncDatabase(path_db) as cursor:
        try:
             # Делаем запись в таблице регистраций
            await cursor.execute(
                '''INSERT INTO Registrations(registrator, object_type, object_id, status, time_reg)
                VALUES (?, ?, ?, ?, ?)''',
                (member_id, 'member', member_id, 'leave', time_leave)
            )
            logger.info(f"Добавлена запись в журнал регистраций о выходе для member_id: {member_id}")
            return "Участник выбыл"
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе с доверием: {e}")
            raise

@log_function_call
async def mark_user_as_unavailable(tg_id: int, reason: str):
    """
    Помечает пользователя как недоступного.
    :param tg_id: ID пользователя в Telegram
    :param reason: Причина недоступности (например, "Бот заблокирован")
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            query = """
            UPDATE Users
            SET tg_available = ?
            WHERE tg_id = ?;
            """
            await cursor.execute(query, (reason, tg_id))
            logger.info(f"Пользователь {tg_id} помечен как недоступный. Причина: {reason}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса пользователя {tg_id}: {e}")

@log_function_call
async def mark_user_as_available(tg_id: int):
    """
    Помечает пользователя как доступного.
    :param tg_id: ID пользователя в Telegram
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            query = """
            UPDATE Users
            SET tg_available = NULL
            WHERE tg_id = ?;
            """
            await cursor.execute(query, (tg_id,))
            logger.info(f"Пользователь {tg_id} помечен как доступный.")
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса пользователя {tg_id}: {e}")

@log_function_call
async def is_user_available(tg_id: int) -> bool:
    """
    Проверяет, доступен ли пользователь.
    :param tg_id: ID пользователя в Telegram
    :return: True, если пользователь доступен; False, если недоступен.
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            query = """
            SELECT tg_available
            FROM Users
            WHERE tg_id = ?;
            """
            await cursor.execute(query, (tg_id,))
            result = await cursor.fetchone()

            logger.debug (f'Результат запроса доступности  {result}')

            if result is not None:
                if not result[0]:
                    # Если tg_available == NULL, пользователь доступен
                    logger.info(f"Пользователь {tg_id} доступен.")
                    return True
                else:
                    # Если tg_available содержит значение, пользователь недоступен
                    logger.info(f"Пользователь {tg_id} недоступен.")
                    return False
            else:
                #Если пользователь не найден в базе данных, считаем его недоступным
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности пользователя {tg_id}: {e}")
            return False

# Функция записи в БД данных о пользователе при короткой регистрации (с запросом телефона)
@log_function_call
async def recording_user_data_1(tg_id: int, member_id: int, tg_phone_number = None,
                                tg_first_name = None, tg_last_name = None, resume = None):
    """
    Записывает в БД данные пользователя при регистрации.
    :param tg_id: ID пользователя в Telegram, данные его анкеты
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            query = """
            UPDATE Users
            SET
            tg_phone_number = ?,
            tg_first_name = ?,
            tg_last_name = ?
            WHERE tg_id = ?;
            """
            params = (tg_phone_number, tg_first_name, tg_last_name, tg_id)
            await cursor.execute(query, params)

            query = """
            UPDATE Members
            SET
            resume = ?
            WHERE id = ?;
            """
            params = (resume, member_id)
            await cursor.execute(query, params)

            logger.info(f"Данные пользователя {tg_id} записаны в базу данных.")
        except Exception as e:
            logger.error(f"Ошибка при записи данных пользователя {tg_id}: {e}")

# Функция записи данных о пользователе в таблицу Users
@log_function_call
async def recording_user_data(tg_id: int, **data):

    """
    Записывает в БД данные пользователя.
    :param tg_id: ID пользователя в Telegram, данные его анкеты
    """

    try:
        await db_update('Users', 'tg_id', tg_id, **data)
        logger.info(f"Данные пользователя {tg_id} записаны в базу данных.")
    except Exception as e:
        logger.error(f"Ошибка при записи данных пользователя {tg_id}: {e}")



# Функция записи данных о пользователе в таблицу Members
@log_function_call
async def recording_member_data(member_id: int, **data):

    """
    Записывает в БД данные пользователя.
    :param member_id: ID пользователя в Telegram, данные его анкеты
    """

    try:
        await db_update('Members', 'id', member_id, **data)
        logger.info(f"Данные пользователя {member_id} записаны в базу данных.")
    except Exception as e:
        logger.error(f"Ошибка при записи данных пользователя {member_id}: {e}")