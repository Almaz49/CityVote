# Модуль manager.py
# Содержит функции, управляющие сложными составными процессами.
# Например, этап голосования и последующая информационная рассылка об его итогах.
import logging
from typing import Dict, Optional, Any
from keyboards.keyboards import create_inline_kb
from services.services import send_notification_to_user, send_notification_to_chat_or_channel, not_votist_because_proxy_quit
from data_base.data_base import (
    voting_create,
    list_of_members,
    list_of_channel,
    extract_club_info,
    extract_voting_info,
    member_leave_club,
    voting_stage,
    voting_start,
    voting_final,
    voting_complete,
    extract_group_id
)
from utils import log_function_call

# Настройка логирования
logger = logging.getLogger(__name__)

# Словарь уровня информирования. Ключ - событие, значение - список уровней информирования.
level_info_dict = {
    'create': ['max', None],
    'start': ['max', 'average', None],
    'stage': ['max', None],
    'final': ['max', 'average', None],
    'confirm': ['max', 'average', None],
    'complete': ['max', 'average', None]
}

@log_function_call
async def voting_create_manager(club_id: int, creator: str, title: str, text: Optional[str] = None,
                                voting_type: str = 'usual', voting_status: str = 'add_variants') -> Dict[str, Any]:
    """
    Менеджер создания голосования. Вызывает функцию создания голосования,
    организует информационные рассылки.
    """
    result = await voting_create(club_id, creator, title, text, voting_type, voting_status)
    if not result or not result.get('success'):
        return {'success': False, 'message': result.get('message', 'Ошибка при создании голосования')}

    club_info = await extract_club_info(club_id)
    if not club_info:
        logger.error(f"Информация о группе {club_id} не найдена")
        return {'success': False, 'message': 'Группа не найдена'}

    club_name: str = club_info.get('name', 'Неизвестная группа')
    notify_text = f'В группе {club_name} создано голосование:\n{title}\n'

    if voting_status == 'add_variants':
        notify_text += ('\nПока оно находится в стадии добавления вариантов. Добавлять варианты могут '
                        'пользователи со статусом "Делегат".\nВы сможете выбрать один из вариантов, '
                        'когда голосование будет запущено.')

    # Рассылка пользователям
    members = await list_of_members(club_id)
    if members:
        for item in members:
            info_level = item.get('info_level')
            if info_level in level_info_dict.get('create', []):
                tg_id = item.get('tg_id')
                if tg_id is not None:
                    try:
                        await send_notification_to_user(tg_id, notify_text)
                    except Exception as e:
                        logger.error(f"Ошибка отправки пользователю {tg_id}: {e}")

    # Рассылка каналам и чатам
    chats = await list_of_channel(club_id)
    if chats:
        for item in chats:
            info_level = item.get('info_level')
            if info_level in level_info_dict.get('create', []):
                chat_id = item.get('tg_id')
                if chat_id is not None:
                    try:
                        await send_notification_to_chat_or_channel(chat_id, notify_text)
                    except Exception as e:
                        logger.error(f"Ошибка отправки в чат {chat_id}: {e}")

    return {'success': True, 'message': 'Голосование успешно создано и рассылка произведена'}


@log_function_call
async def voting_manager(voting_id: int, club_id: Optional[int] = None, admin: Optional[int] = None,
                         stage_type: str = 'stage') -> Dict[str, Any]:
    """
    Менеджер этапов голосования. Вызывает функцию соответствующего этапа голосования,
    организует информационные рассылки.
    """
    if not club_id:
        club_id = await extract_group_id(voting_id)
        if not club_id:
            logger.error("Не удалось получить club_id по voting_id")
            return {'success': False, 'message': 'club_id не найден'}

    club_info = await extract_club_info(club_id)
    if not club_info:
        return {'success': False, 'message': 'Информация о группе не найдена'}

    club_name = club_info.get('name', 'Неизвестная группа')

    voting_info = await extract_voting_info(voting_id)
    if not voting_info:
        return {'success': False, 'message': 'Информация о голосовании не найдена'}

    title = voting_info.get('title', 'Без названия')
    current_status = voting_info.get('voting_status')

    accept = {
        'add_variants': ['start'],
        'ongoing': ['stage', 'final', 'complete'],
        'confirmation': ['complete']
    }

    if current_status not in accept or stage_type not in accept[current_status]:
        return {'success': False, 'message': 'Недопустимое действие. Возможно, кнопка устарела.'}

    # Выполняем этап голосования
    if stage_type == 'stage':
        result = await voting_stage(voting_id, club_id, admin)
    elif stage_type == 'start':
        result = await voting_start(voting_id, admin)
    elif stage_type == 'final':
        result = await voting_final(voting_id, admin)
    elif stage_type == 'complete':
        result = await voting_complete(voting_id, admin)
    else:
        return {'success': False, 'message': 'Неизвестный этап голосования'}

    if not result or not result.get('success'):
        return {'success': False, 'message': result.get('message', 'Этап голосования не выполнен')}

    keyboard = {f'show_oll_variants:{voting_id}': 'Голосовать'}
    markup = create_inline_kb(1, **keyboard)

    notify = result.get('notify', result.get('message', ''))
    base_text = f'В группе {club_name} '

    if stage_type == 'start':
        notify_text = f'{base_text}стартовало голосование:\n{title}\n\n{notify}\n\nВы можете выбрать один из вариантов'
    elif stage_type == 'stage':
        notify_text = f'{base_text}подведен промежуточный итог голосования: {title}\n\n{notify}'
    elif stage_type == 'final':
        notify_text = f'{base_text}начался финальный этап голосования: {title}\n\n{notify}'
    elif stage_type == 'complete':
        notify_text = f'{base_text}завершилось голосование: {title}\n\n{notify}'
        keyboard = {f'show_oll_variants:{voting_id}': 'Посмотреть итоги'}
        markup = create_inline_kb(1, **keyboard)
    else:
        notify_text = f'{base_text}произошло событие: {title}\n\n{notify}'

    # Рассылка участникам
    members = await list_of_members(club_id)
    if members:
        for item in members:
            info_level = item.get('info_level')
            if info_level in level_info_dict.get(stage_type, []):
                tg_id = item.get('tg_id')
                if tg_id is not None:
                    try:
                        await send_notification_to_user(tg_id, notify_text, reply_markup=markup)
                    except Exception as e:
                        logger.error(f"Ошибка отправки пользователю {tg_id}: {e}")

    # Рассылка каналам
    chats = await list_of_channel(club_id)
    if chats:
        for item in chats:
            info_level = item.get('info_level')
            if info_level in level_info_dict.get(stage_type, []):
                chat_id = item.get('tg_id')
                if chat_id is not None:
                    try:
                        await send_notification_to_chat_or_channel(chat_id, notify_text)
                    except Exception as e:
                        logger.error(f"Ошибка отправки в чат {chat_id}: {e}")

    return result


@log_function_call
async def leave_club(member_id: int, status: str) -> None:
    """
    Функция выхода из группы. Если участник был представителем — вызывается дополнительная логика.
    """
    logger.info(f"Выход из группы: member_id={member_id}")
    await member_leave_club(member_id, status)
    if 'proxy' in status:
        await not_votist_because_proxy_quit(member_id)


async def daily_task(club_id: int) -> None:
    """
    Ежедневная задача — рассылка админам.
    """
    logger.info("Выполняется ежедневная задача в 00:00")
    admins = await list_of_members(club_id, status='admin')
    if admins:
        for admin in admins:
            tg_id = admin.get('tg_id')
            if tg_id is not None:
                try:
                    await send_notification_to_user(tg_id=tg_id, message_text="📅 Ежедневная задача выполнена!")
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение админу {tg_id}: {e}")