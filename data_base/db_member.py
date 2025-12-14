# Модуль db_member
# ФУНКЦИИ БАЗЫ ДАННЫХ ПО РАБОТЕ С УЧАСТНИКАМИ
import datetime
import logging
import os
import aiosqlite
import pandas as pd
from data_base.db_func import AsyncDatabase, db_update, extract_member_id, extract_status, extract_user_id, get_member_lang, path_db, threshold_in_voices
from utils import log_function_call
from utils.utils import fetch_as_dict

# Настройка логирования
logger = logging.getLogger(__name__)


# Запись нового пользователя в базу данных из телеграм-бота
# (того, который первый раз им воспользовался)
@log_function_call
async def new_user_tg(tg_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                "INSERT OR IGNORE INTO Users(tg_id) VALUES(?)", (tg_id,)
            )
            logger.info(f"Добавлен новый пользователь с tg_id: {tg_id}")
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при добавлении нового пользователя: {e}")
            raise


# Запись нового участника в группу без присвоения статуса
@log_function_call
async def new_premember(club_id, user_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                "INSERT OR IGNORE INTO Members(club_id, user_id) VALUES(?, ?)",
                (club_id, user_id),
            )
            logger.info(
                f"Добавлен новый участник в группу {club_id} с user_id: {user_id}"
            )
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при добавлении нового участника: {e}")
            raise

# Функция выяснения статуса участника по tg_id.
# Если участник с таким телеграм id не обнаружен,
# заносит его в БД в таблицы Users и Members (в колонке club_id записывается id группы данного бота),
# без статуса (что равнозначно статусу user). Если пользователь обнаружен, но не является участником группы -
# он заносится в список участников группы, которую обслуживает телеграм-бот.
# Возвращает список статусов типа ['admin', 'registrator']

@log_function_call
async def extract_status_tg_id(club_id, tg_id):
    """
    Brief: Извлечение статуса участника по его tg_id
    :param club_id: id группы
    :param tg_id: id пользователя в телеграме
    :return: список статусов
    """
    logger.info(f"Проверка статуса участника по tg_id={tg_id}")
    user_id = await extract_user_id(tg_id)

    if not user_id:
        logger.info(f"Создание нового пользователя с tg_id={tg_id}")
        await new_user_tg(tg_id)
        user_id = await extract_user_id(tg_id)
        await new_premember(club_id, user_id)
        status = ["user"]
    else:
        member_id = await extract_member_id(club_id, user_id)

        if not member_id:
            logger.info(f"Добавление пользователя с tg_id={tg_id} в группу")
            await new_premember(club_id, user_id)
            status = ["user"]
        else:
            status = await extract_status(member_id)

    logger.info(f"Статус участника с tg_id={tg_id}: {status}")
    return status


# Запись нового статуса (registrator - member_id того, кто присвоил статус,
# member_id кому, какой статус, подтверждающий токен)
# Если переан статус в виде 'not_status', соответствующий статус удаляется
# status в данном случае - не список статусов, а один из статусов
# Если статус прислан в виде AppointAs_'status', то записывается 'status'.
# Если в другом - то записвается как прислан
@log_function_call
async def new_status(registrator, member_id, status, token_id=None):
    time_reg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    """
    Записывает новый статус пользователя.
    :param registrator: ID пользователя, который придал статус
    :param member_id: ID участника, которому придался статус
    :param status: Статус, который придался участнику
    :param token_id: ID токена, если он использовался
    :return: True, если запись прошла успешно, False - в противном случае, + текст сообщения
    """
    logger.info(
        f"Запись нового статуса: registrator={registrator}, member_id={member_id}, status={status}, token_id={token_id}, time_reg={time_reg}"
    )
    lang = await get_member_lang(registrator)
    data = {"lang": lang}
    async with AsyncDatabase(path_db) as cursor:
        try:
            # Делаем запись в таблице регистраций
            await cursor.execute(
                """INSERT INTO Registrations(registrator, object_type, object_id, status, token_id, time_reg)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (registrator, "member", member_id, status, token_id, time_reg),
            )

            # Проверяем, не удаляется ли статус (не начинается ли с 'not')
            status1 = status.split("_")
            if status1[0] == "not":
                status2 = status[4:]
                await cursor.execute(
                    """DELETE FROM Status WHERE member_id = ? AND status = ?""",
                    (member_id, status2),
                )
                logger.info(f"Статус '{status2}' удален для member_id: {member_id}")
                # Если удаляется стаус member, то удаляем все остальные статусы, кроме owner
                if status2 == "member":
                    await cursor.execute(
                        """DELETE FROM Status WHERE member_id = ? AND
                        status IN ('member', 'registrator','admin','superregistrator','pre-registrator','votist','delegate','proxy')""",
                        (member_id,),
                    )
                    logger.info(f"Статус 'member' удавлен для member_id: {member_id}")

                # Если удаляется стаус banned, то удаляем срок бана из таблицы Members
                if status2 == "banned":
                    await cursor.execute(
                        """UPDATE Members SET ban_expires_at = NULL WHERE member_id = ? """,
                        (member_id,),
                    )
                    logger.info(f"Статус 'owner' удавлен для member_id: {member_id}")
                success = True
                message = f"Статус '{status2}' удален для member_id: {member_id}"
                return success, message
            else:
                if status1[0] == "AppointAs":
                    new_st = status[10:]
                else:
                    new_st = status

                await cursor.execute(
                    """INSERT OR IGNORE INTO Status(member_id, status) VALUES (?, ?)""",
                    (member_id, new_st),
                )

                success = True
                message = f"Статус '{new_st}' добавлен для member_id: {member_id}"

                # Если присваевается статус member, удаляем статус candidate
                if new_st == "member":
                    await cursor.execute(
                        """DELETE FROM Status WHERE member_id = ? AND status = ?""",
                        (member_id, "candidate"),
                    )
                    logger.info(
                        f"Статус '{'candidate'}' удален для member_id: {member_id}"
                    )
                    # Проверяем, был ли уже у пользователя токен. Если да, то старому токену присваивается статус 'old'
                    await cursor.execute(
                        """SELECT token FROM Members WHERE id = ?""",
                        (member_id,),
                    )
                    result = await cursor.fetchone()
                    if result and result[0] is not None:
                        await cursor.execute(
                            """UPDATE Tokens SET status = ? WHERE id = ?""",
                            ("old", result[0]),
                        )

                    # Проверяем, были ли токены, привязанные к пользователю со статусом, отличающимся от "old" и присваиваем им статус "old"
                    await cursor.execute(
                        """
                        UPDATE Tokens SET status = 'old' WHERE member_id = ? AND status != 'old'
                        """, (member_id,)
                    )


                    # Записываем токен в таблицу Members
                    await cursor.execute(
                        """UPDATE Members SET token = ? WHERE id = ?""",
                        (token_id, member_id),
                    )
                    # Записываем member_id в таблицу Tokens
                    await cursor.execute(
                        """UPDATE Tokens SET member_id = ? WHERE id = ?""",
                        (member_id, token_id),
                    )
                    # Меняем токену статус на 'used'
                    await cursor.execute(
                            """UPDATE Tokens SET status = ? WHERE id = ?""",
                            ("used", token_id),
                        )
                # Если присваевается статус candidate, удаляем статус member
                if new_st == "candidate":
                    await cursor.execute(
                        """DELETE FROM Status WHERE member_id = ? AND status = ?""",
                        (member_id, "member"),
                    )
                    logger.info(
                        f"Статус '{'member'}' удален для member_id: {member_id}"
                    )
                logger.info(
                    f"Добавлен новый статус '{status}' для member_id: {member_id}"
                )
                return success, message

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе со статусом: {e}")
            raise


# Функция выбора представителя. Передается id участника, id выбранного им представителя.
# Производится запись id представителя в колонку proxy таблицы Members
# Производится запись в таблицу Trusts, фиксирующая делегирование голоса
@log_function_call
async def trust(member_id, proxy):
    time_trust = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(
        f"Запись доверия: member_id={member_id}, proxy={proxy}, time_trust={time_trust}"
    )
    lang = await get_member_lang(member_id)
    data = {"lang": lang}
    async with AsyncDatabase(path_db) as cursor:
        try:
            # Добавляем в строку члена запись о представителе в таблицу Members
            await cursor.execute(
                """
                UPDATE Members SET proxy = ? WHERE id = ?
                """,
                (proxy, member_id),
            )
            logger.info(f"Добавлена запись о представителе для member_id: {member_id}")

            # Проверяем, является ли участник членом группы и не имеет ли уже статус 'votist'
            await cursor.execute(
                """
                SELECT id FROM Status WHERE member_id = ? AND status = 'member'
                """,
                (member_id,),
            )
            result = await cursor.fetchone()

            if result:
                await cursor.execute(
                    """
                    INSERT OR IGNORE INTO Status (member_id, status) VALUES (?, ?)
                    """,
                    (member_id, "votist"),
                )
                logger.info(f"Добавлен статус 'votist' для member_id: {member_id}")

            # Добавляем запись в "журнал доверенностей" - таблицу Trusts
            await cursor.execute(
                """
                INSERT INTO Trusts (member_id, proxy_id, time_trust) VALUES (?, ?, ?)
                """,
                (member_id, proxy, time_trust),
            )
            logger.info(
                f"Добавлена запись в журнал доверенностей для member_id: {member_id}"
            )
            return "Представитель успешно назначен!"
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе с доверием: {e}")
            raise


@log_function_call
async def is_votist(member_id: int):
    """
    Проверка, является ли пользователь 'votist'
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            # Получаем все статусы пользователя
            await cursor.execute(
                "SELECT status FROM Status WHERE member_id = ?", (member_id,)
            )
            user_statuses = [tuple(row) for row in await cursor.fetchall()]
            has_member = ("member",) in user_statuses
            has_proxy = ("proxy",) in user_statuses
            has_votist = ("votist",) in user_statuses
            has_banned = ("banned",) in user_statuses
            has_frozen = ("frozen",) in user_statuses


            if not has_member:
                flag = False  # Не член клуба — не голосует
            elif has_banned:
                flag = False  # Забанен — не голосует
            elif has_frozen:
                flag = False  # Заморожен — не голосует
            elif has_proxy:
                flag = True  # Сам представитель — голосует
            else:
                # Проверяем, есть ли представитель со статусом 'proxy'
                await cursor.execute(
                    """
                    SELECT 1 FROM Status
                    WHERE member_id IN (
                        SELECT proxy FROM Members
                        WHERE id = ? AND proxy IS NOT NULL
                    ) AND status = 'proxy'
                """,
                    (member_id,),
                )
                has_proxy_parent = await cursor.fetchone()

                flag = bool(has_proxy_parent)  # Голосует через представителя

            # Обновляем статус 'votist', если нужно
            if flag != has_votist:
                response = "votist" if flag else "not_votist"
                await new_status(registrator=None, member_id=member_id, status=response)

            logger.info(
                f"Участник с member_id {member_id} имеет ли право голоса: {flag}"
            )
            return flag

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при определении права голоса: {e}")
            raise


# Функция выхода из группы. Передается id участника.
# Производится стирание всех статусов (что анаогично статусу user).
@log_function_call
async def member_leave_club(member_id, status):
    time_leave = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Запись выхода из группы member_id={member_id}")
    lang = await get_member_lang(member_id)
    data = {"lang": lang}
    # Если уходит владелец, оставляем за ним статус владельца
    if "owner" in status:
        status.remove("owner")

    # По очереди удаляем каждый статус
    for st in status:
        request = "not_" + st
        await new_status(member_id, member_id, request)

    async with AsyncDatabase(path_db) as cursor:
        try:
            # Делаем запись в таблице регистраций
            await cursor.execute(
                """INSERT INTO Registrations(registrator, object_type, object_id, status, time_reg)
                VALUES (?, ?, ?, ?, ?)""",
                (member_id, "member", member_id, "leave", time_leave),
            )
            logger.info(
                f"Добавлена запись в журнал регистраций о выходе для member_id: {member_id}"
            )
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
            logger.info(
                f"Пользователь {tg_id} помечен как недоступный. Причина: {reason}"
            )
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

            logger.debug(f"Результат запроса доступности  {result}")

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
                # Если пользователь не найден в базе данных, считаем его недоступным
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности пользователя {tg_id}: {e}")
            return False


# Функция записи в БД данных о пользователе при короткой регистрации (с запросом телефона)
@log_function_call
async def recording_user_data_1(
    tg_id: int,
    member_id: int,
    tg_phone_number=None,
    tg_first_name=None,
    tg_last_name=None,
    resume=None,
):
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
            raise


# Функция записи данных о пользователе в таблицу Users
@log_function_call
async def update_user_data(user_id: int, **data):
    """
    Записывает в БД данные пользователя.
    :param tg_id: ID пользователя в Telegram, данные его анкеты
    """

    try:
        await db_update("Users", "id", user_id, **data)
        logger.info(f"Данные {data} пользователя {user_id} записаны в базу данных.")
    except Exception as e:
        logger.error(f"Ошибка при записи данных пользователя {user_id}: {e}")
        raise


# Функция записи данных о пользователе в таблицу Members
@log_function_call
async def update_member_data(member_id: int, **data):
    """
    Записывает в БД данные пользователя.
    :param member_id: ID пользователя в Telegram, данные его анкеты
    """

    try:
        await db_update("Members", "id", member_id, **data)
        logger.info(f"Данные пользователя {member_id} записаны в базу данных.")
    except Exception as e:
        logger.error(f"Ошибка при записи данных пользователя {member_id}: {e}")
        raise


@log_function_call
async def is_appointed_delegate(member_id):
    """
    Проверяет, является ли пользователь с указанным member_id назначенным делегатом (delegate),
    учитывая, что статус не был удалён и registrator не равен None или 0.

    :param member_id: ID пользователя, которого нужно проверить.
    :return: True, если пользователь является назначенным делегатом, иначе False.
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            # Получаем все записи о назначении/удалении статуса delegate для данного member_id
            await cursor.execute(
                """
                SELECT status, registrator, time_reg
                FROM Registrations
                WHERE object_id = ? AND (status = 'delegate' OR status = 'not_delegate')
                AND (registrator IS NOT NULL AND registrator != 0 AND registrator != '')
                ORDER BY time_reg ASC
                """,
                (member_id,),
            )
            records = await cursor.fetchall()

            if not records:
                # Если записей нет, пользователь никогда не был делегатом
                logger.info(
                    f"Пользователь с member_id={member_id} никогда не был делегатом."
                )
                return False

            # Определяем последний статус
            last_status = None
            for record in records:
                status, registrator, time_reg = record
                if status == "delegate":
                    last_status = "delegate"
                elif status == "not_delegate":
                    last_status = "not_delegate"

            # Если последний статус - 'delegate', значит пользователь является текущим делегатом
            if last_status == "delegate":
                logger.info(
                    f"Пользователь с member_id={member_id} является назначенным делегатом."
                )
                return True
            else:
                logger.info(
                    f"Пользователь с member_id={member_id} не является назначенным делегатом."
                )
                return False

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при проверке статуса делегата: {e}")
            raise


@log_function_call
async def count_trust(club_id, member_id):
    """
    Подсчитывает число голосов, доверенных данному представителю
    :param club_id: ID группы
    :param memeber_id: ID участника
    :return: число голосов
    """
    async with AsyncDatabase(path_db) as cursor:
        # Подсчитывам количество участников группы, которые имеют данного участника представителем и чей статус member
        try:
            await cursor.execute(
                """
                SELECT COUNT(*) FROM Members WHERE club_id = ? AND proxy = ? AND
                id IN (SELECT member_id FROM Status WHERE status = 'member')
            """,
                (club_id, member_id),
            )
            result = await cursor.fetchone()
            if result:
                (amount_votes,) = result
            else:
                amount_votes = 0
            return amount_votes
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при подсчете голосов, доверенных представителю: {e}")
            raise


@log_function_call
async def is_delegate(club_id, member_id):
    """
    Выясняет, имеет ли право пользователь иметь статус `делегат` по количеству доверенных голосов
    или потому что его назначили делегатом
    :param club_id: ID группы
    :param memeber_id: ID участника
    :return: False or True
    """
    coefficient = (
        0.8  # Коэффициент, на который отличается порог потери статуса делегата
    )
    # от порога получения. Например, если делегатом становятся, получив 5 голосов,
    # то теряют этот статус, опустившись ниже чем 5 * coefficient голосов.

    threshold = await threshold_in_voices(club_id)
    trust_voice = await count_trust(club_id, member_id)
    if trust_voice >= threshold:
        logger.debug(
            f"Пользователь {member_id} имеет право быть делегатом по числу голосов"
        )
        return True
    status = await extract_status(member_id)
    if "delegate" in status and trust_voice >= threshold * coefficient:
        logger.debug(
            f"""Пользователь {member_id} имеет право быть делегатом,
                     потому что пока число его голосов не опустилось ниже порога потери статуса"""
        )
        return True
    appointed = await is_appointed_delegate(member_id)
    if appointed:
        logger.debug(
            f"""Пользователь {member_id} имеет право быть делегатом,
                     потому что он был назначен и не был лишен своего статуса"""
        )
        return True
    logger.debug(f"""Пользователь {member_id} не имеет право быть делегатом""")
    return False

@log_function_call
async def remove_status_votist_for_non_votist(club_id: int):
    """
    Проверка правильности статуса 'votist' для всех пользователей
    """
    async with AsyncDatabase(path_db) as cursor:
        # Удаляем статус 'votist' у тех, кто не имеет статус 'member'
        # и у тех, кто имеет статус 'banned' или 'frozen'
        query_delete = """
        DELETE FROM Status
        WHERE status = 'votist'
        AND member_id IN (
            SELECT Members.id
            FROM Members
            WHERE Members.club_id = ?
            AND Members.id NOT IN (
                SELECT Status.member_id
                FROM Status
                WHERE Status.status = 'member'
            )
            OR Members.id IN (
                SELECT Status.member_id
                FROM Status
                WHERE Status.status = 'banned' OR Status.status = 'frozen'
            )
        )
        """
        await cursor.execute(query_delete, (club_id,))


@log_function_call
async def extract_list_of_full_member_ids(club_id):
    async with AsyncDatabase(path_db) as cursor:
        # Получаем членов группы с актуальным статусом 'member'
        query_select = """
        SELECT
        Users.tg_id AS tg_id,
        Members.id AS member_id
        FROM Users
        INNER JOIN Members ON Users.id = Members.user_id
        WHERE Members.club_id = ?
          AND Members.id IN (
            SELECT Status.member_id
            FROM Status
            WHERE Status.status = 'member'
          )
        """
        await cursor.execute(query_select, (club_id,))
        result = await fetch_as_dict(cursor)
        logger.info(
            f"Найдено {len(result)} участников с правом голоса. Обновляем статус 'votist'"
        )
        return result

@log_function_call
async def check_token_expiration(member_id) -> tuple[bool, datetime.datetime]:
    """
    Проверяет, истек ли срок токена для пользователя с указанным member_id.
    Если истек - пользователю присваивается статус 'frozen', а токену - статус 'old'.
    Также у пользователя удаляется статус 'votist', если он есть.

    :param member_id: ID пользователя (member_id) для проверки.
    :return: None, срок токена, если срок токена истек, и , True, срок токена, если срок токена не истек.
    """
    now = datetime.datetime.now()
    three_days_ago = now - datetime.timedelta(days=3)
    async with AsyncDatabase(path_db) as cursor:
        query = """
        SELECT time_of_action, id FROM Tokens
        WHERE id IN
        (SELECT token FROM Members WHERE id = ?)
        """
        await cursor.execute(query, (member_id,))
        result = await cursor.fetchone()
        if result is None:
            logger.info("Токен не найден")
            await cursor.execute(
                "INSERT OR IGNORE INTO Status (member_id, status) VALUES (?, 'frozen')",(member_id,)
                        )
            await cursor.execute(
                "DELETE FROM Status WHERE member_id = ? AND status = 'votist'",(member_id,)
                        )
            return False, three_days_ago  # Прирваниваем отсутсвие токена к его просрочке
        expires_at, token_id = result
        expires_at_dt = datetime.datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
        if expires_at_dt < now:
            await cursor.execute(
                "UPDATE Tokens SET status = 'old' WHERE id = ?", (token_id,)
                )
            await cursor.execute(
                "INSERT OR IGNORE INTO Status (member_id, status) VALUES (?, 'frozen')",(member_id,)
                        )
            await cursor.execute(
                "DELETE FROM Status WHERE member_id = ? AND status = 'votist'",(member_id,)
                        )
            return False, expires_at_dt
        else:
            return True, expires_at_dt

@log_function_call
async def ban_member(member_id: int, admin: int, ban_time_days: int) -> None:
    """
    Функция бана пользователя.
    :param member_id: ID пользователя, которого нужно забанить
    :param admin: ID админа,
    :param ban_time_days: Время бана в днях.
    """

    now = datetime.datetime.now()
    reg_time = now.strftime("%Y-%m-%d %H:%M:%S")
    ban_expires_at = (now + datetime.timedelta(days=ban_time_days)).strftime("%Y-%m-%d %H:%M:%S")
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(
            "INSERT OR IGNORE INTO Status (member_id, status) VALUES (?, 'banned')",(member_id,)
                    )
        await cursor.execute(
            "UPDATE Members SET ban_expires_at = ? WHERE id = ?", (ban_expires_at, member_id)
        )
        await cursor.execute(
            """INSERT OR IGNORE INTO Registrations (object_type, object_id, registrator, status, time_reg)
            VALUES ('member', ?, ?, 'banned', ?)""",
            (member_id, admin, reg_time)
        )


async def check_ban_status(member_id):
    """
    Проверка бана пользователя.
    Если срок бана истек, то удаляется бан
    :param member_id: id пользователя
    :return: Дата бана, если бан сохраняется, False если срок бана истек или бан не найден

    """
    now = datetime.datetime.now()
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute("""
            SELECT ban_expires_at FROM Members
            WHERE id = ?
        """, (member_id,))
        result = await cursor.fetchone()
        if result is None:
            # На всякий случай удаляем статус бана, которого не должно быть
            await cursor.execute("""
                DELETE FROM Status
                WHERE member_id = ? AND status = 'banned'
            """, (member_id,))
            return False
        ban_expires_at = result[0]
        # Пытаемся распарсить дату окончания бана
        try:
            ban_expires_at_dt = datetime.datetime.strptime(ban_expires_at, "%Y-%m-%d %H:%M:%S")
            ban_expires_at_date = ban_expires_at_dt.date()
        except (ValueError, TypeError):
            # Если дата невалидна или отсутствует, считаем бан истекшим
            ban_expires_at_dt = None
        if ban_expires_at_dt is None or ban_expires_at_dt < now:
            await cursor.execute("""
                UPDATE Members SET ban_expires_at = NULL
                WHERE id = ?
            """, (member_id,))
            await cursor.execute("""
                DELETE FROM Status
                WHERE member_id = ? AND status = 'banned'
            """, (member_id,))
            await cursor.execute(
                """INSERT OR IGNORE INTO Registrations (object_type, object_id, status, time_reg)
                VALUES ('member', ?, 'unbanned', ?)""",
                (member_id, now)
        )

            return False
        else:
            return ban_expires_at_date


@log_function_call
async def check_ban_status_all_members(club_id: int):
    """
    Проверка бана у всех участников.
    Если срок бана истёк или отсутствует (NULL или пустая строка),
    удаляется статус 'banned', обнуляется ban_expires_at,
    и добавляется запись в таблицу 'Registrations' со статусом 'unbanned'.

    :param club_id: ID группы
    """
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    async with AsyncDatabase(path_db) as cursor:
        # Получаем всех участников группы
        await cursor.execute("""
            SELECT id, ban_expires_at FROM Members
            WHERE club_id = ?
        """, (club_id,))
        rows = await cursor.fetchall()

        if not rows:
            return False

        for row in rows:
            member_id = row[0]
            ban_expires_at = row[1]

            # Пытаемся распарсить дату окончания бана
            try:
                ban_expires_at_dt = datetime.datetime.strptime(ban_expires_at, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                # Если дата невалидна или отсутствует, считаем бан истекшим
                ban_expires_at_dt = None

            # Если бан истёк или невалиден
            if ban_expires_at_dt is None or ban_expires_at_dt < now:
                # Обнуляем срок бана
                await cursor.execute("""
                    UPDATE Members SET ban_expires_at = NULL
                    WHERE id = ?
                """, (member_id,))

                # Логируем разбан
                await cursor.execute(
                    """INSERT OR IGNORE INTO Registrations (object_type, object_id, status, time_reg)
                    VALUES ('member', ?, 'unbanned', ?)""",
                    (member_id, now_str)
                )

        # Удаляем статус 'banned' у всех, у кого истёк или отсутствует срок бана
        await cursor.execute("""
            DELETE FROM Status
            WHERE member_id IN (
                SELECT id
                FROM Members
                WHERE ban_expires_at IS NULL OR ban_expires_at = ''
            ) AND status = 'banned'
        """)

@log_function_call
async def export_list_of_members(
    club_id: int,
    status: str | list[str] = "all",
    filename: str = "members_export.xlsx"
    ):
    """
    Экспортирует список участников клуба в Excel-файл.

    :param club_id: ID клуба
    :param status: Статус участников (если указано "all", то выводятся все)
    :param filename: Имя файла для сохранения
    :return: Путь к файлу
    """
    if isinstance(status, str):
        if status != "all":
            status = [status]
    elif isinstance(status, list):
        pass
    else:
        raise ValueError("Параметр status должен быть строкой или списком строк")
    # Получаем список участников с дополнительным полем info_level из таблицы Members
    query = """
    SELECT
        Users.first_name,
        Users.last_name,
        Users.tg_id AS tg_id,
        Users.tg_first_name,
        Users.tg_last_name,
        Users.username,
        Users.id AS user_id,
        Members.id AS member_id,
        Members.resume,
        Members.description,
        Members.info_level,
        Tokens.lot,
        Tokens.number_in_lot,
        Tokens.token,
        Tokens.status AS token_status,
        Tokens.comment,
        Tokens.time_of_action
    FROM Members
    INNER JOIN Users ON Users.id = Members.user_id
    LEFT JOIN Tokens ON Tokens.id = Members.token
    WHERE Members.club_id = ?
    """
    params = (club_id,)
    # Подзапрос проверяет, есть ли у участника указанный статус в таблице Status
    if status != "all":
        placeholders = ", ".join("?" for _ in status)
        query += f"""
        AND Members.id IN (
            SELECT member_id
            FROM Status
            WHERE status IN ({placeholders})
        )
        """
        params += tuple(status)

    logger.info(f"Выполняется запрос: {query}")
    logger.info(f"Параметры для запроса: {params}")

    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            # Получаем названия колонок автоматически
            columns = [desc[0] for desc in cursor.description]

            logger.info("Запрос успешно выполнен.")
            df = pd.DataFrame(rows, columns=columns)

            # Сохраняем в Excel
            df.to_excel(filename, index=False)
            return os.path.abspath(filename)

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выполнении запроса: {e}")
            raise