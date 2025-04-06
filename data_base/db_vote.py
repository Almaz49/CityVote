# Модуль db_vote. Содержит функции для работы с голосованиями
# и подсчетом голосов.

import datetime
import random
import time
from data_base.db_func import *
from utils import log_function_call
from LEXICON.LEXICON import LEXICON
import logging


# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание нового голосования. Создается название голосования и описание,
# также может быть введен тип голосования и ссылка. Варианты добавляются позже.
@log_function_call
async def new_voting(club_id, creator, title, text=None, voting_type='usual', voting_status='add_variants'):
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
                        INSERT INTO Votings(club_id, creator, title, text, time_create, voting_type, voting_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (club_id, creator, title, text, time_create, voting_type, voting_status)
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
                    """
                    SELECT voting_status FROM Votings WHERE id = ?
                    """, (voting_id,)
                )
            status, = await cursor.fetchone()
            await cursor.execute('''SELECT COUNT(*) FROM Variants WHERE (voting_id = ? AND variant_status = 'valid' )''', (voting_id,))
            count_of_var = await cursor.fetchone()
            print (count_of_var)
            count_of_var = count_of_var[0] if count_of_var else 0
            if status != 'add_variants':
                flag = False
                response = 'Это голосование не находится в стадии добавления вариантов, вы не можете его запустить.'
            elif count_of_var < 2:
                flag = False
                response = ('У этого голосования меньше двух вариантов, вы не можете его запустить.'
                            'Добавьте еще варианты.')
            else:
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
                flag = True
                response = 'Голосование успешно запущено'
            return flag,response
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
async def voting_stage(voting_id, club_id, stager=None):
    time_stage = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')
    s_votist = await count_votist(club_id)

    # Подсчитываем число голосов, отданных за каждый вариант (в виде кортежа): всего, напрямую, не имеющих права голоса
    res = {} #Словарь результатов голосования, ключ - ID варианта, значение - кортеж из трех результатов - 1. число реающих
            #   голосов за вариант (поданных напрямую и поданных через предстаителя), 2. число решающих голосов, поданных напрямую,
            # 3. число нерешающих голосов, поданных за вариант напрямую

    sum_vote = 0 #сумма поданых за все варианты решающих голосов (как напрямую так и через представителя)

    for item in variants:
        dir_votes = await count_directly_votes(item[0]) # решающие голоса, поданные за вариант напрямую
        prox_votes = await count_proxy_votes(item[0])   #решающие голоса, поданные через представителя
        empt_votes = await count_directly_empty_votes(item[0])   # нерешающие голоса
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)
        sum_vote += dir_votes + prox_votes

    logging.info(f"Результаты голосования для voting_id={voting_id}: {res}")
    logging.info(f"Суммарное количество голосов: {sum_vote}")

    # Если проголосовало более половины решающих голосои, отсекаем самые непопулярные варианты.
    # Сумма голосов за оставшиеся варианты должна быть более 1/2 от числа решающих голосов.
    if sum_vote * 2 > s_votist:
        a = s_votist / 2
        k = None

# сортрируем варианты в порядке убывания результата
        sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)

# по очереди вычитаем результат вариантов из 1/2 общего числа голосов, пока не получим отрицательное значение
        for i in range(len(sorted_res)):
            a -= sorted_res[i][1][0]
            if a < 0:
                k = sorted_res[i][1][0] #Значение "отсечения" - те варианты, которые набрали меньше, становятся проигравшими
                break

        losers = [item for item in res if res[item][0] < k]
        winners = [item for item in res if res[item][0] >= k]

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
                    flag = True
                    text =  f'''Осталось {len(winners)} вариантов. \n
                    Выбыли варианты:{tuple(zip(*losers))[0]}'''
                    if len(winners) == 1:
                        winner_id, = winners[0]
                        await cursor.execute(
                        '''
                        UPDATE Variants SET variant_status = 'winner' WHERE id = ?
                        ''', (winner_id,)
                        )
                        await cursor.execute(
                            """
                            UPDATE Votings SET result = ?, time_completed = ?,
                            voting_status =  WHERE id = ?
                            """, (winner_id, time_stage, 'completed', voting_id)
                        )


                        await cursor.execute(
                            '''
                            INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                            VALUES (?,?,?,?,?)
                            ''', ('voting', voting_id, stager, 'completed', time_stage)
                        )

                        logging.info(f"Победивший вариант: {winner_id}, Проигравшие варианты: {losers}")
                        flag = True
                        for item in variants:
                            if item[0] == winner_id:
                                winner_title = item[1]
                        text = f'Голосование завершено, победил вариант: {winner_title}'
                else:
                    logging.info("Нет проигравших вариантов.")
                    flag = False
                    text = 'Нет проигравших вараинтов'
            except aiosqlite.Error as e:
                logging.error(f"Ошибка при завершении промежуточного этапа голосования: {e}")
                raise
    else:
        logging.info("Сумма голосов недостаточна для завершения промежуточного этапа.")
        flag = False
        text = 'Сумма голосов недостаточна для завершения промежуточного этапа.'
        winners = variants
        losers = None
    return flag,text,winners,losers

# Функция создания финального этапа голосования (где голосуется два варианта или больше, если есть варианты,
# которые набрали столько же, сколько второй)
@log_function_call
async def voting_final(voting_id, finaler=None):
    time_final = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')

    if not variants:
        logging.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        flag = False
        text = 'Нет действительных вариантов'

    res = {}
    for item in variants:
        dir_votes = await count_directly_votes(item[0])
        prox_votes = await count_proxy_votes(item[0])
        empt_votes = await count_directly_empty_votes(item[0])
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)

    sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
    # Находим результат "отсечения" (варианты, набравшие меньше, проигрывают).
    # Вполне возможно, ниже требуется не float('inf') а 0
    k = sorted_res[1][1] if len(sorted_res) > 1 else (0, 0, 0)
    losers = [item for item in res.items() if item[1] < k]
    winners = [item for item in res if res[item][0] >= k]

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
                flag = True
                text = f'В финал голосования вышли варианты {winners}'
            else:
                logging.info("Нет проигравших вариантов.")
                flag = True
                text = f'В финал голосования вышли варианты {winners}'
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при создании финального этапа голосования: {e}")
            raise
    return flag,text,winners,losers

# Функция завершения голосования. Определяет вариант - победитель.
# При прочих равных (что вряд ли) побеждает тот вариант, который создан раньше.
# Если вариант победитель не набрал 50% от числа действительных голосов,
# запускается утверждение итогов голосования. То есть выбор между вариантом-победителем
# и вариантом  "Лучше не принимать никакого решения"
@log_function_call
async def voting_complete(voting_id, finisher=None):
    time_finish = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')
    club_id = await extract_group_id(voting_id)
    s_votist = await count_votist(club_id)

    if not variants:
        logging.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        return 'У голосования нет действительных вариантов', None, None, None

    res = {}
    for item in variants:
        dir_votes = await count_directly_votes(item[0])
        prox_votes = await count_proxy_votes(item[0])
        empt_votes = await count_directly_empty_votes(item[0])
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)

    sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
    winner_id = sorted_res[0][0]
    winner_res = sorted_res[0][1]

# Ищем нет ли других вариантов с максимальным результатом.
# Если есть - победителем назначается вариант, созданный раньше.
    i = 1
    flag = True if i + 1 <= len(sorted_res) else False

    while flag:
        if sorted_res[i][1] == winner_res:
            if sorted_res[i][0] < winner_id:
                winner_id = sorted_res[i][0]
            i += 1
        else:
            flag = False

# делаем список (точнее, кортеж кортежей) ID проигравших вариантов (все, кроме winner_id)
    losers_list = []
    for item in variants:
        if item[0] != winner_id:
            losers_list.append(item[0],)

    losers = [(id,) for id in losers_list]


    winner_title = None
    for item in variants:
        if item[0] == winner_id:
            winner_title = item[1]

# Записываем в БД проигравшие варианты
    async with AsyncDatabase(path_db) as cursor:
        try:
            if losers:
                await cursor.executemany(
                    '''
                   UPDATE Variants SET variant_status = 'loser' WHERE id = ?
                    ''', losers
                )
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при завершении голосования: {e}")
            raise

# Если вариант-победитель набрал менее половины действительных голосов, запускаем процедуру утверждения итогов голосования
    if winner_res[0] * 2 < s_votist:
        await confirmation_of_voting_results(voting_id, winner_id)
        text = f'''Победил вариант {winner_title}.\n
        Его результат:\n
        Всего голосов "за": {winner_res[[0]]}\n
        Из них отдано напрямую: {winner_res[1]}\n
        Отдано недействительных голосов: {winner_res[2]}\n
        Oн набрал менее 50% действительных голосов.\n
        Запущена процедура утверждения итогов голосования.'''
    else:
        async with AsyncDatabase(path_db) as cursor:
            try:
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
                    UPDATE Votings SET voting_status = 'completed', time_completed = ? WHERE id = ?
                    ''', (time_finish, voting_id)
                )
                await cursor.execute(
                    '''
                    INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                    VALUES (?,?,?,?,?)
                    ''', ('voting', voting_id, finisher, 'completed', time_finish)
                )

                logging.info(f"Победивший вариант: {winner_id}, Проигравшие варианты: {losers}")
                text = f'''Победил вариант {winner_title}.\n
                Его результат:\n
                Всего голосов "за": {winner_res[[0]]}\n
                Из них отдано напрямую: {winner_res[1]}\n
                Отдано недействительных голосов: {winner_res[2]}\n
                Oн набрал более 50% действительных голосов.\n
                Голосование завершено.'''

            except aiosqlite.Error as e:
                logging.error(f"Ошибка при завершении голосования: {e}")
                raise
    return text, winner_id, winner_title, winner_res

# Функция запуска утверждения итогов голосования.
# Добавляет вариант "Лучше не принимать никакого решения". Переводит голосование в статус 'confirmation'
@log_function_call
async def confirmation_of_voting_results(voting_id, winner_id):
    logging.info(f'Запущено утверждение итогов голосования {voting_id}')
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    author = 0
    title = LEXICON.get("Don't make any decision","Don't make any decision")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                UPDATE Votingd SET voting_status = 'confirmation' WHERE id = ?
                ''', (voting_id,)
            )
            await cursor.execute(
                '''
                INSERT OR IGNORE INTO Variants(voting_id, author, title, variant_status, text, time_create)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (voting_id, author, title, 'valid', title, time_create)
            )
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при запуске утверждения итогов голосования: {e}")
            raise



# Функция завершения утврждения голосования. Определяет вариант - победитель (или отсутствие победителя).
# При прочих равных (что вряд ли) побеждает тот вариант, который создан раньше.
@log_function_call
async def confirmation_of_voting_results_stop(voting_id, finisher=None):
    time_finish = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')
    club_id = await extract_group_id(voting_id)

    if not variants:
        logging.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        return 'У голосования нет действительных вариантов', None, None, None

    res = {}
    for item in variants:
        dir_votes = await count_directly_votes(item[0])
        prox_votes = await count_proxy_votes(item[0])
        empt_votes = await count_directly_empty_votes(item[0])
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)

    sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
    winner_id = sorted_res[0][0]
    winner_res = sorted_res[0][1]

# Ищем нет ли других вариантов с максимальным результатом.
# Если есть - победителем назначается вариант, созданный раньше.
    i = 1
    flag = True if i + 1 <= len(sorted_res) else False

    while flag:
        if sorted_res[i][1] == winner_res:
            if sorted_res[i][0] < winner_id:
                winner_id = sorted_res[i][0]
            i += 1
        else:
            flag = False

# делаем список (точнее, кортеж кортежей) ID проигравших вариантов (все, кроме winner_id)
    losers_list = []
    for item in variants:
        if item[0] != winner_id:
            losers_list.append(item[0],)

    losers = tuple(losers_list)


    winner_title = None
    for item in variants:
        if item[0] == winner_id:
            winner_title = item[1]

# Записываем в БД проигравшие варианты
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
                UPDATE Votings SET voting_status = 'completed', time_completed = ? WHERE id = ?
                ''', (time_finish, voting_id)
            )
            await cursor.execute(
                '''
                INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                VALUES (?,?,?,?,?)
                ''', ('voting', voting_id, finisher, 'completed', time_finish)
            )

            logging.info(f"Победивший вариант: {winner_id}, Проигравшие варианты: {losers}")
            text = f'''Победил вариант {winner_title}.\n
            Его результат:\n
            Всего голосов "за": {winner_res[[0]]}\n
            Из них отдано напрямую: {winner_res[1]}\n
            Отдано недействительных голосов: {winner_res[2]}\n
            Голосование завершено.'''

        except aiosqlite.Error as e:
            logging.error(f"Ошибка при завершении голосования: {e}")
            raise
    return text, winner_id, winner_title, winner_res



# Функция возвращает статус голосования по его ID
@log_function_call
async def extract_voting_status(voting_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                SELECT voting_status FROM Votings WHERE id = ?
                ''', (voting_id,)
            )
            result = await cursor.fetchone()
            if result:
                voting_status, = result
                logging.info(f"Статус голосования voting_id={voting_id}: {voting_status}")
                return voting_status
            else:
                logging.info(f"Для voting_id={voting_id} не найдено статуса.")
                return None
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при получении статуса голосования: {e}")
            raise

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#      Функция возобновления голосования
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!