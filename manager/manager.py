# Модуль manager.py
# Содержит функции, управляющие сложными составными процессами.
# Например, этап голосования и последующая информационная рассылка об его итогах.

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from FSMs.FSMs import FSMRegistration, FSMRereg
from data_base.db_func import extract_club_info
# from data_base.telegram_bot_logic import AsyncDatabase, is_votist
from data_base.data_base import *
from keyboards.keyboards import create_inline_kb
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from services.services import *
from LEXICON.LEXICON import LEXICON

# Настройка логирования
logger = logging.getLogger(__name__)

# Словарь уровня информирования. Ключ - событие, значение - список уровней информирования,
# которым рассылается сообщение о событии.
# Если событие без приставки, обозначающий объект (например, 'variant_create'), то оно относится к голосованию
level_info_dict = {
    'create':['max',None],
    'start':['max','average',None],
    'stage':['max',None],
    'final':['max','average',None],
    'confirm':['max','average',None],
    'complete':['max','average',None]
}

@log_function_call
async def voting_create_manager(club_id, creator, title, text=None, voting_type='usual', voting_status='add_variants'):
    """
    Менеджер создания голосования. Вызывает функцию создания голосования,
    организует информационные рассылки.
    """

    # Запускаем голосование
    result = await voting_create(club_id, creator, title, text, voting_type, voting_status)

    # Если запуск был неудачен - возвращаем результат
    if result:
        success = result.get('success',False)
        message = result.get('message','Что-то пошло не так, не найден результат')
    else:
        return result

    if not success:
        return result

    club_info = await extract_club_info(club_id)
    club_name = club_info[0]
    notify_text = f'В группе {club_name} Создано голосование:\n{title} '
    if voting_status == 'add_variants':
        notify_text = notify_text + ('\n\nПока оно находится в стадии добавления вариантов. Добавлять варианты могут пользователи со статусом "Делегат".'
        '\nВы сможете выбрать один из вариантов, когда голосвание будет запущено. О старте голосования сообщим дополнительно')

    # Если голосование запущено, делаем рассылки пользователям, в чаты и каналы
    members = await list_of_members(club_id)
    if not members:
        logger.info("Не найдены участники группы")
        return result

    # Делаем рассылку пользователям бота в зависимость от их уровня информирования
    for item in members:
        if item[6] in level_info_dict.get('create'):
            response = await send_notification_to_user(item[2],notify_text)
            if response:
                # logger.debug(f'{response}')
                pass

    logger.info("Рассылка пользователям произведена")

    chats = await list_of_channel(club_id)
    if not chats:
        logger.info("Не найдены связанные с ботом чаты и каналы")
        return result


    # Делаем рассылку по каналам и чатам, в которые добавлен бот
    for item in chats:
        if item.get('info_level') in level_info_dict.get('create'):
            response = await send_notification_to_chat_or_channel(item.get('id'), notify_text)
            if response:
                logger.info(f'{response}')

    return True, message + "\nВсе рассылки удачно произведены"

@log_function_call
async def voting_manager(voting_id, club_id=None, admin=None, stage_type='stage'):
    """
    Менеджер этапов голосования. Вызывает функцию соответствующего этапа голосования,
    организует информационные рассылки.
    :param voting_id: ID голосования.
    :param club_id: ID группы.
    :param admin: ID админа в таблице Members
    :param stage_type: тип этапа ("start", "stage", "final", "confirm", "complete")
    """
    if not club_id:
        club_id = extract_group_id(voting_id)

    club_info = await extract_club_info(club_id)
    if not club_info:
        return {
            'success':False,
            'message':"Не найдена информация о группе"
            }
    club_name = club_info.get('name')

    voting_info = await extract_voting_info(voting_id)
    if not voting_info:
        return {
            'success':False,
            'message':"Не найдена информация о голосовании"
            }
    title = voting_info.get('title')
    voting_status = voting_info.get('voting_status')
    # variants = await list_of_variants(voting_id, 'valid')

    # Составляем словарь допустимых действий в зависимости от статуса голосования
    accept = {
        'add_variants':['start'],
        'ongoing':['stage','final','complete'],
        'confirmation':['complete']
    }

    flag = False
    if voting_status in accept:
        if stage_type in accept[voting_status]:
            flag = True

    if not flag:
        return {
            'success':False,
            'message':"Недопустимое действие. Наверно, кнопка устарела. Обновите меню или обратитесь к администрации"
            }




    # Запускаем этап в зависимости от типа
    if stage_type == 'stage':
        result = await voting_stage(voting_id, club_id, admin)
    elif stage_type == 'start':
        result = await voting_start(voting_id, admin)
    elif stage_type == 'final':
        result = await voting_final(voting_id, admin)
    elif stage_type == 'complete':
        result = await voting_complete(voting_id, admin)



    # Если запуск был неудачен - возвращаем результат
    if not result:
        return {
            'success':False,
            'message':"Этап голосования не удался, обратитесь к администрации"
            }
    if not result.get('success'):
        return {
            'success':False,
            'message':result.get('message','Этап голосования не дал результата')
            }



    keyboard = {f'show_oll_variants:{voting_id}':'Голосовать'}
    markup = create_inline_kb(1,**keyboard)
    # Если в функции предусмотрено сообщение для рассылки, передаем его, если нет - сообщение функции
    notify = result.get('notify',result.get('message'))

    if stage_type == 'start':
        notify_text = (f'В группе {club_name} стартовало голосование:\n{title}\n'
                       f'\n{notify}\n'
                       'Вы можете выбрать один из вариантов ')
    elif stage_type == 'stage':
        notify_text = (f'В группе {club_name} подведен промежуточный итог голоcования: {title}\n'
                       f'{notify}')
    elif stage_type == 'final':
        notify_text = (f'В группе {club_name} начался финальный этап голоcования: {title}\n'
                       f'{notify}')
    elif stage_type == 'complete':
        notify_text = (f'В группе {club_name} завершилось голоcоование: {title}\n'
                       f'{notify}')
        keyboard = {f'show_oll_variants:{voting_id}':'Посмотреть итоги'}
        markup = create_inline_kb(1,**keyboard)


    # Если голосование запущено, делаем рассылки пользователям, в чаты и каналы
    members = await list_of_members(club_id)
    if not members:
        logger.info("Не найдены участники группы")
        return {
            'success':False,
            'message':"Не найдены участники группы"
            }

    # Делаем рассылку пользователям бота
    for item in members:
        if item[6] in level_info_dict.get(stage_type):
            response = await send_notification_to_user(item[2],notify_text, reply_markup=markup)
            if response:
                pass
                # logger.debug(f'{response}')

    logger.info("Рассылка пользователям произведена")

    chats = await list_of_channel(club_id)
    if not chats:
        logger.info("Не найдены связанные с ботом чаты и каналы")
        return result



    # Делаем рассылку по каналам и чатам, в которые добавлен бот
    for item in chats:
        if item.get('info_level') in level_info_dict.get(stage_type):
            response = await send_notification_to_chat_or_channel(item.get('tg_id'), notify_text)
            if response:
                logger.info(f'{response}')

    return result


# Функция выхода из группы. Передается id участника.
# Производится вызыв функии member_leave_club
# Если участник был представителем вызывается функция not_votist_because_proxy_quit
@log_function_call
async def leave_club (member_id, status):
    logger.info(f"Выход из группы member_id={member_id}")
    await member_leave_club(member_id,status)
    if 'proxy' in status:
        await not_votist_because_proxy_quit(member_id)