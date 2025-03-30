# Модуль registrator_handlers
# Содержит хэндлеры регистраторов (тех, кто подтверждает членство
# в группе новых участников)
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, Message
from filters.filters import StatusFilter
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import db_update, extract_user_data_tg, extract_user_member_id, new_status
import logging
from utils import log_handler_call

# Настройка логирования
logging.basicConfig(level=logging.INFO)

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
#     logging.info(f"Пользователь {message.from_user.id} начал работу как регистратор.")
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
        logging.info(f"Регистратор {callback.from_user.id} подтверждает членство пользователя {tg_id}.")

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
    except Exception as e:
        logging.error(f"Ошибка при подтверждении членства пользователя {tg_id}: {e}")
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
        logging.info(f"Регистратор {callback.from_user.id} отклоняет членство пользователя {tg_id}.")

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
        logging.error(f"Ошибка при отклонении членства пользователя {tg_id}: {e}")
        await callback.message.answer(
            text="Произошла ошибка при отклонении членства.",
            reply_markup=await user_menu(callback.from_user.id,data['user_status'])
            )