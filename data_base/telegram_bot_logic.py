# Модуль telegram_bot_logic.
# Служит "прокладкой" между телеграм-ботом и функциями базы данных.
# Его функции принимают аргументом телеграм-ID, и обращаются к функциям,
# работающим с базой данных, отпарвляя им в качестве аргумента user_id и member_id
# Это нужно для того, чтобы при необходимости поменять базу данных,
# но не переписывать хэндлеры


import logging

from data_base.db_func import *
from data_base.db_member import *
from data_base.db_vote import *
from utils import log_function_call

# Настройка логирования
logger = logging.getLogger(__name__)





# Функция извлечения данных о пользователе по его tg_id
# Используется при создании нового регистратора
# Возвращает (flag, ans_str). Если flag == true, значит участник может быть назначен регистратором.
# ans_str - комментарий, который выдается по итогу извлечения данных
@log_function_call
async def extract_new_registrator_data(club_id:int, tg_id:int):
    user_id = await extract_user_id(tg_id)
    member_id = await extract_member_id(club_id, user_id)

    if not member_id:
        flag = False
        ans_str = "Нет такого участника. Попробуйте снова."
        logger.warning(f"Участник с tg_id={tg_id} не найден: {ans_str}")
        return flag, ans_str

    user_data = await get_profile(member_id=member_id)
    if user_data:
        ans_str = (
            f"Имя: {user_data.get('first_name')}, Фамилия: {user_data.get('last_name')},\n"
            f"Телефон: {user_data.get('tg_phone_number')}\nПсевдоним: {user_data.get('username')}"
        )
    else:
        # Если user_data пустое, устанавливаем ans_str в значение по умолчанию
        ans_str = "Данные профиля участника не найдены."

    has_registator = await check_member_status(
        member_id=member_id, target_status="registrator"
    )
    has_superregistator = await check_member_status(
        member_id=member_id, target_status="superregistrator"
    )
    if (
        has_registator or has_superregistator
    ):  # если пользователь регистратор или суперрегистратор
        flag = False
        ans_str += "\nЭтот участник уже регистратор."
    else:
        flag = True

    logger.info(
        f"Результат проверки на регистрацию для tg_id={tg_id}: {flag}, {ans_str}"
    )
    return flag, ans_str


# Присвоение нового статуса - в качестве аргументов функции tg_id регистратора и участника группы
@log_function_call
async def new_status_tg(club_id, registrator_tg_id, member_tg_id, status, token_id=None):
    ans_str = ""
    if registrator_tg_id:
        registrator_user_id = await extract_user_id(registrator_tg_id)
        if not registrator_user_id:
            ans_str += "Нет такого регистратора."
            logger.warning(
                f"Не найден регистратор с tg_id={registrator_tg_id}: {ans_str}"
            )
            return False, ans_str

        registrator = await extract_member_id(club_id, registrator_user_id)
        if not registrator:
            ans_str += "Нет такого регистратора."
            logger.warning(
                f"Не найден участник с member_id={registrator_user_id} в группе {club_id}: {ans_str}"
            )
            return False, ans_str
    else:
        registrator = None

    user_id = await extract_user_id(member_tg_id)
    if not user_id:
        ans_str += "Нет такого участника."
        logger.warning(f"Не найден пользователь с tg_id={member_tg_id}: {ans_str}")
        return False, ans_str

    member_id = await extract_member_id(club_id, user_id)
    if not member_id:
        ans_str += "Нет такого участника."
        logger.warning(
            f"Не найден участник с user_id={user_id} в группе {club_id}: {ans_str}"
        )
        return False, ans_str

    try:
        await new_status(registrator, member_id, status, token_id)
        logger.info(
            f"Присвоен новый статус '{status}' участнику с tg_id={member_tg_id} от регистратора с tg_id={registrator_tg_id}"
        )
        ans_str += f"Присвоен новый статус '{status}' участнику с tg_id={member_tg_id} от регистратора с tg_id={registrator_tg_id}"
        return True, ans_str
    except Exception as e:
        logger.error(f"Ошибка при присвоении статуса: {e}")
        ans_str += f"Ошибка при присвоении статуса: {str(e)}"
        return False, ans_str




# Извлечение статусов участника группы (отдает список статусов)
@log_function_call
async def extract_status_tg(club_id, tg_id):
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
