# Модуль services
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
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from FSMs.FSMs import FSMRegistration, FSMRereg
from data_base.db_func import extract_club_info
# from data_base.telegram_bot_logic import AsyncDatabase, is_votist
from data_base.data_base import *
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, return_to_main_menu_markup, main_menu_markup
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from LEXICON.LEXICON import LEXICON

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)
path_db = config.db.path_db  # путь к базе данных
club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)

# Получение информации о боте
async def get_bot_username():
    bot_info = await bot.get_me()
    return bot_info.username

# Функция уведомления пользователя
@log_function_call
async def send_notification_to_user(tg_id: int, message_text: str, reply_markup = main_menu_markup):
    is_available = await is_user_available(tg_id)
    logger.debug(f"Пользователь {tg_id} доступен: {is_available}")
    if is_available:
        try:
            # Попытка отправить сообщение
            await bot.send_message(
                tg_id,
                text=message_text,
                reply_markup=reply_markup
            )
            response = f'Сообщение отправлено пользователю {tg_id}'
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            logger.warning(f"Пользователь {tg_id} заблокировал бота.")
            response = f"Пользователь {tg_id} заблокировал бота."
            await mark_user_as_unavailable(tg_id, reason="bot blocked")
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                # Чат не найден (пользователь удалил аккаунт)
                logger.warning(f"Пользователь {tg_id} удалил аккаунт или чат не существует.")
                response = f"Пользователь {tg_id} удалил аккаунт или чат не существует."
                await mark_user_as_unavailable(tg_id, reason="user lost")
            else:
                # Другая ошибка BadRequest
                logger.error(f"Ошибка при отправке сообщения пользователю {tg_id}: {e}")
                response = f"Ошибка при отправке сообщения пользователю {tg_id}: {e}"
        except TelegramAPIError as e:
            # Любая другая ошибка Telegram API
            logger.error(f"Telegram API Error для пользователя {tg_id}: {e}")
            response = f"Telegram API Error для пользователя {tg_id}: {e}"
        except Exception as e:
            # Все остальные исключения
            logger.error(f"Неизвестная ошибка при отправке сообщения пользователю {tg_id}: {e}")
            response = f"Неизвестная ошибка при отправке сообщения пользователю {tg_id}: {e}"
    else:
        response = f"Пользователь {tg_id} недоступен для отправки сообщений"

    return response


@log_function_call
async def send_notification_to_chat_or_channel(
    chat_id: int,
    message_text: str,
    inline_button_text: str = "Принять участие в голосованиях",
    inline_button_callback_data: str = None, # Параметр, который передается при нажатии на кнопку
    member_id: int = None,
    parse_mode: str = "HTML"
):
    """
    Отправляет уведомление в чат или канал с возможностью добавления inline-кнопки.

    :param chat_id: ID чата или канала, куда отправляется уведомление.
    :param message_text: Текст уведомления (может быть в формате HTML).
    :param inline_button_text: Текст для inline-кнопки (опционально). По умолчанию "Принять участие в голосованиях".
    :param inline_button_callback_data: Callback data для inline-кнопки (опционально). Передается как аргумент команды /start.
    :param member_id: ID участника, который является автором уведомления (опционально).
    :param parse_mode: Режим разбора текста ("HTML" по умолчанию).
    :return: Сообщение об успешной отправке или ошибке.
    """
    try:
        #Излекаем имя бота
        bot_username = await get_bot_username()
        # Создаем inline-клавиатуру, если указаны текст и callback_data кнопки
        reply_markup = None
        if inline_button_text and inline_button_callback_data:
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=inline_button_text,
                            url=f"https://t.me/{bot_username}?start={inline_button_callback_data}"
                        )
                    ]
                ]
            )

# Хорошо бы еще добавить к message_text автора, если он есть

        # Попытка отправить сообщение
        await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

        response = f"Уведомление успешно отправлено в чат/канал {chat_id}"

    except TelegramForbiddenError:
        # Канал или чат заблокировали бота
        logger.warning(f"Бот заблокирован в чате/канале {chat_id}.")
        response = f"Бот заблокирован в чате/канале {chat_id}."

    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            # Чат или канал не существует
            logger.warning(f"Чат/канал {chat_id} не найден.")
            response = f"Чат/канал {chat_id} не найден."
        else:
            # Другая ошибка BadRequest
            logger.error(f"Ошибка при отправке уведомления в чат/канал {chat_id}: {e}")
            response = f"Ошибка при отправке уведомления в чат/канал {chat_id}: {e}"

    except TelegramAPIError as e:
        # Любая другая ошибка Telegram API
        logger.error(f"Telegram API Error для чата/канала {chat_id}: {e}")
        response = f"Telegram API Error для чата/канала {chat_id}: {e}"

    except Exception as e:
        # Все остальные исключения
        logger.error(f"Неизвестная ошибка при отправке уведомления в чат/канал {chat_id}: {e}")
        response = f"Неизвестная ошибка при отправке уведомления в чат/канал {chat_id}: {e}"

    return response

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
            f'Имя: {user_dict["tg_first_name"]}\n'
            f'Фамилия: {user_dict["tg_last_name"]}\n'
            f'Истинность контакта: {user_dict["contact_true"]}\n'
            f'Номер телефона: {user_dict["tg_phone_number"]}\n'
            f"Просит вас подтвердить его право\n"
            f"стать членом клуба.\n"
            f"Подтверждаете?"
        )


        # Отправляем сообщение регистратору
        await send_notification_to_user(
            registrator_tg_id,
            message_text,
            markup  # клавиатура подтверждения
        )

        return True, "Уведомление отправлено."
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления регистратору: {e}")
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
            f"Никого из регистраторов он не знает."
            f"Подтверждаете?"
        )

        super_registrators = await list_of_members(club_id,'superregistrator')
        if not super_registrators:
            super_registrators = await list_of_members(club_id,'registrator')


        # Отправляем сообщение суперрегистраторам (а если их нет - регистраторам)
        for registrator in super_registrators:
            registrator_tg_id = registrator[2]
            await send_notification_to_user(
                registrator_tg_id,
                message_text,
                markup  # клавиатура подтверждения
        )

        return True, "Уведомление отправлено."
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления регистратору: {e}")
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
        await send_notification_to_user(
            registrator_tg_id,
            message_text,
            markup  # клавиатура подтверждения
        )

        return True, "Уведомление отправлено."
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления регистратору: {e}")
        return False, str(e)

# Функция уведомления и лишения статуса 'votist' тех пользователей, чей представитель утратил этот статус
@log_function_call
async def not_votist_because_proxy_quit(proxy:int):
    logger.info(f"Лишаем статуса гоосующих тех, чей представитель {proxy} сложил полномочия")
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
            logger.error(f"Ошибка при лишении статуса 'голосующих' доверителей ушедшего представителя: {e}")
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
                    await send_notification_to_user(
                        tg_id,
                        message_text
                    )

                except aiosqlite.Error as e:
                    logger.error(f"Ошибка при лишении статуса голосующего: {e}")
                    raise

# Функция уведомления и присвоения статуса 'votist' тем пользователям, чей представитель возобновил этот статус
@log_function_call
async def votist_because_proxy_returned(proxy:int):
    logger.info(f"Возвращаем статус гоосующих тем, чей представитель {proxy} вернул полномочия")
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
            logger.error(f"Ошибка при возвращении статуса 'голосующих' доверителям вернувшегося представителя: {e}")
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
                    await send_notification_to_user(
                        tg_id,
                        message_text
                    )

                except aiosqlite.Error as e:
                    logger.error(f"Ошибка при лишении статуса голосующего: {e}")
                    raise

# Функция выхода из группы. Передается id участника.
# Производится вызыв функии member_leave_club
# Если участник был представителем вызывается функция not_votist_because_proxy_quit
@log_function_call
async def leave_club (member_id, status):
    logger.info(f"Выход из группы member_id={member_id}")
    await member_leave_club(member_id,status)
    if 'proxy' in status:
        await not_votist_because_proxy_quit(member_id)

# Функция создания приветственного обращения. Использует информацию о группе
@log_function_call
async def greetings_message(club_id:int):
    result = await extract_club_info(club_id)
    if result:
        name, description,father_group, tg_bot, channel_link, conditions_of_entry = result
        response = f"<b>👋 Привет! Я — бот для голосований группы {name}.</b>" + LEXICON.get('greetings',
        'Пройдите регистрацию, чтобы воспользоваться всеми моими возможностями')
        if channel_link:
            response = response + f"<a href='{channel_link}'>[Подпишитесь на наш канал, чтобы быть в курсе всех событий:]</a>"
        logger.debug('Текст приветствия успешно составлен')
    else:
        response = 'Привет! Произошла ошибка, информация о группе не найдена, сообщите об этом администрациии'
        logger.debug('Не найдена информация о группе для составления приветствия')
    return response

# Функция создания справки в зависимости от ролей участника
@log_function_call
def help_message(status_list: list):
    status = set(status_list) - {'votist'}  # Исключаем статус 'votist'
    text = "<b>Справка по вашим ролям:</b>\n\n"  # Заголовок

    for item in sorted(status):  # Сортируем роли для удобства
        role_help = LEXICON.get(item + '_help', f'Для статуса {item} пока нет справки.')
        text += f"📌 <b>{LEXICON.get(item, item.capitalize())}:</b>\n{role_help}\n\n"

    logger.debug(f'Сформирована справка:\n{text}')
    return text

# Функция создания ссылки на публичный канал по его ID
async def get_channel_link(channel_id):
    try:
        chat = await bot.get_chat(chat_id=channel_id)
        if chat.username:
            # Формируем ссылку для публичного канала
            return f"https://t.me/{chat.username}"
        else:
            # Если канал приватный, можно попробовать получить invite link
            invite_link = await bot.export_chat_invite_link(chat_id=channel_id)
            return invite_link
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

# Функция создания пригласительной ссылки в приватный канал (работает, если бот администратор) по ID канала
@log_function_call
async def get_invite_link(channel_id):
    try:
        invite_link = await bot.export_chat_invite_link(chat_id=channel_id)
        return invite_link
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

# Функция создания справки в зависимости от ролей участника
@log_function_call
async def get_channel_id(channel_username): # Имя канала без @
    try:
        chat = await bot.get_chat(chat_id=channel_username)
        channel_id = chat.id
        return channel_id
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

@log_function_call
async def validate_and_get_channel_info(channel_info: str) -> dict:
    """
    Проверяет существование канала/чата и права бота.
    :param channel_info: ID или username канала/чата
    :return: Словарь с информацией о канале/чате или сообщением об ошибке
    """
    try:
        # Определяем, является ли ввод числовым ID или username
        if channel_info.startswith('@') or not channel_info.lstrip('-').isdigit():
            # Это username
            chat = await bot.get_chat(chat_id=channel_info)
            channel_id = chat.id
            channel_type = 'username'
        else:
            # Это ID
            channel_id = int(channel_info)
            chat = await bot.get_chat(chat_id=channel_id)
            channel_type = 'id'

        # Проверяем права бота
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        can_send_messages = member.can_send_messages if hasattr(member, 'can_send_messages') else False
        is_admin = member.status in ['administrator', 'creator']

        if not (is_admin and can_send_messages):
            return {
                "success": False,
                "message": ("Бот не имеет прав на отправку сообщений в этот канал/чат. "
                            "Добавьте бота в администраторы и дайте право на отправку сообщений.")
            }

        # Формируем ответ
        invite_link = None
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        elif chat.invite_link:
            invite_link = chat.invite_link
        else:
            try:
                invite_link = await bot.export_chat_invite_link(chat_id=channel_id)
            except TelegramForbiddenError:
                pass

        return {
            "success": True,
            "channel_id": channel_id,
            "channel_title": chat.title,
            "invite_link": invite_link,
            "input_type": channel_type
        }

    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            return {"success": False, "message": "Канал/чат не найден."}
        return {"success": False, "message": f"Ошибка при получении информации о канале/чате: {e}"}
    except TelegramForbiddenError:
        return {"success": False, "message": "Бот заблокирован в этом канале/чате."}
    except Exception as e:
        logger.error(f"Неизвестная ошибка при проверке канала/чата: {e}")
        return {"success": False, "message": f"Произошла ошибка: {e}"}

@log_function_call
async def process_channel_info(channel_info: str, club_id: int, action: str) -> dict:
    """
    Обрабатывает информацию о канале/чате для различных действий.
    :param channel_info: ID или username канала/чата
    :param club_id: ID группы в базе данных
    :param action: Тип действия ('add', 'remove', 'set_main')
    :return: Словарь с результатом операции
    """
    # Проверяем существование канала и права бота
    validation_result = await validate_and_get_channel_info(channel_info)
    if not validation_result["success"]:
        return {"success": False, "message": validation_result["message"]}

    channel_id = validation_result["channel_id"]
    channel_title = validation_result["channel_title"]
    invite_link = validation_result["invite_link"]

    if action == "add":
        result = await add_telegram_channel(club_id, channel_id, channel_title)
    elif action == "remove":
        result = await remove_telegram_channel(club_id, channel_id)
    elif action == "set_main":
        result = await set_main_channel(club_id, invite_link)
    else:
        return {"success": False, "message": "Неверное действие."}

    return result