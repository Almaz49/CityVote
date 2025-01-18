import datetime

if __name__ == '__main__':
    from db_func import *
else:
    from data_base.db_func import *

# ФУНКЦИИ ВЗАИМОДЕЙСТВИЯ БАЗЫ ДАННЫХ С ГОЛОСОВАНИЕМ


# Создание нового голосования. Создается название голосования и описание, также
# может быть введен тип голосования и ссылка. Варианты добавляются позже.
def new_vote(club_id, creator, title, text = None,
             vote_type = 'usual', vote_status = 'add_variants', link_id = None):
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
def new_variant(vote_id, author, title,variant_status = 'valid', text = None, link_id = None):
    time_create = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if len(title) > 40:
        flag,answ_str = False,'Название не должо быть длиннее 40 символов'
    else:
        with Database(path_db) as cursor:
            cursor.execute(
            """
            SELECT vote_status FROM Votes WHERE id = ?
            """,(vote_id,)
            )
            status, = cursor.fetchone()
            if status == 'add_variants':
                # print('Добавление вариантов у голосования возможно')
                cursor.execute(
            """
         SELECT title FROM Variants WHERE vote_id = ?
            """,
            (vote_id,)
            )
                titles = cursor.fetchall()
                print(titles)
                if (title,) not in titles:
                    # print('Такого варианта еще нет')
                    cursor.execute(
            '''
            INSERT INTO Variants(vote_id, author, title, variant_status, text, time_create, link_id)
            VALUES (?,?,?,?,?,?,?)
            ''',(vote_id, author, title, variant_status, text, time_create, link_id)
            )
                    answ_str = 'Вариант добавлен'
                    flag = True
                else:
                    answ_str = '''Вариант с таким названием уже существует.
Придумайте другое название'''
                    flag = False
                    # print(answ_str)
            else:
                answ_str = 'К этому голосованию нельзя добавить варианты'
                flag = False
                # print(answ_str)
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

# Функция возвращает ID группы по ID голосования
def extract_group_id(vote_id):
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            SELECT club_id FROM Votes WHERE id = ?
            ''', (vote_id,)
                )
        result = cursor.fetchone()
            #print(answ)
        if result:
            club_id, = result
            return(club_id)
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

# Функция подсчета числа членов группы, имеющих право голоса
def count_votist(club_id):
    with Database(path_db) as cursor:
        cursor.execute('''
           SELECT COUNT (*) FROM Members WHERE id IN
           (SELECT id FROM Members WHERE club_id = ?)
           AND id IN
           (SELECT member_id FROM  Status WHERE status  = 'votist')
           '''
            ,(club_id, )
            )
        result = cursor.fetchone()
            #print(answ)
        if result:
            amount, = result
            return(int(amount))
        else: return None


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
        # print(result)
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

# Функция завершения промежуточного этапа голосования. Переводит в статус "loser" наименее популярные варианты.
# Оставшиеся варианты должны в сумме набирать 50% голосов от имеющих право голоса.
# Возвращает кортеж из ID проигравших вариантов.
def vote_stage(vote_id):
    variants = list_of_variants(vote_id,'valid')
    club_id = extract_group_id(vote_id)
    s_votist = count_votist(club_id)
    # подсчитываем число голосов, отданных за вариант (в виде кортежа): всего, напрямую, не имеющих права голоса
    res = {}
    sum_vote = 0
    # Делаем словарь, где ключ - ID варианта, а значение - кортеж результатов. Заодно подсчитываем суму отданных голосов
    for item in variants:
        dir = count_directly_votes(item[0])
        prox = count_proxy_votes(item[0])
        empt = count_directly_empty_votes(item[0])
        res[item[0]] = dir + prox, dir, empt
        sum_vote += dir+prox
    print(res)
    # Упорядочиваем словарь (он превращается в список кортежей)
    sorted_res = sorted(res.items(), key=lambda item: item[1],reverse = True)
    print(sorted_res)
    # Если сумма, отданная за варианты больше "кворума" в половину голосующих, ищем проигравшие варианты
    if sum_vote * 2 > s_votist:
        a = s_votist / 2
        k = 1
        # k - количество голосов, меньше которого варианты выбывают
        for i in range(len(sorted_res)):
            a -= sorted_res[i][1][0]
            if a < 0:
                k = sorted_res[i][1][0]
                break
    losers = []
    for item in res:
        if res[item][0] < k:
            losers.append((item,))
    if losers:
        with Database(path_db) as cursor:
            cursor.executemany(
            '''
            UPDATE Variants SET variant_status = 'loser' WHERE id = ?
            ''', losers
                )
        return list(zip(*losers))[0]
    else:
        return None

# Функция создания финального этапа голосования (где голосуется два варианта или больше, если есть варианты, которые набрали столькоо же, сколько второй)
def vote_final(vote_id):
    variants = list_of_variants(vote_id,'valid')
    # подсчитываем число голосов, отданных за вариант (в виде кортежа): всего, напрямую, не имеющих права голоса
    res = {}
    # Делаем словарь, где ключ - ID варианта, а значение - кортеж результатов. Заодно подсчитываем суму отданных голосов
    for item in variants:
        dir = count_directly_votes(item[0])
        prox = count_proxy_votes(item[0])
        empt = count_directly_empty_votes(item[0])
        res[item[0]] = dir + prox, dir, empt
    print(res)
    # Упорядочиваем словарь (он превращается в список кортежей). При одинаковом общем числе голосов - упорядочивается по прямым голосам, затем - по "пустым"
    sorted_res = sorted(res.items(), key=lambda item: item[1],reverse = True)
    print(sorted_res)
    k = sorted_res[1][1] # результат второго варианта в виде кортежа
    print('результат отсечения: ', k)
    losers = []
    for item in res:
        if res[item] < k:
            losers.append((item,))
    if losers:
        with Database(path_db) as cursor:
            cursor.executemany(
            '''
            UPDATE Variants SET variant_status = 'loser' WHERE id = ?
            ''', losers
                )
        return list(zip(*losers))[0]
    else:
        return None


# Функция завершения голосования. Определяет вариант - победитель.
# При прочих равных (что вряд ли) побеждает тот вариант, который создан раньше
def vote_finish(vote_id):
    variants = list_of_variants(vote_id,'valid')
    print(variants)
    if not variants:
        return(None,[])
    # подсчитываем число голосов, отданных за вариант (в виде кортежа): всего, напрямую, не имеющих права голоса
    res = {}
    # Делаем словарь, где ключ - ID варианта, а значение - кортеж результатов. Заодно подсчитываем суму отданных голосов
    for item in variants:
        dir = count_directly_votes(item[0])
        prox = count_proxy_votes(item[0])
        empt = count_directly_empty_votes(item[0])
        res[item[0]] = dir + prox, dir, empt
    print(res)
    # Упорядочиваем словарь (он превращается в список кортежей). При одинаковом общем числе голосов - упорядочивается по прямым голосам, затем - по "пустым"
    sorted_res = sorted(res.items(), key=lambda item: item[1],reverse = True)
    print(sorted_res)
    losers = []
    # Отрабатываем случай одинакового результата нескольких вариантов. Тогда выигрывает тот,
    # который раньше создан (у кого меньше ID)
    winner_id = sorted_res[0][0]
    winner_res = sorted_res[0][1]
    i = 1
    len_sr = len(sorted_res)
    if i+1 <= len_sr: flag = True
    while flag:
        if sorted_res[i][1]>=winner_res:
            if sorted_res[i][0] < time_1:
                winner_id = sorted_res[i][0]
                winner_res = sorted_res[i][1]
            i += 1
        else:
            flag = False
    # Делаем  проигравших вариантов статус loser
    for i in range(len(sorted_res)):
        if i > 0:
            losers.append((sorted_res[i][0],))
    if losers:
        with Database(path_db) as cursor:
            cursor.executemany(
            '''
            UPDATE Variants SET variant_status = 'loser' WHERE id = ?
            ''', losers
                )
    if winner_id:
        with Database(path_db) as cursor:
            cursor.execute(
            '''
            UPDATE Variants SET variant_status = 'winner' WHERE id = ?
            ''', (winner_id,)
                )
    with Database(path_db) as cursor:
        cursor.execute(
            '''
            UPDATE Votes SET vote_status = 'finshed' WHERE id = ?
            ''', (vote_id,)
                )
    return(winner_id,losers)




#       //////////////////////////////////////
#           Проверяем работу функций
#       \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

# print('losers: ', vote_final(3))
print(vote_finish(3))
