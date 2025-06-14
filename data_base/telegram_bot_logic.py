# Модуль telegram_bot_logic.
# Служит "прокладкой" между телеграм-ботом и функциями базы данных.
# Его функции принимают аргументом телеграм-ID, и обращаются к функциям,
# работающим с базой данных, отпарвляя им в качестве аргумента user_id и member_id
# Это нужно для того, чтобы при необходимости поменять базу данных,
# но не переписывать хэндлеры



import logging
from config_data.config import Config, load_config
from data_base.db_func import *
from data_base.db_member import *
from data_base.db_vote import *
from utils import log_function_call

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)




# Функция выяснения статуса участника по tg_id.
# Если участник с таким телеграм id не обнаружен,
# заносит его в БД в таблицы Users и Members (в колонке club_id записывается id группы данного бота),
# без статуса (что равнозначно статусу user). Если пользователь обнаружен, но не является участником группы -
# он заносится в список участников группы, которую обслуживает телеграм-бот.
# Возвращает список статусов типа ['admin', 'registrator']
# В каждом кортеже только один элемент. Кортежей столько, сколько статусов у участника.
# Функция используется в фильтрах для хендлеров
@log_function_call
async def status_member(tg_id):
    logger.info(f"Проверка статуса участника по tg_id={tg_id}")
    user_id = await extract_user_id(tg_id)

    if not user_id:
        logger.info(f"Создание нового пользователя с tg_id={tg_id}")
        await new_user_tg(tg_id)
        user_id = await extract_user_id(tg_id)
        await new_member(club_id, user_id)
        status = ['user']
    else:
        member_id = await extract_member_id(club_id, user_id)

        if not member_id:
            logger.info(f"Добавление пользователя с tg_id={tg_id} в группу")
            await new_member(club_id, user_id)
            status = ['user']
        else:
            status = await extract_status(member_id)

    logger.info(f"Статус участника с tg_id={tg_id}: {status}")
    return status


# # Функция создания нового голосования
# @log_function_call
# async def new_voting_tg(creator_tg_id, title, text=None, vote_type='usual', voting_status='add_variants'):
#     creatot_user_id, creator = await extract_user_member_id(creator_tg_id)
#     if creator:
#         result = await voting_create(club_id, creator, title, text, vote_type, voting_status)
#         logger.info(f"Создано новое голосование с creator_tg_id={creator_tg_id}: {result}")
#         return result
#     else:
#         logger.warning(f"Пользователь с tg_id={creator_tg_id} не является участником группы.")
#         return False, 'Вы не являетесь участником группы'

# Функция извлечения user_id и member_id по tg_id
@log_function_call
async def extract_user_member_id(tg_id: int):  # Добавляем club_id как параметр
    try:
        user_id = await extract_user_id(tg_id)
        if user_id:
            member_id = await extract_member_id(club_id, user_id)
            logger.info(f"Извлечен member_id={member_id} для tg_id={tg_id}")
            return user_id, member_id
        else:
            logger.info(f"Пользователь с tg_id={tg_id} не найден.")
            return None, None
    except Exception as e:
        logger.error(f"Ошибка при извлечении member_id: {e}")
        return None, None

# Функция извлечения данных о пользователе по его tg_id
# Используется при создании нового регистратора
# Возвращает (flag, ans_str). Если flag == true, значит участник может быть назначен регистратором.
# ans_str - комментарий, который выдается по итогу извлечения данных
@log_function_call
async def extract_new_registrator_data(tg_id):
    user_id = await extract_user_id(tg_id)
    member_id = await extract_member_id(club_id, user_id)

    if not member_id:
        flag = False
        ans_str = 'Нет такого участника. Попробуйте снова.'
        logger.warning(f"Участник с tg_id={tg_id} не найден: {ans_str}")
        return flag, ans_str

    user_data = await get_profile(member_id=member_id)
    if user_data:
        ans_str = (f"Имя: {user_data.get('first_name')}, Фамилия: {user_data.get('last_name')},\n"
                   f"Телефон: {user_data.get('tg_phone_number')}\nПсевдоним: {user_data.get('username')}")
    else:
        # Если user_data пустое, устанавливаем ans_str в значение по умолчанию
        ans_str = "Данные профиля участника не найдены."

    has_registator = await check_member_status(member_id=member_id, target_status='registrator')
    has_superregistator = await check_member_status(member_id=member_id, target_status='superregistrator')
    if has_registator or has_superregistator:  # если пользователь регистратор или суперрегистратор
        flag = False
        ans_str += '\nЭтот участник уже регистратор.'
    else:
        flag = True

    logger.info(f"Результат проверки на регистрацию для tg_id={tg_id}: {flag}, {ans_str}")
    return flag, ans_str



# Присвоение нового статуса - в качестве аргументов функции tg_id регистратора и участника группы
@log_function_call
async def new_status_tg(registrator_tg_id, member_tg_id, status, token_id=None):
    ans_str = ''
    if registrator_tg_id:
        registrator_user_id = await extract_user_id(registrator_tg_id)
        if not registrator_user_id:
            ans_str += 'Нет такого регистратора.'
            logger.warning(f"Не найден регистратор с tg_id={registrator_tg_id}: {ans_str}")
            return False, ans_str

        registrator = await extract_member_id(club_id, registrator_user_id)
        if not registrator:
            ans_str += 'Нет такого регистратора.'
            logger.warning(f"Не найден участник с member_id={registrator_user_id} в группе {club_id}: {ans_str}")
            return False, ans_str
    else:
        registrator = None

    user_id = await extract_user_id(member_tg_id)
    if not user_id:
        ans_str += 'Нет такого участника.'
        logger.warning(f"Не найден пользователь с tg_id={member_tg_id}: {ans_str}")
        return False, ans_str

    member_id = await extract_member_id(club_id, user_id)
    if not member_id:
        ans_str += 'Нет такого участника.'
        logger.warning(f"Не найден участник с user_id={user_id} в группе {club_id}: {ans_str}")
        return False, ans_str

    try:
        await new_status(registrator, member_id, status, token_id)
        logger.info(f"Присвоен новый статус '{status}' участнику с tg_id={member_tg_id} от регистратора с tg_id={registrator_tg_id}")
        ans_str += f"Присвоен новый статус '{status}' участнику с tg_id={member_tg_id} от регистратора с tg_id={registrator_tg_id}"
        return True, ans_str
    except Exception as e:
        logger.error(f"Ошибка при присвоении статуса: {e}")
        ans_str += f"Ошибка при присвоении статуса: {str(e)}"
        return False, ans_str

# # Создание нового голосования
# @log_function_call
# async def new_voting_tg(creator_tg_id, title, text=None, vote_type='usual', voting_status='add_variants'):
#     creator_user_id = await extract_user_id(creator_tg_id)
#     if not creator_user_id:
#         logger.warning(f"Не найден пользователь с tg_id={creator_tg_id}")
#         return False, 'Вы не являетесь участником группы'

#     creator = await extract_member_id(club_id, creator_user_id)
#     if not creator:
#         logger.warning(f"Пользователь с tg_id={creator_tg_id} не является участником группы")
#         return False, 'Вы не являетесь участником группы'

#     result = await voting_create(club_id, creator, title, text=text, voting_type=vote_type, voting_status=voting_status)
#     logger.info(f"Создано новое голосование с creator_tg_id={creator_tg_id}: {result}")
#     return result

# Создание варианта для голосования. Добавляется в голосования со статусом ожидания вариантов.
# В БД вносится автор, заголовок варианта, текст варианта, если есть и мб - ссылка
@log_function_call
async def new_variant_tg(voting_id, creator_tg_id, title, text=None):
    user_id = await extract_user_id(creator_tg_id)
    if not user_id:
        logger.warning(f"Не найден пользователь с tg_id={creator_tg_id}")
        return False, 'Вы не являетесь участником группы'

    author = await extract_member_id(club_id, user_id)
    if not author:
        logger.warning(f"Пользователь с tg_id={creator_tg_id} не является участником группы")
        return False, 'Вы не являетесь участником группы'

    result = await variant_create(voting_id, author, title, text=text)
    logger.info(f"Добавлен новый вариант для голосования voting_id={voting_id} от tg_id={creator_tg_id}: {result}")
    return result

# Извлечение статусов участника группы (отдает список статусов)
@log_function_call
async def extract_status_tg(tg_id):
    user_id = await extract_user_id(tg_id)
    if not user_id:
        logger.warning(f"Не найден пользователь с tg_id={tg_id}")
        return None

    member_id = await extract_member_id(club_id, user_id)
    if not member_id:
        logger.warning(f"Пользователь с tg_id={tg_id} не является участником группы")
        return []

    status = await extract_status(member_id)
    logger.info(f"Статусы участника с tg_id={tg_id}: {status}")
    return status


# Функция извлечения списка участников с указанным статусом
@log_function_call
async def list_of_members_tg(status):
    try:
        members = await list_of_members(club_id, status)
        logger.info(f"Извлечены участники для club_id={club_id} с status={status}: {members}")
        return members
    except Exception as e:
        logger.error(f"Ошибка при извлечении участников: {e}")
        raise



# Функция выбора представителя. Принимает в качестве аргумента tg_id пользователя,
# который доверяет голос и member_id представителя
@log_function_call
async def trust_tg(tg_id, proxy_tg_id):
    try:
        if not isinstance(tg_id, int) or not isinstance(proxy_tg_id, int):
            raise ValueError("tg_id and proxy_tg_id must be integers")

        logger.info(f"Вызвана функция trust_tg")
        user_id, member_id = await extract_user_member_id(tg_id)
        proxy_user_id, proxy_member_id = await extract_user_member_id(proxy_tg_id)

        if member_id is None or proxy_member_id is None:
            logger.error("Invalid member_id or proxy_member_id")
            return False, "Invalid member or proxy ID"

        try:
            result = await trust(member_id, proxy_member_id)
        except Exception as e:
            logger.error(f"Ошибка при назначении представителя: {e}")
            return False, f"Ошибка при назначении представителя: {str(e)}"

        logger.info(f"Пользователь  с tg_id {tg_id} выбрал представителем учатника с tg_id {proxy_tg_id}")
        return True, result
    except aiosqlite.Error as db_error:
        logger.error(f"Ошибка базы данных при выборе представителя пользователем {tg_id}: {db_error}")
        return False, f"Ошибка базы данных: {str(db_error)}"
    except ValueError as value_error:
        logger.error(f"Ошибка значения при выборе представителя пользователем {tg_id}: {value_error}")
        return False, f"Ошибка значения: {str(value_error)}"
    except Exception as e:
        logger.error(f"Произошла неизвестная ошибка при выборе представителя пользователем {tg_id}: {e}")
        return False, f"Произошла неизвестная ошибка: {str(e)}"

# Функция выбора варианта при голосовании (от ТГ-id)
@log_function_call
async def election_tg(tg_id, variant_id):
    try:
        member_id = await extract_member_id(club_id, await extract_user_id(tg_id))
        if member_id:
            result = await election(member_id, variant_id)
            logger.info(f"Выбран вариант variant_id={variant_id} участником с tg_id={tg_id}: {result}")
            return True, result
        else:
            logger.info('Такого участника нет в группе')
            return False, 'Такого участника нет в группе'
    except Exception as e:
        logger.error(f"Произошла ошибка при выборе варианта: {e}")
        return False, f"Произошла ошибка: {str(e)}"

# Функция старта голосования. Меняем статус голосования на 'ongoing'.
# Указываем, кто запустил голосование (если не автоматически).
@log_function_call
async def voting_start_tg(voting_id, starter_tg_id=None):
    try:
        if starter_tg_id:
            starter = await extract_member_id(club_id, await extract_user_id(starter_tg_id))
            await voting_start(voting_id, starter)
        else:
            await voting_start(voting_id)
        logger.info(f"Голосование voting_id={voting_id} успешно запущено.")
    except Exception as e:
        logger.error(f"Ошибка при старте голосования: {e}")
        raise

# Функция завершения промежуточного этапа голосования. Переводит в статус "loser" наименее популярные варианты.
# Оставшиеся варианты должны в сумме набирать 50% голосов от имеющих право голоса.
# Возвращает кортеж из ID проигравших вариантов.
@log_function_call
async def voting_stage_tg(voting_id, stager_tg_id=None):
    try:
        if stager_tg_id:
            stager = await extract_member_id(club_id, await extract_user_id(stager_tg_id))
            result = await voting_stage(voting_id, stager)
        else:
            result = await voting_stage(voting_id)

        logger.info(f"Промежуточный этап голосования voting_id={voting_id} завершен: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при завершении промежуточного этапа голосования: {e}")
        raise


# Функция создания финального этапа голосования (где голосуется два варианта или больше, если есть варианты,
# которые набрали столько же, сколько второй)
@log_function_call
async def voting_final_tg(voting_id, finaler_tg_id=None):
    try:
        if finaler_tg_id:
            finaler = await extract_member_id(club_id, await extract_user_id(finaler_tg_id))
            if not finaler:
                logger.warning(f"Пользователь с tg_id={finaler_tg_id} не является участником группы")
                return False, 'Вы не являетесь участником группы'
            result = await voting_final(voting_id, finaler)
        else:
            result = await voting_final(voting_id)

        logger.info(f"Создан финальный этап голосования voting_id={voting_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при создании финального этапа голосования: {e}")
        raise

# Функция завершения голосования. Определяет вариант - победитель.
@log_function_call
async def voting_complete_tg(voting_id, finisher_tg_id=None):
    try:
        if finisher_tg_id:
            finisher = await extract_member_id(club_id, await extract_user_id(finisher_tg_id))
            if not finisher:
                logger.warning(f"Пользователь с tg_id={finisher_tg_id} не является участником группы")
                return False, 'Вы не являетесь участником группы'
            result = await voting_complete(voting_id, finisher)
        else:
            result = await voting_complete(voting_id)

        logger.info(f"Голосование voting_id={voting_id} успешно завершено: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при завершении голосования: {e}")
        raise


# Функция обновления адреса пользователя
@log_function_call
async def update_address(tg_id, city, street, house):
    try:
        user_id = await extract_user_id(tg_id)
        if not user_id:
            return False, 'Пользователь не найден.'

        member_id = await extract_member_id(club_id, user_id)
        if not member_id:
            return False, 'Пользователь не является участником группы.'

        # Здесь должна быть функция для обновления адреса в базе данных
        # Например, используем функцию db_update из db_func.py
        result = await update_user_data(user_id=user_id, city=city, street=street, house=house)
        if result:
            return True, 'Адрес успешно обновлен.'
        else:
            return False, 'Ошибка при обновлении адреса.'
    except Exception as e:
        logger.error(f"Ошибка при обновлении адреса: {e}")
        return False, str(e)
