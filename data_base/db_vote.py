# ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ БАЗЫ ДАННЫХ С ГОЛОСОВАНИЕМ

from db_func import *

# Создание нового голосования. Создается название голосования и описание, также
# может быть введен тип голосования и ссылка. Варианты добавляются позже.
def new_vote(club_id, creator, title, text = None,
             vote_type = 'usual', vote_status = None, link_id = None):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(title) > 40:
        flag = False
        answ_str = ('Название не должо быть длиннее 40 символов'
                    'Придумайте другое название')

    else:
        with Database(path_db) as cursor:
            cursor.execute(
            """
            SELECT title FROM Votes WHERE club_id = ? AND vote_status <> 'finished'
            """,(club_id,)
            )
            titles = cursor.fetchall()
            if (title,) not in titles:
                print('Такого голосования еще нет')
                cursor.execute(
            '''INSERT INTO Votes(club_id, creator, title, text, time_create, vote_type, vote_status, link_id)
            VALUES (?,?,?,?,?,?,?,?)''',(club_id, creator, title, text, time_create, vote_type, vote_status, link_id)
            )
                answ_str = 'Голосование добавлено'
                flag = True
            else:
                answ_str = ('Уже есть идущее голосование с таким названием.'
                       'Придумайте другое название')
                flag = False
    print(flag, answ_str)
    return (flag,answ_str)

# Создание варианта для голосования. Добавляется только в голосования
# со статусом ожидания вариантов.
# В БД вносится автор (member_id)  заголовок варианта, текст варианта,
# если есть  - ссылка
# Возвращает комментарий по итогам добавления
def new_variant(vote_id, author, title, text = None, link_id = None):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if len(title) > 40:
        flag,answ_str = 'too_long','Название не должо быть длиннее 40 символов'
    else:
        with Database(path_db) as cursor:
            cursor.execute(
            """
            SELECT vote_status FROM Votes WHERE id = ?
            """,(vote_id,)
            )
            status, = cursor.fetchone()
            if status == 'add_variants':
                print('Добавление вариантов у голосования возможно')
                cursor.execute(
            """
         SELECT title FROM Variants WHERE vote_id = ?
            """,
            (vote_id,)
            )
                titles = cursor.fetchall()
                print(titles)
                if (title,) not in titles:
                    print('Такого варианта еще нет')
                    cursor.execute(
            '''
            INSERT INTO Variants(vote_id, author, title, text, time_create, link_id)
            VALUES (?,?,?,?,?,?)
            ''',(vote_id, author, title, text, time_create, link_id)
            )
                    answ_str = 'Вариант добавлен'
                    flag = 'OK'
                else:
                    answ_str = '''Вариант с таким названием уже существует.
Придумайте другое название'''
                    flag = 'double'
                    print(answ_str)
            else:
                answ_str = 'К этому голосованию нельзя добавить варианты'
                flag = 'too_late'
                print(answ_str)
    return(flag,answ_str)



# Функция старта голосования. Меняем статус голосования на 'ongoing'
# Указываем, кто запустил голосование (если не автоматически)

def vote_start(vote_id, starter = None):
    time_start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            UPDATE Votes SET vote_status = ?, starter = ?, time_start = ?
            WHERE id = ?
            ''', ('ongoing', starter, time_start, vote_id)
                )



# Функция возвращает ID голосования по ID варианта
def extract_vote_id(variant_id):
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT vote_id FROM Variants WHERE id = ?
            ''', (variant_id,)
                )
        result = cursor.fetchone()
            #print(answ)
        if result:
            vote_id, = result
            return(vote_id)
        else: return None

# Функция выясняет, за какие варианты в данном голосовании голосовал (лично) пользователь
# Возвращает ID вариантов (список кортежей с одним членом) или None
def past_choise(member_id, vote_id):
    with Database(path_db) as cursor:
        cursor.execute('''
        SELECT id FROM Elections
        WHERE member_id = ? AND variant_id IN
        (SELECT id FROM Variants
        WHERE vote_id = ?) AND status = 'valid'
            '''
            ,(member_id, vote_id)
            )
        result = cursor.fetchall()
        # print(result)
        return result

# Функция подсчета голосов, отданых за вариант лично теми, кто имеет право голоса
def count_directly_votes(variant_id):
    with Database(path_db) as cursor:
        cursor.execute('''
           SELECT COUNT (*) FROM Members WHERE id IN
           (SELECT member_id FROM Elections WHERE variant_id = ? AND status = 'valid')
           AND id IN
           (SELECT member_id FROM  Status WHERE status  = 'votist')
           '''
            ,(variant_id, )
            )
        result = cursor.fetchone()
            #print(answ)
        if result:
            amount, = result
            return(int(amount))
        else: return None


# Функция подсчета голосов, отданых за вариант лично теми, кто не имеет право голоса
def count_directly_empty_votes(variant_id):
    with Database(path_db) as cursor:
        cursor.execute('''
           SELECT COUNT (*) FROM Members WHERE id IN
           (SELECT member_id FROM Elections WHERE variant_id = ? AND status = 'valid')
           AND id NOT IN
           (SELECT member_id FROM  Status WHERE status = 'votist')
           '''
            ,(variant_id, )
            )
        result = cursor.fetchone()
            #print(answ)
        if result:
            amount, = result
            return(int(amount))
        else: return None

# Функция подсчета голосов, отданых за вариант через представителей
def count_proxy_votes(variant_id):
    with Database(path_db) as cursor:
        cursor.execute('''
            SELECT COUNT (*) FROM Members WHERE proxy IN
            (SELECT member_id FROM Elections WHERE variant_id = ?
            AND status = 'valid')
            AND id NOT IN
            (SELECT member_id FROM Elections WHERE status = 'valid'
            AND variant_id IN
           (SELECT id FROM Variants WHERE Vote_id IN
           (SELECT vote_id FROM Variants WHERE id = ?)))
            AND id IN
            (SELECT member_id FROM  Status WHERE status  = 'votist')

            '''
            ,(variant_id,variant_id)
            )
        result = cursor.fetchone()
            #print(answ)
        if result:
            amount, = result
            return(int(amount))
        else: return None

# Функция выбора варианта при голосовании
def election(member_id,variant_id):
    time_election = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vote_id = extract_vote_id(variant_id)
    old_elect = past_choise(member_id, vote_id)
    with Database(path_db) as cursor:
        cursor.execute(''' SELECT vote_status FROM Votes WHERE id = ?
            '''
            ,(vote_id,)
            )
        result = cursor.fetchone()
        print(result)
        vote_status, = result
        if vote_status == 'add_variants':
            answer = (False, 'Голосование ещё не началось')
        elif vote_status == 'closed':
            answer = (False, 'Голосование уже закончилось')
        elif vote_status == 'ongoing':
            cursor.execute(
            '''
          SELECT variant_status FROM Variants WHERE id = ?
            '''
            ,(variant_id,)
            )
            variant_status, = cursor.fetchone()
            if variant_status == 'loser':
                answer = (False, 'Этот вариант уже выбыл из голосования')
            else:
#            Делаем запись о голосовании в таблицу выборов
                cursor.execute(
            '''
            INSERT INTO Elections(member_id, variant_id, time_election,status)
            VALUES (?,?,?,?)
            ''',(member_id, variant_id, time_election, 'valid')
            )
#             Меняем статус предыдущего выбора на 'invalid'
                if old_elect:
                    for item in old_elect:
                        cursor.execute(
            '''
            UPDATE Elections SET status = 'invalid' WHERE id = ?
            ''',(item[0],)
            )
                answer = (True, 'Ваш голос принят')
        else:
            answer = (False , 'Непонятен статус голосования')
    if 'votist' not in extract_status(member_id):
        str1 = answer[1]+'''\n Обращаем ваше внимание на то, что ваш голос не учитывается при подсчете.
Возможно, ваша личность не подтверждена регистратором.
Или вы не выбрали представителя.'''
        flag = answer[0]
        answer = (flag, str1)
    return answer