# Модуль db_vote. Содержит функции для работы с голосованиями
# и подсчетом голосов.

import datetime
import random
import time
from data_base.db_func import *
from utils import log_function_call
import logging


# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание нового голосования. Создается название голосования и описание,
# также может быть введен тип голосования и ссылка. Варианты добавляются позже.
@log_function_call
async def new_voting(club_id, creator, title, text=None, vote_type='usual', voting_status='add_variants'):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(title) > 40:
        flag = False
        answ_str = ('Название не должно быть длиннее 40 символов.'
                    ' Придумайте другое название.')
    else:
        async with AsyncDatabase(path_db) as cursor:
            try:
                await cursor.execute(
                    """
                    SELECT title FROM Votings WHERE club_id = ? AND voting_status <> 'finished'
                    """, (club_id,)
                )
                titles = await cursor.fetchall()
                if (title,) not in titles:
                    logging.info(f"Добавление нового голосования: club_id={club_id}, creator={creator}, title={title}")
                    await cursor.execute(
                        '''
                        INSERT INTO Votings(club_id, creator, title, text, time_create, vote_type, voting_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (club_id, creator, title, text, time_create, vote_type, voting_status)
                    )
                    answ_str = 'Голосование добавлено'
                    flag = True
                else:
                    answ_str = ('Уже есть идущее голосование с таким названием.'
                                ' Придумайте другое название.')
                    flag = False
            except aiosqlite.Error as e:
                logging.error(f"Ошибка при создании нового голосования: {e}")
                raise
    return flag, answ_str

# Создание варианта для голосования. Добавляется только в голосования
# со статусом ожидания вариантов.
# В БД вносится автор (member_id), заголовок варианта, текст варианта,
# если есть - ссылка.
# Возвращает комментарий по итогам добавления.
@log_function_call
async def new_variant(voting_id, author, title, text=None, variant_status='valid'):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(title) > 40:
        flag, answ_str = False, 'Название не должно быть длиннее 40 символов.'
    else:
        async with AsyncDatabase(path_db) as cursor:
            try:
                await cursor.execute(
                    """
                    SELECT voting_status FROM Votings WHERE id = ?
                    """, (voting_id,)
                )
                status, = await cursor.fetchone()
                if status == 'add_variants':
                    logging.info(f"Добавление нового варианта: voting_id={voting_id}, author={author}, title={title}")
                    await cursor.execute(
                        """
                        SELECT title FROM Variants WHERE voting_id = ?
                        """, (voting_id,)
                    )
                    titles = await cursor.fetchall()
                    if (title,) not in titles:
                        await cursor.execute(
                            '''
                            INSERT INTO Variants(voting_id, author, title, variant_status, text, time_create)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ''', (voting_id, author, title, variant_status, text, time_create)
                        )
                        answ_str = 'Вариант добавлен'
                        flag = True
                    else:
                        answ_str = '''Вариант с таким названием уже существует.
Придумайте другое название.'''
                        flag = False
                else:
                    answ_str = 'К этому голосованию нельзя добавить варианты.'
                    flag = False
            except aiosqlite.Error as e:
                logging.error(f"Ошибка при добавлении нового варианта: {e}")
                raise
    return flag, answ_str

# Функция старта голосования. Меняем статус голосования на 'ongoing'.
# Указываем, кто запустил голосование (если не автоматически).
@log_function_call
async def voting_start(voting_id, starter=None):
    time_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                UPDATE Votings SET voting_status = ?, time_start = ?
                WHERE id = ?
                ''', ('ongoing', time_start, voting_id)
            )
            await cursor.execute(
                '''
                INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                VALUES (?, ?, ?, ?, ?)
                ''', ('voting', voting_id, starter, 'ongoing', time_start)
            )
            logging.info(f"Голосование {voting_id} запущено пользователем {starter}.")
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при старте голосования: {e}")
            raise




# Функция возвращает ID голосования по ID варианта
@log_function_call
async def extract_voting_id(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                SELECT voting_id FROM Variants WHERE id = ?
                ''', (variant_id,)
            )
            result = await cursor.fetchone()
            if result:
                voting_id, = result
                logging.info(f"ID голосования для variant_id={variant_id}: {voting_id}")
                return voting_id
            else:
                logging.info(f"Для variant_id={variant_id} не найдено голосования.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при получении ID голосования: {e}")
            raise

# Функция возвращает ID группы по ID голосования
@log_function_call
async def extract_group_id(voting_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                SELECT club_id FROM Votings WHERE id = ?
                ''', (voting_id,)
            )
            result = await cursor.fetchone()
            if result:
                club_id, = result
                logging.info(f"ID группы для voting_id={voting_id}: {club_id}")
                return club_id
            else:
                logging.info(f"Для voting_id={voting_id} не найдена группа.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при получении ID группы: {e}")
            raise

# Функция выясняет, за какие варианты в данном голосовании голосовал (лично) пользователь
# Возвращает ID вариантов (список кортежей с одним членом) или None
@log_function_call
async def past_choise(member_id, voting_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT id FROM Elections
                WHERE member_id = ? AND variant_id IN
                (SELECT id FROM Variants
                WHERE voting_id = ?) AND status = 'valid'
            ''', (member_id, voting_id))
            result = await cursor.fetchall()
            logging.info(f"Результат выборки для member_id={member_id}, voting_id={voting_id}: {result}")
            return result
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при проверке прошлых выборов: {e}")
            raise

# Функция подсчета числа членов группы, имеющих право голоса
@log_function_call
async def count_votist(club_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members WHERE id IN
                (SELECT id FROM Members WHERE club_id = ?)
                AND id IN
                (SELECT member_id FROM Status WHERE status = 'votist')
            ''', (club_id,))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logging.info(f"Количество участников с правом голоса в группе {club_id}: {amount}")
                return int(amount)
            else:
                logging.info(f"В группе {club_id} нет участников с правом голоса.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при подсчете количества участников с правом голоса: {e}")
            raise



# Функция подсчета голосов, отданых за вариант лично теми, кто имеет право голоса
@log_function_call
async def count_directly_votes(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members WHERE id IN
                (SELECT member_id FROM Elections WHERE variant_id = ? AND status = 'valid')
                AND id IN
                (SELECT member_id FROM Status WHERE status = 'votist')
            ''', (variant_id,))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logging.info(f"Количество прямых голосов за variant_id={variant_id}: {amount}")
                return int(amount)
            else:
                logging.info(f"Для variant_id={variant_id} нет прямых голосов.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при подсчете прямых голосов: {e}")
            raise

# Функция подсчета голосов, отданых за вариант лично теми, кто не имеет право голоса
@log_function_call
async def count_directly_empty_votes(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members WHERE id IN
                (SELECT member_id FROM Elections WHERE variant_id = ? AND status = 'valid')
                AND id NOT IN
                (SELECT member_id FROM Status WHERE status = 'votist')
            ''', (variant_id,))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logging.info(f"Количество прямых голосов без права голоса за variant_id={variant_id}: {amount}")
                return int(amount)
            else:
                logging.info(f"Для variant_id={variant_id} нет прямых голосов без права голоса.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при подсчете прямых голосов без права голоса: {e}")
            raise

# Функция подсчета голосов, отданых за вариант через представителей
@log_function_call
async def count_proxy_votes(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members WHERE proxy IN
                (SELECT member_id FROM Elections WHERE variant_id = ? AND status = 'valid')
                AND id NOT IN
                (SELECT member_id FROM Elections WHERE status = 'valid'
                AND variant_id IN
                (SELECT id FROM Variants WHERE voting_id IN
                (SELECT voting_id FROM Variants WHERE id = ?)))
                AND id IN
                (SELECT member_id FROM Status WHERE status = 'votist')
            ''', (variant_id, variant_id))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logging.info(f"Количество голосов через представителей за variant_id={variant_id}: {amount}")
                return int(amount)
            else:
                logging.info(f"Для variant_id={variant_id} нет голосов через представителей.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при подсчете голосов через представителей: {e}")
            raise

# Функция выбора варианта при голосовании
@log_function_call
async def election(member_id, variant_id):
    time_election = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    voting_id = await extract_voting_id(variant_id)
    old_elect = await past_choise(member_id, voting_id)
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT voting_status FROM Votings WHERE id = ?
            ''', (voting_id,))
            result = await cursor.fetchone()
            if result:
                voting_status, = result
                if voting_status == 'add_variants':
                    answer = (False, 'Голосование ещё не началось')
                elif voting_status == 'completed':
                    answer = (False, 'Голосование уже закончилось')
                elif voting_status == 'ongoing':
                    await cursor.execute('''
                        SELECT variant_status FROM Variants WHERE id = ?
                    ''', (variant_id,))
                    variant_status, = await cursor.fetchone()
                    if variant_status == 'loser':
                        answer = (False, 'Этот вариант уже выбыл из голосования')
                    else:
                        # Делаем запись о голосовании в таблицу выборов
                        await cursor.execute('''
                            INSERT INTO Elections(member_id, variant_id, time_election, status)
                            VALUES (?, ?, ?, ?)
                        ''', (member_id, variant_id, time_election, 'valid'))
                        # Меняем статус предыдущего выбора на 'invalid'
                        if old_elect:
                            for item in old_elect:
                                await cursor.execute('''
                                    UPDATE Elections SET status = 'invalid' WHERE id = ?
                                ''', (item[0],))
                        answer = (True, 'Ваш голос принят')
                else:
                    answer = (False, 'Непонятен статус голосования')
            else:
                answer = (False, 'Не удалось получить статус голосования')

            if 'votist' not in await extract_status(member_id):
                str1 = f"{answer[1]}\n Обращаем ваше внимание на то, что ваш голос не учитывается при подсчете.\n Возможно, ваша личность не подтверждена регистратором или вы не выбрали представителя."
                flag = answer[0]
                answer = (flag, str1)
            return answer
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при выборе варианта: {e}")
            raise



# Функция завершения промежуточного этапа голосования. Переводит в статус "loser" наименее популярные варианты.
# Оставшиеся варианты должны в сумме набирать 50% голосов от имеющих право голоса.
# Возвращает кортеж из ID проигравших вариантов.
@log_function_call
async def voting_stage(voting_id, stager=None):
    time_stage = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')
    club_id = await extract_group_id(voting_id)
    s_votist = await count_votist(club_id)

    # Подсчитываем число голосов, отданных за каждый вариант (в виде кортежа): всего, напрямую, не имеющих права голоса
    res = {}
    sum_vote = 0

    for item in variants:
        dir_votes = await count_directly_votes(item[0])
        prox_votes = await count_proxy_votes(item[0])
        empt_votes = await count_directly_empty_votes(item[0])
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)
        sum_vote += dir_votes + prox_votes

    logging.info(f"Результаты голосования для voting_id={voting_id}: {res}")
    logging.info(f"Суммарное количество голосов: {sum_vote}")

    if sum_vote * 2 > s_votist:
        a = s_votist / 2
        k = None

        sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
        for i in range(len(sorted_res)):
            a -= sorted_res[i][1][0]
            if a < 0:
                k = sorted_res[i][1][0]
                break

        losers = [(item,) for item in res if res[item][0] < k]

        async with AsyncDatabase(path_db) as cursor:
            try:
                if losers:
                    await cursor.executemany(
                        '''
                        UPDATE Variants SET variant_status = 'loser' WHERE id = ?
                        ''', losers
                    )
                    await cursor.execute(
                        '''
                        INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                        VALUES (?,?,?,?,?)
                        ''', ('voting', voting_id, stager, 'stage', time_stage)
                    )
                    logging.info(f"Проигравшие варианты: {losers}")
                    return tuple(zip(*losers))[0] if losers else None
                else:
                    logging.info("Нет проигравших вариантов.")
                    return None
            except aiosqlite.Error as e:
                logging.error(f"Ошибка при завершении промежуточного этапа голосования: {e}")
                raise
    else:
        logging.info("Сумма голосов недостаточна для завершения промежуточного этапа.")
        return None

# Функция создания финального этапа голосования (где голосуется два варианта или больше, если есть варианты,
# которые набрали столько же, сколько второй)
@log_function_call
async def voting_final(voting_id, finaler=None):
    time_final = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')

    if not variants:
        logging.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        return None

    res = {}
    for item in variants:
        dir_votes = await count_directly_votes(item[0])
        prox_votes = await count_proxy_votes(item[0])
        empt_votes = await count_directly_empty_votes(item[0])
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)

    sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
    k = sorted_res[1][1] if len(sorted_res) > 1 else (float('inf'), float('inf'), float('inf'))
    losers = [(item[0],) for item in res.items() if item[1] < k]

    async with AsyncDatabase(path_db) as cursor:
        try:
            if losers:
                await cursor.executemany(
                    '''
                    UPDATE Variants SET variant_status = 'loser' WHERE id = ?
                    ''', losers
                )
                await cursor.execute(
                    '''
                    INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                    VALUES (?,?,?,?,?)
                    ''', ('voting', voting_id, finaler, 'final', time_final)
                )
                logging.info(f"Проигравшие варианты: {losers}")
                return tuple(zip(*losers))[0] if losers else None
            else:
                logging.info("Нет проигравших вариантов.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при создании финального этапа голосования: {e}")
            raise

# Функция завершения голосования. Определяет вариант - победитель.
# При прочих равных (что вряд ли) побеждает тот вариант, который создан раньше.
@log_function_call
async def voting_complete(voting_id, finisher=None):
    time_finish = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')

    if not variants:
        logging.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        return None, [], []

    res = {}
    for item in variants:
        dir_votes = await count_directly_votes(item[0])
        prox_votes = await count_proxy_votes(item[0])
        empt_votes = await count_directly_empty_votes(item[0])
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)

    sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
    winner_id = sorted_res[0][0]
    winner_res = sorted_res[0][1]

    i = 1
    flag = True if i + 1 <= len(sorted_res) else False

    while flag:
        if sorted_res[i][1] == winner_res:
            if sorted_res[i][0] < winner_id:
                winner_id = sorted_res[i][0]
                winner_res = sorted_res[i][1]
            i += 1
        else:
            flag = False

    losers = [(sorted_res[i][0],) for i in range(1, len(sorted_res))]

    async with AsyncDatabase(path_db) as cursor:
        try:
            if losers:
                await cursor.executemany(
                    '''
                    UPDATE Variants SET variant_status = 'loser' WHERE id = ?
                    ''', losers
                )
            if winner_id:
                await cursor.execute(
                    '''
                    UPDATE Variants SET variant_status = 'winner' WHERE id = ?
                    ''', (winner_id,)
                )
                await cursor.execute(
                    """
                    UPDATE Votings SET result = ?, time_completed = ? WHERE id = ?
                    """, (winner_id, time_finish, voting_id)
                )

            await cursor.execute(
                '''
                UPDATE Votings SET voting_status = 'finished', time_completed = ? WHERE id = ?
                ''', (time_finish, voting_id)
            )
            await cursor.execute(
                '''
                INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                VALUES (?,?,?,?,?)
                ''', ('voting', voting_id, finisher, 'finish', time_finish)
            )

            logging.info(f"Победивший вариант: {winner_id}, Проигравшие варианты: {losers}")
            return winner_id, losers, sorted_res
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при завершении голосования: {e}")
            raise
