# Модуль servics
# Содержит фукнции, наприимер, рассылки сообщений пользователям бота
# Вообще-то нарушает логику разделения скрипта на скрипт телеграм-бота и скрипт базы данных.
# Может пределаю позже.

import logging
import aiosqlite
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Contact
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from FSMs.FSMs import FSMRegistration, FSMRereg
# from data_base.telegram_bot_logic import AsyncDatabase, is_votist
from data_base.data_base import *
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, return_to_main_menu_markup
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from LEXICON.LEXICON import LEXICON

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)
path_db = config.db.path_db  # путь к базе данных
club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)

# Функция уведомления пользователей
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

async def send_notification_to_user(tg_id: int, message_text: str):
    try:
        # Попытка отправить сообщение
        await bot.send_message(
            tg_id,
            text=message_text
        )
    except TelegramForbiddenError:
        # Пользователь заблокировал бота
        logging.warning(f"Пользователь {tg_id} заблокировал бота.")
        await mark_user_as_unavailable(tg_id, reason="bot blocked")
    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            # Чат не найден (пользователь удалил аккаунт)
            logging.warning(f"Пользователь {tg_id} удалил аккаунт или чат не существует.")
            await mark_user_as_unavailable(tg_id, reason="user lost")
        else:
            # Другая ошибка BadRequest
            logging.error(f"Ошибка при отправке сообщения пользователю {tg_id}: {e}")
    except TelegramAPIError as e:
        # Любая другая ошибка Telegram API
        logging.error(f"Telegram API Error для пользователя {tg_id}: {e}")
    except Exception as e:
        # Все остальные исключения
        logging.error(f"Неизвестная ошибка при отправке сообщения пользователю {tg_id}: {e}")


#Функция уведомления регистратора при краткой регистрации.
@log_function_call
async def notify_registrator_short(registrator_tg_id, candidate_tg_id, user_dict):
    try:
        print(user_dict)
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
            f'Контакт: {user_dict["contact"]}\n'
            f'Истинность контакта: {user_dict["contact_true"]}\n'
            f'Резюме: {user_dict["resume"]}\n'
            f"Просит подтвердить его право стать членом клуба.\n"
            f"Кого либо из регистраторов он не знает\n"
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

#Функция уведомления суперрегистратора при краткой регистрации.
@log_function_call
async def notify_super_registrator_short(candidate_tg_id, user_dict):
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
            f'Контакт: {user_dict["contact"]}\n'
            f'Истинность контакта: {user_dict["tg_true"]}\n'
            f'Резюме: {user_dict["resume"]}\n'
            f"Просит вас подтвердить его право\n"
            f"стать членом клуба.\n"
            f"Подтверждаете?"
        )

        super_registrators = await list_of_members(club_id,'superregistrator')
        if not super_registrators:
            super_registrators = await list_of_members(club_id,'registrator')


        # Отправляем сообщение суперрегистраторам (а если их нет - регистраторам)
        for registrator in super_registrators:
            registrator_tg_id = registrator[2]
            await bot.send_message(
                registrator_tg_id,
                text=message_text,
                reply_markup=markup  # клавиатура подтверждения
        )

        return True, "Уведомление отправлено."
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления регистратору: {e}")
        return False, str(e)

#Функция уведомления регистратора при подробной регистрации. Возможно, ее надо будет вписать в  хэндлер.
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
@log_function_call
async def not_votist_because_proxy_quit(proxy:int):
    logging.info(f"Лишаем статуса гоосующих тех, чей представитель {proxy} сложил полномочия")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''SELECT username FROM Users WHERE id IN
                                 (SELECT user_id FROM Members WHERE id = ?)''', (proxy,))
            proxy_name, = await cursor.fetchone()

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
            async with AsyncDatabase(path_db) as cursor:
                try:
                    await cursor.execute(
                '''SELECT tg_id FROM Users WHERE id in
                (SELECT user_id FROM Members WHERE id = ?)''',
                (member_id,)
                    )
                    tg_id, = await cursor.fetchone()
                    message_text = f'''
Ваш представитель {proxy_name} утратил статус представителя.
Выберите другого или сами станьте представителем, чтобы иметь право решающего голоса.
Для начала работы наберите или нажмите команду /start
'''
                    # Отправляем сообщение участннику, чей представитель ушел в отставку
                    await bot.send_message(
                        tg_id,
                        text=message_text
                    )

                except aiosqlite.Error as e:
                    logging.error(f"Ошибка при лишении статуса голосующего: {e}")
                    raise

# Функция уведомления и присвоения статуса 'votist' тем пользователям, чей представитель возобновил этот статус
@log_function_call
async def votist_because_proxy_returned(proxy:int):
    logging.info(f"Возвращаем статус гоосующих тем, чей представитель {proxy} вернул полномочия")
    async with AsyncDatabase(path_db) as cursor:
        try:
            await cursor.execute('''SELECT username FROM Users WHERE id IN
                                 (SELECT user_id FROM Members WHERE id = ?)''', (proxy,))
            proxy_name, = await cursor.fetchone()

            await cursor.execute(
                'SELECT id FROM Members WHERE proxy = ?',
                (proxy,)
            )
            result = await cursor.fetchall()
        except aiosqlite.Error as e:
            logging.error(f"Ошибка при возвращении статуса 'голосующих' доверителям вернувшегося представителя: {e}")
            raise

    for item in result:
        member_id, = item
        flag = await is_votist(member_id)
        if flag:
            async with AsyncDatabase(path_db) as cursor:
                try:
                    await cursor.execute(
                '''SELECT tg_id FROM Users WHERE id in
                (SELECT user_id FROM Members WHERE id = ?)''',
                (member_id,)
                    )
                    tg_id, = await cursor.fetchone()
                    message_text = f'''
Ваш представитель {proxy_name} вернул статус представителя.
Теперь ваш голос будет учитываться при голосованиях.
Для начала работы наберите или нажмите команду /start
'''
                    # Отправляем сообщение участннику, чей представитель ушел в отставку
                    await bot.send_message(
                        tg_id,
                        text=message_text
                    )

                except aiosqlite.Error as e:
                    logging.error(f"Ошибка при лишении статуса голосующего: {e}")
                    raise

# Функция выхода из группы. Передается id участника.
# Производится вызыв функии member_leave_club
# Если участник был представителем вызывается функция not_votist_because_proxy_quit
@log_function_call
async def leave_club (member_id, status):
    logging.info(f"Выход из группы member_id={member_id}")
    await member_leave_club(member_id,status)
    if 'proxy' in status:
        await not_votist_because_proxy_quit(member_id)