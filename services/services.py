# Модуль services
# Содержит фукнции, наприимер, рассылки сообщений пользователям бота
# Вообще-то нарушает логику разделения скрипта на скрипт телеграм-бота и скрипт базы данных.
# Может пределаю позже.

import logging
from aiogram import Bot
import aiosqlite
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
import html
from data_base.db_func import get_club_info, get_profile
# from data_base.telegram_bot_logic import AsyncDatabase, is_votist
from data_base.data_base import *
from keyboards.keyboards import main_menu_markup, create_inline_kb
from config_data.config import Config, load_config
from utils import log_function_call
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
    # logger.debug(f"Пользователь {tg_id} доступен: {is_available}")
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
    inline_button_callback_data: str|None = None, # Параметр, который передается при нажатии на кнопку
    member_id: int|None = None,
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
        # Создаем inline-клавиатуру
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=inline_button_text,
                        url=f"https://t.me/{bot_username}?start={inline_button_callback_data or 'start'}"
                    )
                ]
            ]
        )

        url=f"https://t.me/{bot_username}?start={inline_button_callback_data or 'start'}"

        logger.debug(f"Ссылка для кнопки в канале: {url}")

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
            f'Имя: {user_dict.get("tg_first_name")}\n'
            f'Фамилия: {user_dict.get("tg_last_name")}\n'
            f'Резюме: {user_dict.get("resume")}\n'
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
            f'Имя: {user_dict.get("tg_first_name")}\n'
            f'Фамилия: {user_dict.get("tg_last_name")}\n'
            f'Резюме: {user_dict.get("resume")}\n'
            f"Просит вас подтвердить его право\n"
            f"стать членом клуба.\n"
            f"Подтверждаете?"
        )

        super_registrators = await list_of_members(club_id,'superregistrator')
        if not super_registrators:
            super_registrators = await list_of_members(club_id,'registrator')


        # Отправляем сообщение суперрегистраторам (а если их нет - регистраторам)
        for registrator in super_registrators:
            registrator_tg_id = registrator['tg_id']
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
            username_result = await cursor.fetchone()
            if username_result:
                proxy_name, = username_result
            else:
                proxy_name = 'Имя неизвестно'

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
                    tg_id_result = await cursor.fetchone()
                    if tg_id_result:
                        tg_id, = tg_id_result
                    else:
                        tg_id = None
                    message_text = f'''
Ваш представитель {proxy_name} утратил статус представителя.
Выберите другого или сами станьте представителем, чтобы иметь право решающего голоса.
Для начала работы наберите или нажмите команду /start
'''
                    # Отправляем сообщение участннику, чей представитель ушел в отставку
                    if tg_id:
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
            username_result = await cursor.fetchone()
            if username_result:
                proxy_name, = username_result
            else:
                proxy_name = 'Имя неизвестно'

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
                    tg_id_result = await cursor.fetchone()
                    if tg_id_result:
                        tg_id, = tg_id_result
                    else:
                        tg_id = None
                    message_text = f'''
Ваш представитель {proxy_name} вернул статус представителя.
Теперь ваш голос будет учитываться при голосованиях.
Для начала работы наберите или нажмите команду /start
'''
                    # Отправляем сообщение участннику, чей представитель ушел в отставку
                    if  tg_id:
                        await send_notification_to_user(
                            tg_id,
                            message_text
                        )

                except aiosqlite.Error as e:
                    logger.error(f"Ошибка при лишении статуса голосующего: {e}")
                    raise



# Функция создания приветственного обращения. Использует информацию о группе
@log_function_call
async def greetings_message(club_id:int):
    result = await get_club_info(club_id)
    if result:
        # name, description,father_group, tg_bot, channel_link, conditions_of_entry = result
        response = f"<b>👋 Привет! Я — бот для голосований группы {result.get('name')}.</b>" + LEXICON.get('greetings',
        'Пройдите регистрацию, чтобы воспользоваться всеми моими возможностями')
        if result.get('channel_link'):
            response = response + f"<a href='{result.get('channel_link')}'>[Подпишитесь на наш канал, чтобы быть в курсе всех событий:]</a>"
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

# Функция создания справки о группе
@log_function_call
async def club_info(club_id:int):
    info = await get_club_info(club_id)
    if not info:
        logger.error('Не найдена информация о группе')
        raise  Exception( 'Ошибка. Не найдена информация о группе')
    amount = await count_member(club_id)
    text = (
        f'Название группы: {info.get("name","Отсутствует")}\n\n'
        f"Описание группы:\n{info.get('description','Отсутсвует')}\n\n"
        f"Условия участия в группе (кто может быть участником):\n{info.get('conditions_of_entry', 'Отсутствуют')}\n\n"
        f"Количество участников: {amount}"
    )
    logger.debug(f'Сформирована справка о группе:\n{text}')
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
        """ Извлекает username/ID из разных форматов """
        # Обработка ссылок
        if channel_info.startswith(("https://", "http://", "t.me")):
            parts = channel_info.split("/")
            username = parts[-1].split("?")[0]  # Убираем GET-параметры
            if not username.startswith("@"):
                username = "@" + username
            channel_info = username

        # Определяем, является ли ввод числовым ID или username
        if channel_info.startswith('@') or not channel_info.lstrip('-').isdigit():
            # Это username
            chat = await bot.get_chat(chat_id=channel_info)
            channel_id = chat.id

        else:
            # Это ID
            channel_id = int(channel_info)
            chat = await bot.get_chat(chat_id=channel_id)

        # Проверяем права бота
        chat = await bot.get_chat(chat_id=channel_id)
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)

        # Определяем тип чата
        is_channel = chat.type == 'channel'
        is_group = chat.type in ['group', 'supergroup']

        # Проверяем права в зависимости от типа
        if is_channel:
            # Для каналов
            can_send = getattr(member, 'can_post_messages', False)
            required_admin = True  # В каналах бот должен быть админом
            channel_type = 'channel'
        elif is_group:
            # Для чатов (групп/супергрупп)
            can_send = getattr(member, 'can_send_messages', False)
            required_admin = False  # В чатах можно быть обычным участником
            channel_type = 'chat'
        else:
            return {
                "success": False,
                "message": "Тип чата не определен."
            }

        # Проверяем статус админа (для каналов обязательно)
        is_admin = member.status in ['administrator', 'creator']
        if required_admin and not is_admin:
            return {
                "success": False,
                "message": "Бот должен быть администратором канала."
            }

        # Проверяем права на отправку
        if not can_send:
            return {
                "success": False,
                "message": "Бот не имеет прав на отправку сообщений. Настройте права доступа."
            }

        logger.debug(f"Статус бота: {member.status}, can_send_messages: {hasattr(member, 'can_send_messages')}")

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
            "channel_type": channel_type
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
    channel_type =  validation_result["channel_type"]

    if action == "add":
        result = await add_telegram_channel(club_id, channel_id, channel_title, channel_type, invite_link)
    elif action == "remove":
        result = await remove_telegram_channel(club_id, channel_id)
    elif action == "set_main":
        add_result = await add_telegram_channel(club_id, channel_id, channel_title, channel_type, invite_link)
        logger.info(f"Результат добавления канала в список рассылки при его установке, как основного:{add_result}")
        result = await set_main_channel(club_id, invite_link)
        result["add_channel"] = add_result
    else:
        return {"success": False, "message": "Неверное действие."}

    return result

async def profile_message(member_id, status):
    profile = await get_profile(member_id)
    text = 'Данные вашего профиля:\n'
    if profile.get('username'):
        text += f"Псевдоним: {profile.get('username')}\n"
    if profile.get('description'):
        text += f"Ваше описание:\n{profile.get('description')}\n"
    if profile.get('info_level'):
        text += f"Уровень информирования: {profile.get('info_level')}\n"
    if profile.get('proxy_username'):
        if 'proxy' in status:
            text += f"Ваш заместитель: {profile.get('proxy_username')}\n"
        else:
            text += f"Ваш представитель: {profile.get('proxy_username')}\n"
    text+=LEXICON.get('profile_menu','Выберите, что хотите поменять в профиле') # Сюда вставить функцию создания текста
    return text



async def send_variants_by_status(
    callback: CallbackQuery,
    variant_status: str,
    voting_id: int,
    member_id: int,
    member_status: List[str],):
    """
    Отправляет пользователю список вариантов с указанным статусом.
    Добавляет пометки о выборе пользователя и его представителя.

    :param callback: объект CallbackQuery
    :param variant_status: статус вариантов ('valid', 'winner', 'loser', 'invalid')
    :param voting_id: ID голосования
    :param member_id: ID участника (для проверки выбора)
    """

    if not callback.message:
        raise ValueError("Нет сообщения в callback.")


    # Получаем информацию о голосовании
    voting_info = await get_voting_info(voting_id)
    if not voting_info:
        logger.error(f"Голосование с voting_id={voting_id} не найдено.")
        raise  ValueError(f"Го<h1/> с voting_id={voting_id} не найдено.")
    voting_status = voting_info.get('voting_status')

    # Получаем список вариантов нужного статуса
    variants = await list_of_variants(voting_id, variant_status)

    # Если вариантов нет — ничего не отправляем
    if not variants:
        return False

    # Сортируем варианты по total_votes в порядке убывания
    variants = sorted(
        variants,
        key=lambda v: (v.get('directly_votes', 0) + v.get('proxy_votes', 0)),
        reverse=True
    )

    # Получаем выбор пользователя и его представителя
    choise = await extract_member_choise(member_id, voting_id)
    proxy_choice = await extract_proxy_choice(member_id, voting_id)

    # Формируем заголовок
    status_title_map = LEXICON.get('status_title_map')

    if status_title_map:
        title_text = status_title_map.get(variant_status, f'Варианты со статусом "{variant_status}"')
    else:
        title_text = f'Варианты со статусом "{variant_status}"'

    await callback.message.answer(
        text=f"<b>{title_text}</b>",
        parse_mode="HTML"
    )

    # Обрабатываем каждый вариант
    for variant in variants:
        variant_id = variant['id']
        title = variant['title']
        text_var = variant['text']

        # Подготовка пометок
        choise_mark = ''
        proxy_mark = ''

        if choise and variant_id in choise:
            choise_mark = '📌 ***ВАШ ВЫБОР***\n'

        if proxy_choice and variant_id == proxy_choice:
            proxy_mark = '🔹 ***Выбор вашего представителя***\n'

        # Экранируем HTML
        escaped_title = html.escape(title)
        escaped_text_var = html.escape(text_var)

        # Формируем кнопки
        markup = None

        if variant_status == 'valid':
            if voting_status in ['ongoing', 'confirmation'] and 'member' in member_status:
                keyboard = {f'variant:{variant_id}': LEXICON["Vote for this variant"]}
                markup = create_inline_kb(1, **keyboard)
            elif voting_status == 'add_variants' and 'admin' in member_status:
                keyboard = {f'delete_variant:{variant_id}': LEXICON["delete variant"]}
                markup = create_inline_kb(1, **keyboard)

        # Формируем текст
        if variant_status == 'invalid':
            message_text = (
                f"{choise_mark}{proxy_mark}"
                f"🗑️ <b>{escaped_title}</b>\n\n"
                f"📝 <b>Описание:</b>\n{escaped_text_var}\n\n"
                "<i>Статистика голосов не доступна</i>"
            )
        else:
            dir_votes = variant.get('directly_votes') or 0
            proxy_votes = variant.get('proxy_votes') or 0
            empty_votes = variant.get('empty_votes') or 0
            total_votes = dir_votes + proxy_votes

            message_text = (
                f"{choise_mark}{proxy_mark}"
                f"🗳️ <b>{escaped_title}</b>\n\n"
                f"📝 <b>Описание:</b>\n{escaped_text_var}\n\n"
                "📊 <b>Статистика голосов:</b>\n"
                f"• Решающих голосов: <b>{total_votes}</b>\n"
                f"  - Напрямую: {dir_votes}\n"
                f"  - Через представителей: {proxy_votes}\n"
                f"• Нерешающих голосов: {empty_votes}"
            )

        await callback.message.answer(
            text=message_text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    return True