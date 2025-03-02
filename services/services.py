# Модуль servics
# Содержит фукнции, наприимер, рассылки сообщений пользователям бота

import logging
import aiosqlite
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from FSMs.FSMs import FSMRegistration, FSMRereg
from data_base.telegram_bot_logic import Database, is_votist
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, return_to_main_menu_markup
from filters.filters import filter_contact
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from LEXICON.LEXICON import LEXICON

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)
path_db = config.db.path_db  # путь к базе данных


#Функция уведомления регистратора. Возможно, ее надо будет вписать в  хэндлер.
@log_function_call
async def notify_registrator(registrator_tg_id, candidate_tg_id, user_dict):
    try:
        # Создаем объекты инлайн-кнопок
        confirm_button = InlineKeyboardButton(
            text='Подтверждаю',
            callback_data=f"yes_registration:{candidate_tg_id}"
        )
        not_confirm_button = InlineKeyboardButton(
            text='Не подтверждаю',
            callback_data=f"no_registration:{candidate_tg_id}"
        )
        # Добавляем кнопки в клавиатуру в один ряд
        keyboard: list[list[InlineKeyboardButton]] = [
            [confirm_button, not_confirm_button]
        ]
        # Создаем объект инлайн-клавиатуры
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        # Формируем сообщение для регистратора
        message_text = (
            f"Пользователь с данными:\n"
            f'Имя: {user_dict["first_name"]}\n'
            f'Фамилия: {user_dict["last_name"]}\n'
            f'Возраст: {user_dict["birth_year"]}\n'
            f'Пол: {user_dict["gender"]}\n'
            f'Город: {user_dict["city"]}\n'
            f'Улица: {user_dict["street"]}\n'
            f'Дом: {user_dict["house"]}\n'
            f'Истинность контакта: {user_dict["tg_true"]}\n'
            f'Номер телефона: {user_dict["tg_phone_number"]}\n'
            f"Просит вас подтвердить его право\n"
            f"стать членом клуба.\n"
            f"Подтверждаете?"
        )

        # Отправляем сообщение регистратору
        await bot.send_message(
            registrator_tg_id,
            text=message_text,
            reply_markup=markup  # клавиатура подтверждения
        )

        return True, "Уведомление отправлено."
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления регистратору: {e}")
        return False, str(e)

# Функция уведомления и лишения статуса 'votist' тех пользователей, чей представитель утратил этот статус
@log_handler_call
async def not_votist_because_proxy_quit(proxy:int):
    logging.info(f"Лишаем статуса гоосующих тех, чей представитель {proxy} сложил полномочия")
    async with Database(path_db) as cursor:
        try:
            await cursor.execute(
                'SELECT id FROM Members WHERE proxy = ?',
                (proxy,)
            )
            result = await cursor.fetchall()
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при лишении статуса 'голосующих' доверителей ушедшего представителя: {e}")
            raise

    for item in result:
        member_id, = item
        flag = await is_votist(member_id)
        if not flag:
            async with Database(path_db) as cursor:
                try:
                    await cursor.execute(
                '''SELECT tg_id FROM Users WHERE id in
                (SELECT user_id FROM Members WHERE id = ?)''',
                (member_id,)
                    )
                    tg_id, = await cursor.fetchone()
                    message_text = '''
Ваш представитель утратил статус представителя.
Выберите другого или сами станьте представителем, чтобы иметь право решающего голоса.
Для начала работы наберите или нажмите команду /start
'''
                    # Отправляем сообщение регистратору
                    await bot.send_message(
                        tg_id,
                        text=message_text
                    )

                except aiosqlite.Error as e:
                    logging.error(f"Ошибка при лишении статуса голосующего: {e}")
                    raise
