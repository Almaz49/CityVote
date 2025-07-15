# db_token_service.py
import datetime
import pandas as pd
import os
import secrets
from data_base.db_func import AsyncDatabase, path_db
from typing import List, Optional
from collections import defaultdict
# Логирование (замените на ваш логгер)
import logging

from data_base.db_member import new_status
from utils.utils import log_function_call
logger = logging.getLogger(__name__)

@log_function_call
def generate_numeric_token(length=9):
    return ''.join(secrets.choice('0123456789') for _ in range(length))

@log_function_call
async def is_token_unique(cursor, token: str) -> bool:
    await cursor.execute(
        "SELECT 1 FROM Tokens WHERE token = ?",
        (token,)
    )
    result = await cursor.fetchone()
    return result is None

@log_function_call
def format_token(token: str) -> str:
    """
    Форматирует токен с разделителями: XX-XXX-XXX-XXX
    Например: 123456789012 → 12-345-678-901-2
    """
    token = token[::-1]  # Обратный порядок
    chunks = []
    for i in range(0, len(token), 3):
        chunk = token[i:i+3][::-1]
        chunks.append(chunk)
    return "-".join(chunks[::-1])


@log_function_call
async def get_token_attempts_count(member_id: int) -> int:
    """
    Возвращает число попыток ввода токена за последние 24 часа.

    :param tg_id: Telegram ID пользователя.
    :param club_id: ID группы.
    :return: Число попыток.
    """
    twenty_four_hours_ago = (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(
            """
            SELECT COUNT(*) FROM TokenAttempts
            WHERE member_id = ? AND attempt_time > ?
            """,
            (member_id, twenty_four_hours_ago)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

@log_function_call
async def add_token_attempt(member_id: int) -> None:
    """
    Добавляет запись о попытке ввода токена.

    :param tg_id: Telegram ID пользователя.
    """
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(
            "INSERT INTO TokenAttempts (member_id) VALUES (?)",
            (member_id,)
        )

@log_function_call
async def clear_old_attempts(member_id: int) -> None:
    """
    Удаляет попытки ввода токена старше 24 часов.

    :param tg_id: Telegram ID пользователя.
    :param club_id: ID группы.
    """
    twenty_four_hours_ago = (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(
            """
            DELETE FROM TokenAttempts
            WHERE member_id = ? AND attempt_time < ?
            """,
            (member_id, twenty_four_hours_ago)
        )

@log_function_call
async def auto_approve_by_token(member_id: int, token_id: int) -> tuple[bool, str]:
    """
    Привязывает токен к пользователю и автоматически регистрирует его как member.

    :param member_id: ID пользователя.
    :param token_id: ID валидного токена.
    :return: (success, message)
    """

    try:
        async with AsyncDatabase(path_db) as cursor:
            # Обновляем статус токена
            await cursor.execute(
                "UPDATE Tokens SET status = 'used' WHERE id = ?", (token_id,)
            )


        # Обновляем статус пользователя на 'member'
        _, msg = await new_status(registrator=None, member_id=member_id, status="member", token_id=token_id)

        if not _:
            return False, f"Не удалось обновить статус: {msg}"

        async with AsyncDatabase(path_db) as cursor:
            # Удаляем статус 'frozen' у пользователя, если был
            await cursor.execute(
                """
                DELETE FROM Status
                WHERE member_id = ?
                AND status = 'frozen'
                """,
                (member_id,)
            )




        return True, "Автоматическая регистрация успешна"
    except Exception as e:
        logger.error(f"Ошибка при автоматической регистрации: {e}")
        return False, f"Ошибка: {e}"

@log_function_call
async def is_valid_token(token: str, club_id: int):
    """
    Проверяет, валиден ли токен для указанной группы.

    :param token: Токен для проверки (строка).
    :param club_id: ID группы, для которой нужно проверить токен.
    :return: словарь {'token_id': ID токена, 'status': статус токена } или None, если токен не найден.
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                """
                SELECT id, status, validity, time_of_action FROM Tokens
                WHERE token = ? AND club_id = ?
                """,
                (token, club_id)
            )
            row = await cursor.fetchone()
            if not row:
                return None  # Токен не найден

            token_id, status, validity, time_of_action = row
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if status == 'valid':
                if validity and validity < now:
                    # Обновляем статус токена на 'old'
                    await cursor.execute(
                        "UPDATE Tokens SET status = 'old' WHERE id = ?", (token_id,)
                    )
                    return {'token_id': token_id, 'status': 'old'}
                else:
                    return {'token_id': token_id, 'status': 'valid'}  # Токен еще валиден и не использован
            elif status == 'used':
                if time_of_action and time_of_action < now:
                    # Обновляем статус токена на 'old'
                    await cursor.execute(
                        "UPDATE Tokens SET status = 'old' WHERE id = ?", (token_id,)
                    )
                    return {'token_id': token_id, 'status': 'old'}  # Токен уже устарел
                else:
                    return {'token_id': token_id, 'status': 'used'}  # Токен уже использован но еще не устарел
            elif status == 'old':
                return {'token_id': token_id, 'status': 'old'}  # Токен устарел
            else:
                logger.error(f"Неизвестный статус токен: {status}")
                return None


        except Exception as e:
            logger.error(f"Ошибка при проверке токена: {e}")
            return None

@log_function_call
async def create_tokens_for_lot(
    club_id: int,
    lot: Optional[int] = None,
    count: int = 100,
    token_length: int = 9,
    validity_days: int = 30,
    time_of_action_months: int = 12,
    creator_id: Optional[int] = None,
    comment: str = ""  # Добавлен параметр
) -> dict:
    """
    Создаёт указанное количество токенов для заданного лота или следующего свободного номера.
    :param club_id: ID клуба
    :param lot: Номер лота (если None — будет найден первый доступный)
    :param count: Количество токенов
    :param token_length: Длина токена
    :param validity_days: Срок действия в днях
    :param time_of_action_months: Срок действия действия по токену
    :param creator_id: Кто создал токен (ID пользователя)
    :param comment: Комментарий к токенам этого лота
    :return: {'tokens': {ключ - номер тоена в лоте, значение - токен}, 'lot': ...}
    """
    if not comment.strip():
        raise ValueError("Комментарий обязателен при создании токенов")

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    validity = (
        datetime.datetime.now() + datetime.timedelta(days=validity_days)
    ).strftime("%Y-%m-%d %H:%M:%S")
    time_of_action = (
        datetime.datetime.now() + datetime.timedelta(days=time_of_action_months*30.44)
    ).strftime("%Y-%m-%d %H:%M:%S")
    tokens = []
    async with AsyncDatabase(path_db) as cursor:
        # Если номер лота не указан — найти первый доступный
        if lot is None:
            await cursor.execute("""
                SELECT DISTINCT lot FROM Tokens WHERE club_id = ?
            """, (club_id,))
            rows = await cursor.fetchall()
            existing_lots = set(row[0] for row in rows)
            next_lot = 1
            while next_lot in existing_lots:
                next_lot += 1
            lot = next_lot
            max_number_in_lot = 1
        else:
            await cursor.execute("""
                SELECT number_in_lot FROM Tokens WHERE club_id = ? AND lot = ?
            """, (club_id, lot))
            result = await cursor.fetchall()
            max_number_in_lot = max([row[0] for row in result]) + 1 if result else 1

        tokens = {} # Словарь для хранения токенов  (ключ - номер в лоте, значение - токен)

        for i in range(max_number_in_lot, count + max_number_in_lot):
            attempts = 0
            while attempts < 100:
                token = generate_numeric_token(token_length)
                if await is_token_unique(cursor, token):
                    break
                attempts += 1
            else:
                raise RuntimeError(f"Не удалось сгенерировать уникальный токен для {i}-го элемента")
            await cursor.execute("""
                INSERT INTO Tokens (
                    token, club_id, creator, status, validity, time_of_action,
                    lot, number_in_lot, created_at, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token, club_id, creator_id, 'valid', validity,
                time_of_action, lot, i, created_at, comment
            ))
            tokens[i] = token
    return {
        'tokens': tokens,
        'lot': lot
    }
@log_function_call
async def create_formatted_tokens_for_lot(
    club_id: int,
    lot: Optional[int] = None,
    count: int = 100,
    token_length: int = 9,
    validity_days: int = 30,
    time_of_action_months: int = 12,
    creator_id: Optional[int] = None,
    comment: str = ""  # Добавлен параметр
) -> dict:
    """
    Создаёт указанное количество токенов для заданного лота или следующего свободного номера.
    :param club_id: ID клуба
    :param lot: Номер лота (если None — будет найден первый доступный)
    :param count: Количество токенов
    :param token_length: Длина токена
    :param validity_days: Срок действия в днях
    :param time_of_action_months: Срок действия действия по токену
    :param creator_id: Кто создал токен (ID пользователя)
    :param comment: Комментарий к токенам этого лота
    :return: {'tokens': {ключ - номер тоена в лоте, значение - токен}, 'lot': ...}
    """

    tokens,lot = await create_tokens_for_lot(club_id, lot, count, token_length, validity_days, time_of_action_months, creator_id, comment)
    for i, token in tokens.items():
        tokens[i] = format_token(token)
    return {
        'tokens': tokens,
        'lot': lot
    }

@log_function_call
async def create_tokens_without_lot(
    club_id: int,
    comment: str,
    count: int = 100,
    token_length: int = 9,
    validity_days: int = 30,
    time_of_action_months: int = 12,
    creator_id: Optional[int] = None
) -> List[str]:
    """
    Создаёт токены, не привязывая к лоту (поле lot = NULL).
    :param club_id: ID клуба
    :param count: Количество токенов
    :param token_length: Длина токена
    :param validity_days: Срок в течении которого можно использовать токен в днях
    :param time_of_action_months: Срок действия действия полномочий, полученных по токену
    :param creator_id: Кто создал токен
    :param comment: Комментарий к каждому токену
    :return: Список созданных токенов
    """
    if not comment.strip():
        raise ValueError("Комментарий обязателен при создании токенов")

    tokens = []
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    validity = (
        datetime.datetime.now() + datetime.timedelta(days=validity_days)
    ).strftime("%Y-%m-%d %H:%M:%S")
    time_of_action = (
        datetime.datetime.now() + datetime.timedelta(days=time_of_action_months*30.44)
    ).strftime("%Y-%m-%d %H:%M:%S")
    async with AsyncDatabase(path_db) as cursor:
        for i in range(1, count + 1):
            attempts = 0
            while attempts < 100:
                token = generate_numeric_token(token_length)
                if await is_token_unique(cursor, token):
                    break
                attempts += 1
            else:
                raise RuntimeError(f"Не удалось сгенерировать уникальный токен для {i}-го элемента")
            await cursor.execute("""
                INSERT INTO Tokens (
                    token, club_id, creator, status, validity, time_of_action,
                    created_at, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token, club_id, creator_id, 'valid', validity,
                time_of_action, created_at, comment
            ))
            tokens.append(token)
    return tokens
@log_function_call
async def create_formatted_tokens_without_lot(
    club_id: int,
    comment: str,
    count: int = 100,
    token_length: int = 9,
    validity_days: int = 30,
    time_of_action_months: int = 12,
    creator_id: Optional[int] = None
) -> List[str]:
    """
    Создаёт форматированные токены, не привязывая к лоту (поле lot = NULL).
    :param club_id: ID клуба
    :param count: Количество токенов
    :param token_length: Длина токена
    :param validity_days: Срок в течении которого можно использовать токен в днях
    :param time_of_action_months: Срок действия действия полномочий, полученных по токену
    :param creator_id: Кто создал токен
    :param comment: Комментарий к каждому токену
    :return: Список созданных токенов
    """
    formatted_tokens = []
    tokens = await create_tokens_without_lot(club_id=club_id,comment=comment,
        count=count, token_length=token_length, validity_days=validity_days,
        time_of_action_months=time_of_action_months, creator_id=creator_id
    )
    for token in tokens:
        formatted_tokens.append(format_token(token))
    return formatted_tokens


@log_function_call
async def get_lot_info(club_id: int, lot_number: int) -> dict:
    """
    Возвращает информацию о лоте: кол-во токенов по статусам и списки токенов.

    :param club_id: ID клуба
    :param lot_number: Номер лота
    :return: {
        'total': ...,
        'statuses': {'valid': ..., 'used': ..., ...},
        'tokens_by_status': {'valid': [...], 'used': [...], ...}
    }
    """
    result = {
        'total': 0,
        'statuses': {},
        'tokens_by_status': defaultdict(list),
    }

    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute("""
            SELECT token, status FROM Tokens
            WHERE club_id = ? AND lot = ?
        """, (club_id, lot_number))

        rows = await cursor.fetchall()
        if not rows:
            return {'error': 'Лот не найден или пуст'}

        rows = list(rows)  # <-- Явное преобразование в list
        result['total'] = len(rows)

        for token, status in rows:
            result['tokens_by_status'][status].append(token)
            result['statuses'][status] = result['statuses'].get(status, 0) + 1

    # Преобразуем defaultdict в обычный dict
    result['tokens_by_status'] = dict(result['tokens_by_status'])
    return result

@log_function_call
async def export_tokens_to_excel(
    club_id: int,
    lot_number: Optional[int] = None,
    creator_id: Optional[int] = None,
    filename: str = "tokens_export.xlsx"
) -> str:
    """
    Экспортирует токены в Excel-файл.

    :param club_id: ID клуба
    :param lot_number: Номер лота (если указан — берём только этот лот)
    :param creator_id: ID создателя (если указан — фильтруем по нему)
    :param filename: Имя файла для сохранения
    :return: Путь к файлу
    """

    query = """
        SELECT id, token, validity, time_of_action, status, lot, number_in_lot, created_at, comment
        FROM Tokens
        WHERE club_id = ?
    """
    params = [club_id]

    if lot_number is not None:
        query += " AND lot = ?"
        params.append(lot_number)

    if creator_id is not None:
        query += " AND creator = ?"
        params.append(creator_id)

    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute(query, tuple(params))
        rows = await cursor.fetchall()

        if not rows:
            raise ValueError("Нет токенов для экспорта.")

        # Получаем названия колонок автоматически
        columns = [desc[0] for desc in cursor.description]

        logger.info("Запрос успешно выполнен.")
        df = pd.DataFrame(rows, columns=columns)

    # Сохраняем в Excel
    df.to_excel(filename, index=False)
    return os.path.abspath(filename)
async def mark_token_as_old(token: str) -> bool:
    """
    Помечает токен как устаревший.
    :param token: строка токена без разделителей
    :return: True, если токен был обновлён
    """
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute("""
            UPDATE Tokens SET status = 'old'
            WHERE token = ?
        """, (token,))
        return cursor.rowcount > 0

@log_function_call
async def mark_token_as_used(token: str, memder_id: int) -> bool:
    """
    Помечает токен как использованный.
    :param token: строка токена без разделителей
    :return: True, если токен был обновлён
    """
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute("""
            UPDATE Tokens SET status = 'used', member_id = ?
            WHERE token = ?
        """, (memder_id, token))
        return cursor.rowcount > 0