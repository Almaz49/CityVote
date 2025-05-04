from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from FSMs.FSMs import FSMRegistration, FSMRereg
from data_base.db_func import extract_club_info
# from data_base.telegram_bot_logic import AsyncDatabase, is_votist
from data_base.data_base import *
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, return_to_main_menu_markup, main_menu_markup
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from services.services import *
from LEXICON.LEXICON import LEXICON

# Настройка логирования
logger = logging.getLogger(__name__)

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
        success, message = result
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

    # Делаем рассылку пользователям бота
    for item in members:
        response = await send_notification_to_user(item[2],notify_text)
        if response:
            logger.debug(f'{response}')

    logger.info("Рассылка пользователям произведена")

    chats = await list_of_channel(club_id)
    if not chats:
        logger.info("Не найдены связанные с ботом чаты и каналы")
        return result


    # Делаем рассылку по каналам и чатам, в которые добавлен бот
    for item in chats:
        response = await send_notification_to_chat_or_channel(item[0], notify_text)
        if response:
            logger.info(f'{response}')

    return True, message + "\nВсе рассылки удачно произведены"
