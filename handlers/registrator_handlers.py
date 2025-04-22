# Модуль registrator_handlers
# Содержит хэндлеры регистраторов (тех, кто подтверждает членство
# в группе новых участников)
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, Message
import logging
from filters.filters import StatusFilter
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import db_update, extract_user_data_tg, extract_user_member_id, new_status
from services.services import send_notification_to_user
from utils import log_handler_call

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')

# Инициализируем роутер уровня модуля
router = Router()

# Навешиваем фильтр, проверяющий, является ли пользователь Регистратором
router.message.filter(StatusFilter(required_status = ['registrator']))

router.callback_query.filter(StatusFilter(required_status = ['registrator']))

"""
ХЭНДЛЕРЫ
"""

# # Хэндлер на команду /start
# @router.message(Command(commands=["start"]))
# async def process_start_command2(message: Message):
#     """
#     Обработчик команды /start для регистраторов.
#     Отправляет приветственное сообщение.
#     """
#     logger.info(f"Пользователь {message.from_user.id} начал работу как регистратор.")
#     await message.answer(
#         text='Привет, Регистратор!\nЯ бот для управления голосованиями.\n'
#              'Вы можете подтверждать членство новых участников.',
#         reply_markup=remove_markup
#     )


"""
Подтверждение или отклонение членства участника регистратором после заполнения анкеты
"""

# Этот хэндлер срабатывает при нажатии регистратором кнопки "Подтверждаю"
@router.callback_query(F.data.startswith('yes_registration:'))
@log_handler_call
async def process_registrator_yes_press(callback: CallbackQuery,data:dict):
    """
    Обработчик подтверждения членства нового участника.
    Изменяет статус пользователя в базе данных.
    """
    try:
        # Извлекаем Telegram ID пользователя из callback_data
        tg_id = int(callback.data.split(':')[1])
        logger.info(f"Регистратор {callback.from_user.id} подтверждает членство пользователя {tg_id}.")

        # Получаем member_id пользователя
        user_id, member_id = await extract_user_member_id(tg_id)
        if not member_id:
            await callback.message.answer(text=f"Пользователь с ID {tg_id} не найден.")
            return

        # Обновляем статус пользователя в базе данных
        await new_status(registrator=data['member_id'], member_id=member_id, status='member')
        await callback.message.delete_reply_markup()  # Удаляем кнопки

        # Отправляем уведомление о успешном подтверждении
        await callback.message.answer(
            text=f"Спасибо! Пользователь {tg_id} получил статус 'Участник'.",
            reply_markup=await user_menu(callback.from_user.id,data['user_status'])
        )
        #Отправляем сообщение принятому пользователю
        await send_notification_to_user(
            tg_id,
            message_text=('Поздравляем! Ваша заявка на вступление в группу одобрена. Теперы вы полноправный участник группы и можете принимать участие в голосованиях.\n'
            'Обратите внимание - чтобы ваш голос учитывался, вам нужно либо выбрать себе представителя, либо саморму стать представителем.\n'
            'Выбор представителя не ограничивает вашу возможность голосовать самому в любом голосовании.'
            'Но если вы не приняли участие в голосовании, будет учитываться то, как за вас проголосовал ваш представитель.'
            'Если вас не будет устраивать то, как за вас голосует ваш представитель, вы в любой момент сможете его поменять, либо сами стать представителем.'
            'Но статус предстаителя налагает определенные обязательства. Например - участие во всех голосованиях.\n'
            'Представитель может выбрать себе заместителя, который будет голосвать за него в случае отсутствия.\n'
            'Представитель несет ответственность за голосования заместителя, как за свои')
            )

    except Exception as e:
        logger.error(f"Ошибка при подтверждении членства пользователя {tg_id}: {e}")
        await callback.message.answer(text="Произошла ошибка при подтверждении членства.")


# Этот хэндлер срабатывает при нажатии регистратором кнопки "Не подтверждаю"
@router.callback_query(F.data.startswith('no_registration:'))
@log_handler_call
async def process_registrator_no_press(callback: CallbackQuery, data):
    """
    Обработчик отказа от подтверждения членства нового участника.
    Изменяет поле "familiar" пользователя в базе данных.
    """
    try:
        # Извлекаем Telegram ID пользователя из callback_data
        tg_id = int(callback.data.split(':')[1])
        logger.info(f"Регистратор {callback.from_user.id} отклоняет членство пользователя {tg_id}.")

        # Получаем member_id пользователя
        user_id, member_id = await extract_user_member_id(tg_id)
        if not member_id:
            await callback.message.answer(text=f"Пользователь с ID {tg_id} не найден.")
            return

        # Обновляем поле "familiar" пользователя в базе данных
        await db_update('Members', 'id', member_id, familiar='stranger')
        await callback.message.delete_reply_markup()  # Удаляем кнопки

        # Отправляем уведомление об отказе
        await callback.message.answer(
            text=f"Спасибо! Пользователь {tg_id} не получил статус 'Участник'.",
            reply_markup=await user_menu(callback.from_user.id,data['user_status'])
        )
    except Exception as e:
        logger.error(f"Ошибка при отклонении членства пользователя {tg_id}: {e}")
        await callback.message.answer(
            text="Произошла ошибка при отклонении членства.",
            reply_markup=await user_menu(callback.from_user.id,data['user_status'])
            )