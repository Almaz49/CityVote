# Модуль db_vote. Содержит функции для работы с голосованиями
# и подсчетом голосов.

import datetime
from data_base.db_func import *
from utils import log_function_call, fetch_as_dict
from LEXICON.LEXICON import LEXICON
import logging
import traceback


# Настройка логирования
logger = logging.getLogger(__name__)

# Создание нового голосования. Создается название голосования и описание,
# также может быть введен тип голосования и ссылка. Варианты добавляются позже.
@log_function_call
async def voting_create(club_id, creator, title, text=None, voting_type='usual', voting_status='add_variants'):
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
                # Преобразуем список объектов Row в список строк
                existing_titles = [row[0] for row in titles]

                if title not in existing_titles:
                    logger.info(f"Добавление нового голосования: club_id={club_id}, creator={creator}, title={title}")
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
                logger.error(f"Ошибка при создании нового голосования: {e}\n{traceback.format_exc()}")
                raise
    result = {'success':flag, 'message':answ_str}
    return result

@log_function_call
async def get_voting_info(voting_id):
    """
    Извлекает информацию о голосовании по его ID.
    :param voting_id: ID голосования.
    :return: Информация группы в базе данных или None, если имя не найдено.
    """
    logger.info(f"Извлечение информации о голосовании для voting_id={voting_id}")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                SELECT *
                FROM Votings WHERE id = ?
                ''', (voting_id,)
            )
            result = await fetch_as_dict(cursor)
            if result:
                logger.info(f"Найдена информация {result[0]} для voting_id={voting_id}")
                return result[0]
            else:
                logger.info(f"Информация о группе voting_id={voting_id} не найдено.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при извлечении информации о группе voting_id={voting_id}: {e}\n{traceback.format_exc()}")
            raise

# Создание варианта для голосования. Добавляется только в голосования
# со статусом ожидания вариантов.
# В БД вносится автор (member_id), заголовок варианта, текст варианта,
# если есть - ссылка.
# Возвращает комментарий по итогам добавления.
@log_function_call
async def variant_create(voting_id, author, title, text=None, variant_status='valid'):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if len(title) > 40:
        flag, answ_str = False, 'Название не должно быть длиннее 40 символов.'
    else:
        async with AsyncDatabase(path_db) as cursor:
            try:
                # Проверяем статус голосования
                await cursor.execute(
                    """
                    SELECT voting_status FROM Votings WHERE id = ?
                    """, (voting_id,)
                )
                result = await cursor.fetchone()

                if result is None:
                    logger.error(f"Голосование с voting_id={voting_id} не найдено.")
                    return False, "Голосование не найдено."

                status, = result  # Распаковываем результат

                if status == 'add_variants':
                    logger.info(f"Добавление нового варианта: voting_id={voting_id}, author={author}, title={title}")

                    # Проверяем существующие варианты
                    await cursor.execute(
                        """
                        SELECT title FROM Variants WHERE voting_id = ?
                        """, (voting_id,)
                    )
                    titles = await cursor.fetchall()

                    # Преобразуем список объектов Row в список строк
                    existing_titles = [row[0] for row in titles]

                    if title not in existing_titles:
                        await cursor.execute(
                            '''
                            INSERT INTO Variants(voting_id, author, title, variant_status, text, time_create)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ''', (voting_id, author, title, variant_status, text, time_create)
                        )
                        answ_str = 'Вариант добавлен'
                        flag = True
                    else:
                        answ_str = ('Вариант с таким названием уже существует. '
                                    'Придумайте другое название.')
                        flag = False
                else:
                    answ_str = 'К этому голосованию нельзя добавить варианты.'
                    flag = False
            except aiosqlite.Error as e:
                logger.error(f"Ошибка при добавлении нового варианта: {e}\n{traceback.format_exc()}")
                raise

    return flag, answ_str

# Функция старта голосования. Меняем статус голосования на 'ongoing'.
# Указываем, кто запустил голосование (если не автоматически).
@log_function_call
async def voting_start(voting_id, starter=None):
    time_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with AsyncDatabase(path_db) as cursor:
        try:
            # Проверяем статус голосования
            await cursor.execute(
                """
                SELECT voting_status FROM Votings WHERE id = ?
                """, (voting_id,)
            )
            result = await cursor.fetchone()

            if result is None:
                logger.error(f"Голосование с voting_id={voting_id} не найдено.")
                return {'success': False, 'message': "Голосование не найдено."}

            status, = result  # Распаковываем результат

            # Проверяем количество активных вариантов
            await cursor.execute(
                """
                SELECT COUNT(*) FROM Variants
                WHERE (voting_id = ? AND variant_status = 'valid')
                """, (voting_id,)
            )
            count_of_var = await cursor.fetchone()
            count_of_var = count_of_var[0] if count_of_var else 0  # Обрабатываем None

            # Логика проверки условий
            if status != 'add_variants':
                flag = False
                response = ('Это голосование не находится в стадии добавления вариантов, '
                            'вы не можете его запустить.')
            elif count_of_var < 2:
                flag = False
                response = ('У этого голосования меньше двух вариантов, вы не можете его запустить. '
                            'Добавьте еще варианты.')
            else:
                # Обновляем статус голосования
                await cursor.execute(
                    '''
                    UPDATE Votings
                    SET voting_status = ?, time_start = ?
                    WHERE id = ?
                    ''', ('ongoing', time_start, voting_id)
                )
                # Регистрируем событие запуска голосования
                await cursor.execute(
                    '''
                    INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                    VALUES (?, ?, ?, ?, ?)
                    ''', ('voting', voting_id, starter, 'ongoing', time_start)
                )
                logger.info(f"Голосование {voting_id} запущено пользователем {starter}.")
                flag = True
                response = 'Голосование успешно запущено'

            # Формируем результат
            result = {'success': flag, 'message': response}
            return result

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при старте голосования: {e}\n{traceback.format_exc()}")
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
                logger.info(f"ID голосования для variant_id={variant_id}: {voting_id}")
                return voting_id
            else:
                logger.info(f"Для variant_id={variant_id} не найдено голосования.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при получении ID голосования: {e}\n{traceback.format_exc()}")
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
                logger.info(f"ID группы для voting_id={voting_id}: {club_id}")
                return club_id
            else:
                logger.info(f"Для voting_id={voting_id} не найдена группа.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при получении ID группы: {e}\n{traceback.format_exc()}")
            raise

# Функция выясняет, за какие варианты в данном голосовании голосовал (лично) пользователь
# Возвращает ID записей в журнале голосований (список кортежей с одним членом) или None
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
            logger.info(f"Результат выборки для member_id={member_id}, voting_id={voting_id}: {result}")
            return result
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при проверке прошлых выборов: {e}\n{traceback.format_exc()}")
            raise

# Функция выясняет, за какой вариант в данном голосовании голосовал (лично) пользователь и который пока действителен
# Возвращает список ID вариантов или None (по идее из одного максимум члена)
@log_function_call
async def extract_member_choise(member_id, voting_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT variant_id FROM Elections
                WHERE member_id = ? AND variant_id IN
                (SELECT id FROM Variants
                WHERE voting_id = ?) AND status IN ('valid','loser','win')
            ''', (member_id, voting_id))
            result = await cursor.fetchall()
            if result:
                choise = [item[0] for item in result]
            else:
                choise = None
            logger.info(f"Результат выборки вариантов для member_id={member_id}, voting_id={voting_id}: {result}")
            return choise
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при проверке прошлых выборов: {e}\n{traceback.format_exc()}")
            raise


@log_function_call
async def number_of_trusted_votes(club_id,proxy):
    """
    Вычисляет число голосов, доверенных представителю
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members
                WHERE club_id = ? AND proxy = ?
            ''', (club_id, proxy))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logger.info(f"Количество голосов, доверенных представителю {proxy}: {amount}")
                return int(amount)
            else:
                logger.info(f"У представителя {proxy} нет доверенных голосов.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при подсчете числа доверенных голосов: {e}\n{traceback.format_exc()}")
            raise


# Функция подсчета числа членов группы, имеющих право голоса
@log_function_call
async def count_votist(club_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members WHERE club_id = ?
                AND id IN
                (SELECT member_id FROM Status WHERE status = 'votist')
            ''', (club_id,))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logger.info(f"Количество участников с правом голоса в группе {club_id}: {amount}")
                return int(amount)
            else:
                logger.info(f"В группе {club_id} нет участников с правом голоса.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при подсчете количества участников с правом голоса: {e}\n{traceback.format_exc()}")
            raise



# Функция подсчета голосов, отданых за вариант лично теми, кто имеет право голоса
@log_function_call
async def count_directly_votes(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            # await cursor.execute('''
            #     SELECT COUNT(*) FROM Members WHERE id IN
            #     (SELECT member_id FROM Elections WHERE variant_id = ? AND (status = 'valid' OR status = 'loser' OR status = 'winner'))
            #     AND id IN
            #     (SELECT member_id FROM Status WHERE status = 'votist')
            # ''', (variant_id,))
            await cursor.execute('''
            SELECT COUNT(DISTINCT Members.id)
            FROM Members
            JOIN Elections ON Members.id = Elections.member_id
            JOIN Status ON Members.id = Status.member_id
            WHERE Elections.variant_id = ?
            AND Elections.status IN ('valid', 'lose', 'win')
            AND Status.status = 'votist'
            ''', (variant_id,))

            result = await cursor.fetchone()
            if result:
                amount, = result
                logger.info(f"Количество прямых голосов за variant_id={variant_id}: {amount}")
                return int(amount)
            else:
                logger.info(f"Для variant_id={variant_id} нет прямых голосов.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при подсчете прямых голосов: {e}\n{traceback.format_exc()}")
            raise

# Функция подсчета голосов, отданых за вариант лично теми, кто не имеет право голоса
@log_function_call
async def count_directly_empty_votes(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members WHERE id IN
                (SELECT member_id FROM Elections WHERE variant_id = ? AND status IN ('valid', 'lose', 'winner'))
                AND id NOT IN
                (SELECT member_id FROM Status WHERE status = 'votist')
            ''', (variant_id,))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logger.info(f"Количество прямых голосов без права голоса за variant_id={variant_id}: {amount}")
                return int(amount)
            else:
                logger.info(f"Для variant_id={variant_id} нет прямых голосов без права голоса.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при подсчете прямых голосов без права голоса: {e}\n{traceback.format_exc()}")
            raise

# Функция подсчета голосов, отданых за вариант через представителей
@log_function_call
async def count_proxy_votes_old(variant_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT COUNT(*) FROM Members WHERE proxy IN
                (SELECT member_id FROM Elections WHERE variant_id = ? AND status IN ('valid', 'lose', 'winner'))
                AND id NOT IN
                (SELECT member_id FROM Elections WHERE status IN ('valid', 'lose', 'winner')
                AND variant_id IN
                (SELECT id FROM Variants WHERE voting_id IN
                (SELECT voting_id FROM Variants WHERE id = ?)))
                AND id IN
                (SELECT member_id FROM Status WHERE status = 'votist')
            ''', (variant_id, variant_id))
            result = await cursor.fetchone()
            if result:
                amount, = result
                logger.info(f"Количество голосов через представителей за variant_id={variant_id}: {amount}")
                return int(amount)
            else:
                logger.info(f"Для variant_id={variant_id} нет голосов через представителей.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при подсчете голосов через представителей: {e}\n{traceback.format_exc()}")
            raise

@log_function_call
async def count_proxy_votes(variant_id):
    """
    Подсчитывает количество голосов, отданных за вариант через представителей.

    :param variant_id: ID варианта, для которого подсчитываются голоса.
    :return: Количество голосов через представителей или None, если их нет.
    """
    async with AsyncDatabase(path_db) as cursor:
        try:
            # Подсчет голосов через представителей
            await cursor.execute('''
                SELECT COUNT(*)
                FROM Members m
                INNER JOIN Status s ON m.id = s.member_id
                LEFT JOIN Elections e ON m.id = e.member_id
                WHERE s.status = 'votist'
                  AND m.proxy IS NOT NULL
                  AND m.proxy IN (
                      SELECT member_id
                      FROM Elections
                      WHERE variant_id = ?
                        AND status IN ('valid', 'lose', 'win')
                  )
                  AND m.id NOT IN (
                      SELECT member_id
                      FROM Elections
                      WHERE variant_id IN (
                          SELECT id
                          FROM Variants
                          WHERE voting_id = (
                              SELECT voting_id
                              FROM Variants
                              WHERE id = ?
                          )
                      )
                  )
            ''', (variant_id, variant_id))

            result = await cursor.fetchone()
            if result:
                amount, = result
                logger.info(f"Количество голосов через представителей за variant_id={variant_id}: {amount}")
                return int(amount)
            else:
                logger.info(f"Для variant_id={variant_id} нет голосов через представителей.")
                return None

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при подсчете голосов через представителей: {e}\n{traceback.format_exc()}")
            raise

# Функция выбора варианта при голосовании
@log_function_call
async def election(member_id, variant_id):
    time_election = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    voting_id = await extract_voting_id(variant_id)
    old_elect = await past_choise(member_id, voting_id)

    async with AsyncDatabase(path_db) as cursor:
        try:
            # Проверяем статус голосования
            await cursor.execute('''
                SELECT voting_status FROM Votings WHERE id = ?
            ''', (voting_id,))
            result = await cursor.fetchone()

            if result is None:
                logger.error(f"Голосование с voting_id={voting_id} не найдено.")
                return False, "Не удалось получить статус голосования."

            voting_status, = result  # Распаковываем результат

            if voting_status == 'add_variants':
                answer = (False, 'Голосование ещё не началось')
            elif voting_status == 'completed':
                answer = (False, 'Голосование уже закончилось')
            elif voting_status in ['ongoing', 'confirmation']:
                # Проверяем статус варианта
                await cursor.execute('''
                    SELECT variant_status FROM Variants WHERE id = ?
                ''', (variant_id,))
                variant_result = await cursor.fetchone()

                if variant_result is None:
                    logger.error(f"Вариант с variant_id={variant_id} не найден.")
                    return False, "Не удалось получить статус варианта."

                variant_status, = variant_result  # Распаковываем результат

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

            # Проверяем статус пользователя
            if 'votist' not in await extract_status(member_id):
                str1 = (
                    f"{answer[1]}\n"
                    "Обращаем ваше внимание на то, что ваш голос не учитывается при подсчете.\n"
                    "Возможно, ваша личность не подтверждена регистратором или вы не выбрали представителя."
                )
                flag = answer[0]
                answer = (flag, str1)

            return answer

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при выборе варианта: {e}\n{traceback.format_exc()}")
            raise

# Функция перевода вариантов в статус "проигравший" (loser)
# Заодно отданные за проигравший вариант голоса отмечаются как lose
@log_function_call
async def lose_variant(losers, voting_id=None, result=None, stager=None):
    if not losers:
        logger.info("Нет проигравших вариантов.")
        flag = False
        return flag
    time_lose = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not voting_id:
        voting_id = extract_voting_id(losers[0])


    async with AsyncDatabase(path_db) as cursor:
        try:
            # Присваиваем проигравшему варианту статус loser и записываем число голосов
            for item in losers:
                if not result:
                    dir_votes = await count_directly_votes(item) # решающие голоса, поданные за вариант напрямую
                    proxy_votes = await count_proxy_votes(item)   #решающие голоса, поданные через представителя
                    empty_votes = await count_directly_empty_votes(item)   # нерешающие голоса
                else:
                    dir_votes = result[item][1]
                    proxy_votes = result[item][0] - result[item][1]
                    empty_votes = result[item][2]

                await cursor.execute(
                    '''
                    UPDATE Variants SET variant_status = 'loser',  directly_votes = ?, proxy_votes = ?,
            empty_votes = ?    WHERE id = ?
            ''', (dir_votes, proxy_votes, empty_votes, item )
                )

                # Присваиваем голосам, отданным за проигравшиq вариант статус lose
                await cursor.execute(
                    '''
                    UPDATE Elections SET status = 'lose' WHERE variant_id = ? AND status = 'valid'
                    ''', (item,)
                )
            logger.info(f"Проигравшие варианты {losers} записаны в БД")
            flag = True

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при записи проигравшего варианта: {e}\n{traceback.format_exc()}")
            raise


# Функция перевода вариантa в статус "победитель" (winner)
# производим запись в таблицу голосований и в журнал регистрации
@log_function_call
async def win_variant(winner_id, voting_id=None, result=None, stager=None):
    time_win = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not voting_id:
        voting_id = extract_voting_id(winner_id)
    if not result:
        dir_votes = await count_directly_votes(winner_id) # решающие голоса, поданные за вариант напрямую
        proxy_votes = await count_proxy_votes(winner_id)   #решающие голоса, поданные через представителя
        empty_votes = await count_directly_empty_votes(winner_id)   # нерешающие голоса
    else:
        dir_votes = result[1]
        proxy_votes = result[0] - result[1]
        empty_votes = result[2]
    async with AsyncDatabase(path_db) as cursor:
        try:

            # Присваиваем выигравшему варианту статус winner и записываем число отданных за него голосов
            await cursor.execute(
                '''
                UPDATE Variants SET variant_status = 'winner', directly_votes = ?, proxy_votes = ?,
                empty_votes = ?    WHERE id = ?
                ''', (dir_votes, proxy_votes, empty_votes, winner_id )
            )
            # # Присваиваем голосам, отданным за победивший вариант статус win
            # await cursor.execute(
            #     '''
            #     UPDATE Elections SET status = 'win' WHERE variant_id = ? AND status = 'valid'
            #     ''', (winner_id,)
            # )
            #Присваиваем статус голосованию "Завершенное" и указываем вариант-победитель.
            await cursor.execute(
                """
                UPDATE Votings SET result = ?, time_completed = ?,
                voting_status = ? WHERE id = ?
                """, (winner_id, time_win, 'completed', voting_id)
            )


            await cursor.execute(
                '''
                INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                VALUES (?,?,?,?,?)
                ''', ('voting', voting_id, stager, 'completed', time_win)
            )

            logger.info(f"Победивший вариант записан: {winner_id}")



        except aiosqlite.Error as e:
            logger.error(f"Ошибка при записи про промежуточного этапа голосования: {e}\n{traceback.format_exc()}")
            raise


# Функция удаления варианта. Применяется на стадии добавления вараинта (на случай идентичных вариантов, например)
@log_function_call
async def delete_variant(variant_id, admin=None):
    time_reg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with AsyncDatabase(path_db) as cursor:
        try:

            # Присваиваем удаляему варианту статус invalid
            await cursor.execute(
                '''
                UPDATE Variants SET variant_status = 'invalid'  WHERE id = ?
                ''', (variant_id, )
            )
            # Присваиваем голосам, отданным за удаленный вариант статус (хотя их не должно быть) статус lose
            await cursor.execute(
                '''
                UPDATE Elections SET status = 'lose' WHERE variant_id = ?
                ''', (variant_id,)
            )

            await cursor.execute(
                '''
                INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                VALUES (?,?,?,?,?)
                ''', ('variant', variant_id, admin, 'delete', time_reg)
            )

            logger.info(f"Удаление варианта записано: {variant_id}")



        except aiosqlite.Error as e:
            logger.error(f"Ошибка при записи про промежуточного этапа голосования: {e}\n{traceback.format_exc()}")
            raise

# Функция завершения промежуточного этапа голосования. Переводит в статус "loser" наименее популярные варианты.
# Оставшиеся варианты должны в сумме набирать 50% голосов от имеющих право голоса.
# Возвращает кортеж из ID проигравших вариантов.
@log_function_call
async def voting_stage(voting_id, club_id=None, stager=None):
    # Проверяем club_id
    if club_id is None:
        club_id = await extract_group_id(voting_id)
        if club_id is None:
            logger.error(f"Не удалось определить club_id для voting_id={voting_id}.")
            return {'success': False, 'message': "Не удалось определить клуб."}

    # Получаем информацию о голосовании
    voting_info = await get_voting_info(voting_id)
    if voting_info is None:
        logger.error(f"Голосование с voting_id={voting_id} не найдено.")
        return {'success': False, 'message': "Голосование не найдено."}

    time_stage = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')
    if not variants:
        return {'success': False, 'message': 'У голосования не найдены варианты'}
    s_votist = await count_votist(club_id) or 0  # Если None, используем 0

    # Подсчитываем число голосов за каждый вариант
    res = {}  # Словарь результатов голосования
    sum_vote = 0  # Сумма решающих голосов

    for item in variants:
        dir_votes = await count_directly_votes(item['id']) or 0  # Если None, используем 0
        proxy_votes = await count_proxy_votes(item['id']) or 0  # Если None, используем 0
        empty_votes = await count_directly_empty_votes(item['id']) or 0  # Если None, используем 0
        res[item['id']] = (dir_votes + proxy_votes, dir_votes, empty_votes, item['title'])
        sum_vote += dir_votes + proxy_votes

    logger.info(f"Результаты голосования для voting_id={voting_id}: {res}")
    logger.info(f"Суммарное количество голосов: {sum_vote}")

    # Если проголосовало более половины решающих голосов, отсекаем непопулярные варианты
    if sum_vote * 2 > s_votist:
        a = s_votist / 2
        k = None

        # Сортируем варианты в порядке убывания результата
        sorted_res = sorted(res.items(), key=lambda item: item[1][0], reverse=True)

        # Вычитаем результаты вариантов из половины общего числа голосов
        for i in range(len(sorted_res)):
            a -= sorted_res[i][1][0]
            if a < 0:
                k = sorted_res[i][1][0]  # Значение "отсечения"
                break

        losers = [item for item in res if res[item][0] < k]
        winners = [item for item in res if res[item][0] >= k]

        logger.debug(f"Проигравшие варианты:\n{losers}\nОставшиеся варианты:\n{winners}")

        # Записываем проигравшие варианты в базу данных
        await lose_variant(losers, voting_id=voting_id, result=res, stager=stager)

        async with AsyncDatabase(path_db) as cursor:
            try:
                if losers:
                    await cursor.execute(
                        '''
                        INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                        VALUES (?, ?, ?, ?, ?)
                        ''', ('voting', voting_id, stager, 'stage', time_stage)
                    )
                    logger.info(f"Произведена запись в журнал регистраций")
                    los_titles = [res[item][3] for item in losers]  # Список названий проигравших вариантов
                    losers_str = '\n'.join(los_titles)
                    flag = True
                    text = f'''Прошло промежуточное подведение итогов в голосовании:\n
                               {voting_info.get('title', 'Название не найдено')}\n\n
                               Осталось {len(winners)} вариантов.\n
                               Выбыли варианты:\n{losers_str}'''
                else:
                    logger.info("Нет проигравших вариантов.")
                    flag = False
                    text = 'Нет проигравших вариантов'

                # Если остался один победивший вариант, завершаем голосование
                if len(winners) == 1:
                    winner_id = winners[0]
                    result = await voting_complete(voting_id, stager)
                    logger.info(f"Голосование завершено. Победивший вариант: {winner_id}, Проигравшие варианты: {losers}")
                    flag = True
                    winner_title = res[winner_id][3]
                    text = result.get('message', 'Информация о результате не найдена')

                # Если победивших вариантов два - переводим в финал
                elif len(winners) == 2:
                    await cursor.execute(
                        '''
                        INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                        VALUES (?, ?, ?, ?, ?)
                        ''', ('voting', voting_id, stager, 'final', time_stage)
                    )
                    flag = True
                    win_titles = [res[item][3] for item in winners]
                    win_str = '\n'.join(win_titles)
                    text = f'Осталось два действительных варианта:\n{win_str},\nпереводим голосование в финал.'

            except aiosqlite.Error as e:
                logger.error(f"Ошибка при завершении промежуточного этапа голосования: {e}\n{traceback.format_exc()}")
                flag = False
                text = f"Ошибка при завершении промежуточного этапа голосования: {e}"
                raise
    else:
        logger.info("Сумма голосов недостаточна для завершения промежуточного этапа.")
        flag = False
        text = 'Сумма голосов недостаточна для завершения промежуточного этапа.'

    result = {'success': flag, 'message': text}
    return result




# Функция создания финального этапа голосования (где голосуется два варианта или больше, если есть варианты,
# которые набрали столько же, сколько второй)
@log_function_call
async def voting_final(voting_id, finaler=None):
    time_final = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')

    flag = True

    if not variants:
        logger.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        flag = False
        text = 'Нет действительных вариантов'

    elif len(variants) == 1:
        logger.info(f"У voting_id={voting_id} только один действительный вариант.")
        flag = False
        text = f'Остался только один действительный вариант {variants}. Завершите голосование или запустите утверждение итогов голосования.'

    elif len(variants) == 2:
        logger.info(f"У voting_id={voting_id} только два действительных варианта. Переводим их в финал.")
        flag = True
        text = f'Осталось только два действительных варианта {variants}'

    else:
        res = {}
        for item in variants:
            dir_votes = await count_directly_votes(item['id']) or 0  # Если None, используем 0
            prox_votes = await count_proxy_votes(item['id']) or 0  # Если None, используем 0
            empt_votes = await count_directly_empty_votes(item['id']) or 0  # Если None, используем 0
            res[item['id']] = (dir_votes + prox_votes, dir_votes, empt_votes)

        sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)

        # Находим значение "отсечения"
        k = sorted_res[1][1] if len(sorted_res) > 1 else (0, 0, 0)
        losers = [item for item in res if res[item] < k]
        winners = [item for item in res if res[item] >= k]
        text = f'В финал голосования вышли варианты {winners}'
        flag = True

        # Записываем проигравшие варианты в БД
        await lose_variant(losers, voting_id=voting_id, result=res, stager=finaler)

    async with AsyncDatabase(path_db) as cursor:
        try:
            if flag:
                await cursor.execute(
                    '''
                    INSERT INTO Registrations(object_type, object_id, registrator, status, time_reg)
                    VALUES (?, ?, ?, ?, ?)
                    ''', ('voting', voting_id, finaler, 'final', time_final)
                )

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при создании финального этапа голосования: {e}\n{traceback.format_exc()}")
            flag = False
            text = f"Ошибка при создании финального этапа голосования: {e}"
            raise

    result = {'success': flag, 'message': text}
    return result


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
    voting_info = await get_voting_info(voting_id) or {}  # Если None, используем пустой словарь
    s_votist = await count_votist(club_id) or 0  # Если None, используем 0

    if not variants:
        logger.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        return {
            'success': False,
            'message': 'У голосования нет действительных вариантов',
            'winner_id': None,
            'winner_title': None,
            'winner_res': None
        }

    res = {}
    for item in variants:
        dir_votes = await count_directly_votes(item['id']) or 0  # Если None, используем 0
        prox_votes = await count_proxy_votes(item['id']) or 0  # Если None, используем 0
        empt_votes = await count_directly_empty_votes(item['id']) or 0  # Если None, используем 0
        res[item[0]] = (dir_votes + prox_votes, dir_votes, empt_votes)

    sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
    winner_id = sorted_res[0][0]
    winner_res = sorted_res[0][1]

    # Ищем, нет ли других вариантов с максимальным результатом.
    # Если есть - победителем назначается вариант, созданный раньше.
    i = 1
    flag = True if i < len(sorted_res) else False

    while flag:
        if sorted_res[i][1] == winner_res:
            if sorted_res[i][0] < winner_id:
                winner_id = sorted_res[i][0]
            i += 1
        else:
            flag = False

    # Делаем список ID проигравших вариантов (все, кроме winner_id)
    losers = [item['id'] for item in variants if item['id'] != winner_id]

    # Находим название победившего варианта
    winner_title = next((item['title'] for item in variants if item['id'] == winner_id), None)

    # Записываем в БД проигравшие варианты
    await lose_variant(losers, voting_id=voting_id, result=res, stager=finisher)

    # Если вариант-победитель набрал менее половины действительных голосов,
    # запускаем процедуру утверждения итогов голосования.
    # Но не в случае, если статус голосования уже 'confirmation'.
    if (winner_res[0] * 2 < s_votist) and voting_info.get('voting_status') != 'confirmation':
        await confirmation_of_voting_results(voting_id, winner_id)
        text = f'''Победил вариант {winner_title}.\n
        Его результат:\n
        Всего голосов "за": {winner_res[0]}\n
        Из них отдано напрямую: {winner_res[1]}\n
        Отдано недействительных голосов: {winner_res[2]}\n
        Он набрал менее 50% действительных голосов.\n
        Запущена процедура утверждения итогов голосования.'''
        success = True
    else:
        try:
            await win_variant(winner_id, voting_id=voting_id, result=res[winner_id], stager=finisher)
            logger.info(f"Победивший вариант: {winner_id}, Проигравшие варианты: {losers}")
            text = f'''Победил вариант {winner_title}.\n
            Его результат:\n
            Всего голосов "за": {winner_res[0]}\n
            Из них отдано напрямую: {winner_res[1]}\n
            Отдано недействительных голосов: {winner_res[2]}\n
            {'Он набрал более 50% действительных голосов.' if (winner_res[0] * 2 > s_votist) else 'Он набрал менее 50% действительных голосов.'}\n
            Всего действительных голосов в группе: {s_votist}\n
            Голосование завершено.'''
            success = True

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при завершении голосования: {e}\n{traceback.format_exc()}")
            success = False
            raise

    return {
        'success': success,
        'message': text,
        'winner_id': winner_id,
        'winner_title': winner_title,
        'winner_res': winner_res
    }

# Функция запуска утверждения итогов голосования.
# Добавляет вариант "Лучше не принимать никакого решения". Переводит голосование в статус 'confirmation'
@log_function_call
async def confirmation_of_voting_results(voting_id, winner_id):
    logger.info(f'Запущено утверждение итогов голосования {voting_id}')
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    author = 0
    title = LEXICON.get("Don't make any decision","Don't make any decision")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute(
                '''
                UPDATE Votings SET voting_status = 'confirmation' WHERE id = ?
                ''', (voting_id,)
            )
            await cursor.execute(
                '''
                INSERT OR IGNORE INTO Variants(voting_id, author, title, variant_status, text, time_create)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (voting_id, author, title, 'valid', title, time_create)
            )
# !!!!!!!!!!!!!!!!!!
# Записываем в журнал регистрации
# !!!!!!!!!!!!!!!!!!
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при запуске утверждения итогов голосования: {e}\n{traceback.format_exc()}")
            raise



# Функция завершения утврждения голосования. Определяет вариант - победитель (или отсутствие победителя).
# При прочих равных (что вряд ли) побеждает тот вариант, который создан раньше.
@log_function_call
async def confirmation_of_voting_results_stop(voting_id, finisher=None):
    time_finish = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    variants = await list_of_variants(voting_id, 'valid')
    club_id = await extract_group_id(voting_id)

    if not variants:
        logger.info(f"Для voting_id={voting_id} нет действительных вариантов.")
        return {
            'success': False,
            'message': 'У голосования нет действительных вариантов',
            'winner_id': None,
            'winner_title': None,
            'winner_res': None
        }

    res = {}
    for item in variants:
        dir_votes = await count_directly_votes(item['id']) or 0  # Если None, используем 0
        prox_votes = await count_proxy_votes(item['id']) or 0  # Если None, используем 0
        empt_votes = await count_directly_empty_votes(item['id']) or 0  # Если None, используем 0
        res[item['id']] = (dir_votes + prox_votes, dir_votes, empt_votes)

    sorted_res = sorted(res.items(), key=lambda item: item[1], reverse=True)
    winner_id = sorted_res[0][0]
    winner_res = sorted_res[0][1]

    # Ищем, нет ли других вариантов с максимальным результатом.
    # Если есть - победителем назначается вариант, созданный раньше.
    i = 1
    flag = True if i < len(sorted_res) else False

    while flag:
        if sorted_res[i][1] == winner_res:
            if sorted_res[i][0] < winner_id:
                winner_id = sorted_res[i][0]
            i += 1
        else:
            flag = False

    # Делаем список ID проигравших вариантов (все, кроме winner_id)
    losers = [item['id'] for item in variants if item['id'] != winner_id]

    # Находим название победившего варианта
    winner_title = next((item['title'] for item in variants if item['id'] == winner_id), None)

    try:
        # Записываем в БД проигравшие варианты
        if losers:
            await lose_variant(losers, voting_id=voting_id, result=res, stager=finisher)

        # Записываем в БД победителя и завершаем голосование
        if winner_id:
            await win_variant(winner_id, voting_id=voting_id, result=res[winner_id], stager=finisher)

        logger.info(f"Победивший вариант: {winner_id}, Проигравшие варианты: {losers}")
        text = f'''Победил вариант {winner_title}.\n
        Его результат:\n
        Всего голосов "за": {winner_res[0]}\n
        Из них отдано напрямую: {winner_res[1]}\n
        Отдано недействительных голосов: {winner_res[2]}\n
        Голосование завершено.'''
        success = True

    except aiosqlite.Error as e:
        logger.error(f"Ошибка при завершении голосования: {e}\n{traceback.format_exc()}")
        success = False
        raise

    return {
        'success': success,
        'message': text,
        'winner_id': winner_id,
        'winner_title': winner_title,
        'winner_res': winner_res
    }


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
                logger.info(f"Статус голосования voting_id={voting_id}: {voting_status}")
                return voting_status
            else:
                logger.info(f"Для voting_id={voting_id} не найдено статуса.")
                return None
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при получении статуса голосования: {e}\n{traceback.format_exc()}")
            raise

@log_function_call
async def extract_proxy_choice(member_id, voting_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''
                SELECT variant_id FROM Elections
                WHERE member_id IN (SELECT proxy FROM Members WHERE id = ?)
                AND variant_id IN (SELECT id FROM Variants WHERE voting_id = ?)
                AND status IN ('valid','loser','win')
            ''', (member_id, voting_id))
            result = await cursor.fetchall()
            if result:
                choise = [item[0] for item in result]
            else:
                choise = None
            logger.info(f"Результат выборки вариантов для member_id={member_id}, voting_id={voting_id}: {result}")
            return choise
        except aiosqlite.Error as e:
            logger.error(f"Ошибка при проверке прошлых выборов: {e}\n{traceback.format_exc()}")
            raise


# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#      Функция возобновления голосования
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!