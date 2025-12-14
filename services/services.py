# Модуль services
# Содержит фукнции, наприимер, рассылки сообщений пользователям бота
# Вообще-то нарушает логику разделения скрипта на скрипт телеграм-бота и скрипт базы данных.
# Может пределаю позже.

import asyncio
import html
import logging
from typing import List
import os
from aiogram import Bot
from aiogram.exceptions import (TelegramAPIError, TelegramBadRequest,
                                TelegramForbiddenError)
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, FSInputFile)

from config_data.config import Config, load_config
# from data_base.telegram_bot_logic import AsyncDatabase, is_votist
from data_base.db_func import AsyncDatabase, add_telegram_channel, count_member, get_club_info, get_profile, get_tg_id_by_member_id, list_of_followers, list_of_members, list_of_variants, remove_telegram_channel, set_main_channel
from data_base.db_member import is_user_available, is_votist, mark_user_as_unavailable
from data_base.db_vote import count_directly_empty_votes, count_directly_votes, count_proxy_votes, extract_member_choise, extract_proxy_choice, get_voting_info
from keyboards.keyboards import create_inline_kb
from LEXICON import get_text
from utils import log_function_call

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
path_db = config.db.path_db  # путь к базе данных
# club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)

# Получение информации о боте
async def get_bot_username(bot: Bot):
    bot_info = await bot.get_me()
    return bot_info.username

# Функция уведомления пользователя
@log_function_call
async def send_notification_to_user(bot: Bot, tg_id: int, message_text: str, reply_markup = None, lang: str = "en"):
    is_available = await is_user_available(tg_id)
    # if not reply_markup: reply_markup = main_menu_markup(lang)
    # logger.debug(f"Пользователь {tg_id} доступен: {is_available}")
    if is_available:
        try:
            # Попытка отправить сообщение
            await bot.send_message(
                tg_id,
                text=message_text,
                reply_markup=reply_markup
            )

            # Задержка между сообщениями, чтобы не забанил телеграм
            await asyncio.sleep(0.05)
            return f'Сообщение отправлено пользователю {tg_id}'
        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            logger.warning(f"Пользователь {tg_id} заблокировал бота.")
            await mark_user_as_unavailable(tg_id, reason="bot blocked")
            await asyncio.sleep(0.05)
            return f"Пользователь {tg_id} заблокировал бота."
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                # Чат не найден (пользователь удалил аккаунт)
                logger.warning(f"Пользователь {tg_id} удалил аккаунт или чат не существует.")
                await mark_user_as_unavailable(tg_id, reason="user lost")
                await asyncio.sleep(0.05)
                return f"Пользователь {tg_id} удалил аккаунт или чат не существует."

            else:
                # Другая ошибка BadRequest
                logger.error(f"Ошибка при отправке сообщения пользователю {tg_id}: {e}")
                await asyncio.sleep(0.05)
                return f"Ошибка при отправке сообщения пользователю {tg_id}: {e}"
        except TelegramAPIError as e:
            # Любая другая ошибка Telegram API
            logger.error(f"Telegram API Error для пользователя {tg_id}: {e}")
            await asyncio.sleep(0.05)
            return f"Telegram API Error для пользователя {tg_id}: {e}"
        except Exception as e:
            # Все остальные исключения
            logger.error(f"Неизвестная ошибка при отправке сообщения пользователю {tg_id}: {e}")
            await asyncio.sleep(0.05)
            return f"Неизвестная ошибка при отправке сообщения пользователю {tg_id}: {e}"
    else:
        await asyncio.sleep(0.05)
        return f"Пользователь {tg_id} недоступен для отправки сообщений"



@log_function_call
async def send_notification_to_members(
    bot: Bot,
    club_id: int,
    message_text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    lang: str = "en",
    status: str | list[str] = "all",
) -> str:
    try:
        members = await list_of_members(club_id, status)
        sent_count = 0
        failed_count = 0

        for i, member in enumerate(members):
            tg_id = member.get("tg_id")
            if not isinstance(tg_id, int) or tg_id is None:
                logger.warning(f"Пропускаем участника: некорректный tg_id={tg_id}")
                failed_count += 1
                continue

            result = await send_notification_to_user(bot, tg_id, message_text)
            if "отправлено" in result or "успешно" in result or "sender" in result or "sent" in result or "success" in result:
                sent_count += 1
            else:
                failed_count += 1

            if (i + 1) % 20 == 0:
                await asyncio.sleep(1)

        return f"✅ Рассылка завершена: {sent_count} отправлено, {failed_count} ошибок"
    except Exception as e:
        logger.error(f"Ошибка при подготовке рассылки: {e}")
        return f"❌ Ошибка при получении списка участников: {e}"

@log_function_call
async def send_notification_to_followers(
    bot: Bot,
    club_id: int,
    message_text: str,
    proxy: int,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
    lang: str = "en",
) -> str:
    club_info = await get_club_info(club_id)
    if not club_info:
        logger.error(f"Группа {club_id} не найдена")
        raise ValueError(f"Group {club_id} not found")
    data = {"club_id": club_id, "lang": club_info.get("lang", "ru")}
    logger.debug(f"Отправка сообщения {message_text} в подписчиков {proxy}")
    message_text_with_header = f"📩 От вашего представителя:\n\n{message_text}"
    try:
        followers = await list_of_followers(proxy)
        logger.info(f"Запущена рассылка от представителя {proxy} для {len(followers)} подписчиков")
        sent_count = 0
        failed_count = 0

        for i, tg_id in enumerate(followers):
            if not isinstance(tg_id, int) or tg_id is None:
                logger.warning(f"Пропускаем участника: некорректный tg_id={tg_id}")
                failed_count += 1
                continue

            result = await send_notification_to_user(bot, tg_id, message_text_with_header)
            if "отправлено" in result or "успешно" in result:
                sent_count += 1
            else:
                failed_count += 1

            if (i + 1) % 20 == 0:
                await asyncio.sleep(1)

        return f"✅ Рассылка завершена: {sent_count} отправлено, {failed_count} ошибок"
    except Exception as e:
        logger.error(f"Ошибка при подготовке рассылки: {e}")
        return f"❌ Ошибка при получении списка участников: {e}"

@log_function_call
async def send_notification_to_chat_or_channel(
    bot: Bot,
    chat_id: int,
    message_text: str,
    inline_button_text: str = "Принять участие в голосованиях",
    inline_button_callback_data: str|None = None, # Параметр, который передается при нажатии на кнопку
    member_id: int|None = None,
    lang: str = "en",
    parse_mode: str = "HTML"
):
    """
    Отправляет уведомление в чат или канал с возможностью добавления inline-кнопки.

    :param bot: Экземпляр бота Aiogram.
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
        bot_username = await get_bot_username(bot)
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
        # Задержка между сообщениями, чтобы не забанил телеграм
        await asyncio.sleep(0.05)
        return f"Уведомление успешно отправлено в чат/канал {chat_id}"

    except TelegramForbiddenError:
        # Канал или чат заблокировали бота
        logger.warning(f"Бот заблокирован в чате/канале {chat_id}.")
        return f"Бот заблокирован в чате/канале {chat_id}."

    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            # Чат или канал не существует
            logger.warning(f"Чат/канал {chat_id} не найден.")
            return f"Чат/канал {chat_id} не найден."
        else:
            # Другая ошибка BadRequest
            logger.error(f"Ошибка при отправке уведомления в чат/канал {chat_id}: {e}")
            return f"Ошибка при отправке уведомления в чат/канал {chat_id}: {e}"

    except TelegramAPIError as e:
        # Любая другая ошибка Telegram API
        logger.error(f"Telegram API Error для чата/канала {chat_id}: {e}")
        return f"Telegram API Error для чата/канала {chat_id}: {e}"

    except Exception as e:
        # Все остальные исключения
        logger.error(f"Неизвестная ошибка при отправке уведомления в чат/канал {chat_id}: {e}")
        return f"Неизвестная ошибка при отправке уведомления в чат/канал {chat_id}: {e}"


@log_function_call
async def send_file_to_user(bot: Bot, tg_id: int, file_path: str, caption: str = "Файл", reply_markup=None, lang: str = "en"):
    """
    Отправляет файл пользователю по его tg_id.

    :param tg_id: ID пользователя в Telegram
    :param file_path: Путь к файлу на сервере
    :param caption: Подпись к файлу (опционально)
    :param reply_markup: Клавиатура (опционально)
    :return: Результат отправки
    """
    is_available = await is_user_available(tg_id)
    if not is_available:
        return f"Пользователь {tg_id} недоступен для отправки."

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл {file_path} не найден.")

        # Создаем объект файла для отправки
        document = FSInputFile(path=file_path)

        # Отправляем документ

        await bot.send_document(
            chat_id=tg_id,
            document=document,
            caption=caption,
            reply_markup=reply_markup
        )
        # Задержка между сообщениями, чтобы не забанил телеграм
        await asyncio.sleep(0.05)
        return f"Файл успешно отправлен пользователю {tg_id}"

    except TelegramForbiddenError:
        logger.warning(f"Пользователь {tg_id} заблокировал бота.")
        await mark_user_as_unavailable(tg_id, reason="bot blocked")
        return f"Пользователь {tg_id} заблокировал бота."

    except TelegramBadRequest as e:
        if "chat not found" in str(e).lower():
            logger.warning(f"Пользователь {tg_id} удалил аккаунт или чат не существует.")
            await mark_user_as_unavailable(tg_id, reason="user lost")
            return f"Пользователь {tg_id} удалил аккаунт или чат не существует."

        else:
            logger.error(f"Ошибка при отправке файла пользователю {tg_id}: {e}")
            return f"Ошибка при отправке файла пользователю {tg_id}: {e}"
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке файла пользователю {tg_id}: {e}")
        return f"Неизвестная ошибка при отправке файла пользователю {tg_id}: {e}"


#Функция уведомления регистратора при краткой регистрации.
@log_function_call
async def notify_registrator_short(bot: Bot, club_id: int, registrator_tg_id, candidate_tg_id, user_dict, lang: str = 'en'):
    club_info = await get_club_info(club_id)
    if not club_info:
        logger.error(f"Группа {club_id} не найдена")
        return (False, "Group not found")
    data = {"club_id": club_id, "lang": club_info.get("lang", "ru")}
    try:
        logger.debug(f"Данные пользователя для регистрации: {user_dict}")
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
            "Пользователь с данными:\n"
            f'Имя: {user_dict.get("tg_first_name")}\n'
            f'Фамилия: {user_dict.get("tg_last_name")}\n'
            f'Резюме: {user_dict.get("resume")}\n'
            "Просит вас подтвердить его право\n"
            "стать членом клуба.\n"
            "Подтверждаете?"
        )


        # Отправляем сообщение регистратору
        await send_notification_to_user(
            bot,
            registrator_tg_id,
            message_text,
            markup,  # клавиатура подтверждения
        )

        return True, "Уведомление отправлено."
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления регистратору: {e}")
        return False, str(e)

#Функция уведомления суперрегистратора при краткой регистрации.
@log_function_call
async def notify_super_registrator_short(bot, club_id, candidate_tg_id, user_dict, lang: str = ''):
    club_info = await get_club_info(club_id)
    if not club_info:
        logger.error(f"Группа {club_id} не найдена")
        return (False, "Group not found")
    data = {"club_id": club_id, "lang": lang or club_info.get("lang", "ru")}
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
            f'Имя: {user_dict.get("first_name") or user_dict.get("tg_first_name") or "Не указано"}\n'
            f'Фамилия: {user_dict.get("last_name") or user_dict.get("tg_last_name") or "Не указано"}\n'
            f'Резюме: {user_dict.get("resume") or "Не указано"}\n'
            f"Просит вас подтвердить его право\n"
            f"стать членом клуба.\n"
            f"Подтверждаете?"
        )

        if user_dict.get('status') and 'member' in user_dict.get('status'):
            message_text = (
                f"Пользователь с данными:\n"
                f'Имя: {user_dict.get("first_name") or user_dict.get("tg_first_name") or "Не указано"}\n'
                f'Фамилия: {user_dict.get("last_name") or user_dict.get("tg_last_name") or "Не указано"}\n'
                f'Резюме: {user_dict.get("resume") or "Не указано"}\n'
                f"Просит новый токен\n"
        )


        super_registrators = await list_of_members(club_id,'superregistrator')
        if not super_registrators:
            super_registrators = await list_of_members(club_id,'registrator')


        # Отправляем сообщение суперрегистраторам (а если их нет - регистраторам)
        for registrator in super_registrators:
            registrator_tg_id = registrator['tg_id']
            await send_notification_to_user(
                bot,
                registrator_tg_id,
                message_text,
                markup,  # клавиатура подтверждения
        )

        return True, "Уведомление отправлено."
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления регистратору: {e}")
        return False, str(e)




@log_function_call
async def _notify_trustees(bot: Bot, proxy_id: int, message_template: str):
    """

    """
    async with AsyncDatabase(path_db) as cursor:
        await cursor.execute('''SELECT username FROM Users WHERE id IN (SELECT user_id FROM Members WHERE id = ?)''', (proxy_id,))
        row = await cursor.fetchone()
        if row:
            proxy_name = row[0]
        else:
            proxy_name ="Имя неизвестно"

        await cursor.execute('SELECT id FROM Members WHERE proxy = ?', (proxy_id,))
        trustees = await cursor.fetchall()

    for (member_id,) in trustees:
        await is_votist(member_id)
        tg_id = await get_tg_id_by_member_id(member_id)  # вынеси в отдельную функцию
        if tg_id:
            text = message_template.format(proxy_name=proxy_name)
            await send_notification_to_user(bot, tg_id, text)

async def not_votist_because_proxy_quit(bot: Bot, proxy: int, lang: str = "en"):
    """
    Функция уведомления о том, что представитель ушел в отставку
    """
    template = "Ваш представитель {proxy_name} ушёл. Выберите нового..."
    await _notify_trustees(bot, proxy, template)

async def votist_because_proxy_returned(bot: Bot, proxy: int, lang: str = "en"):
    """
    Функция уведомления о том, что представитель вернулся
    """
    template = "Ваш представитель {proxy_name} вернулся. Ваш голос учитывается!"
    await _notify_trustees(bot, proxy, template)


# Функция создания приветственного обращения. Использует информацию о группе
@log_function_call
async def greetings_message(club_id:int, lang:str = 'en'):
    result = await get_club_info(club_id)
    if result:
        # name, description,father_group, tg_bot, channel_link, conditions_of_entry = result
#         response = f"<b>👋 Привет! Я — бот для голосований группы {result.get('name')}.</b>" + LEXICON.get('greetings',
#         'Пройдите регистрацию, чтобы воспользоваться всеми моими возможностями')
        bot_name = result.get('name')
        response = f"<b>👋 Привет! Я — бот для голосований группы {bot_name}.</b>" + get_text("greetings", lang=lang)
        if result.get('channel_link'):
            logger.debug('Текст приветствия успешно составлен')
            channel_link = result.get('channel_link')
            return response + f"<a href='{channel_link}'>[Подпишитесь на наш канал, чтобы быть в курсе всех событий:]</a>"
        logger.debug('Текст приветствия успешно составлен')
    else:
        logger.debug('Не найдена информация о группе для составления приветствия')
        return 'Привет! Произошла ошибка, информация о группе не найдена, сообщите об этом администрациии'


# Функция создания справки в зависимости от ролей участника
@log_function_call
def help_message(status_list: list, lang: str = 'en'):
    status = set(status_list) - {'votist'}  # Исключаем статус 'votist'
    text = "<b>Справка по вашим ролям:</b>\n\n"  # Заголовок

    for item in sorted(status):  # Сортируем роли для удобства
#         role_help = LEXICON.get(item + '_help', f'Для статуса {item} пока нет справки.')
        role_help = get_text("_help", lang=lang)
        role = get_text(item, lang=lang)
        text += f"📌 <b>{role}:</b>\n{role_help}\n\n"

    logger.debug(f'Сформирована справка:\n{text}')
    return text

# Функция создания справки о группе
@log_function_call
async def club_info(club_id:int, lang:str = 'en'):
    info = await get_club_info(club_id)
    if not info:
        logger.error('Не найдена информация о группе')
        raise  Exception( 'Ошибка. Не найдена информация о группе')
    data = {"club_id": club_id, "lang": info.get("lang", "ru")}
    amount = await count_member(club_id)
    text = (
        f'Название группы: {info.get("name", "Отсутствует")}\n\n'
        f"Описание группы:\n{info.get('description','Отсутсвует')}\n\n"
        f"Условия участия в группе (кто может быть участником):\n{info.get('conditions_of_entry', 'Отсутствуют')}\n\n"
        f"Количество участников: {amount}"
    )
    logger.debug(f'Сформирована справка о группе:\n{text}')
    return text


# Функция создания ссылки на публичный канал по его ID
async def get_channel_link(bot: Bot, channel_id: int):
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
async def get_invite_link(bot: Bot, channel_id):
    try:
        invite_link = await bot.export_chat_invite_link(chat_id=channel_id)
        return invite_link
    except Exception as e:
        print(f"Ошибка: {e}")
        return None


@log_function_call
async def get_channel_id(bot: Bot, channel_username): # Имя канала без @
    """
    Получение ID канала по его имени
    """
    try:

        chat = await bot.get_chat(chat_id=channel_username)
        channel_id = chat.id
        return channel_id
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

@log_function_call
async def validate_and_get_channel_info(bot: Bot, channel_info: str, lang: str = 'en') -> dict:
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
async def process_channel_info(bot: Bot, channel_info: str, club_id: int, action: str) -> dict:
    """
    Обрабатывает информацию о канале/чате для различных действий.
    :param channel_info: ID или username канала/чата
    :param club_id: ID группы в базе данных
    :param action: Тип действия ('add', 'remove', 'set_main')
    :return: Словарь с результатом операции
    """
    # Проверяем существование канала и права бота
    validation_result = await validate_and_get_channel_info(bot, channel_info)
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

async def profile_message(member_id, status, lang = ''):
    profile = await get_profile(member_id)
    lang = lang or profile.get('lang') or 'en'
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
    if profile.get('token'):
        text += f"Ваш токен: {profile.get('token')}\n"
#     text+=LEXICON.get('profile_menu','Выберите, что хотите поменять в профиле') # Сюда вставить функцию создания текста
    text+=get_text("profile_menu", lang=lang) # Сюда вставить функцию создания текста
    return text



async def send_variants_by_status(
    callback: CallbackQuery,
    variant_status: str,
    voting_id: int,
    member_id: int,
    member_status: List[str],
    lang: str = ""
    ):
    """
    Отправляет пользователю список вариантов с указанным статусом.
    Добавляет пометки о выборе пользователя и его представителя.

    :param callback: объект CallbackQuery
    :param variant_status: статус вариантов ('valid', 'winner', 'loser', 'invalid')
    :param voting_id: ID голосования
    :param member_id: ID участника (для проверки выбора)
    """

    profile = await get_profile(member_id)
    if not profile: return
    lang = lang or profile.get('lang') or 'en'

    if not callback.message:
        logger.error("Нет сообщения в callback.")
        return False



    # Получаем информацию о голосовании
    voting_info = await get_voting_info(voting_id)
    if not voting_info:
        logger.error(f"Голосование с voting_id={voting_id} не найдено.")
        return False
    voting_status = voting_info.get('voting_status')

    # Получаем список вариантов нужного статуса
    variants = await list_of_variants(voting_id, variant_status)

    # Если вариантов нет — ничего не отправляем
    if not variants:
        return False

    # Если в строке варианта указано число голосов (то есть, вариант уже выбыл из голосования), то отправляем их.
    # Если не указано - подсчитываем текущее число голосов за этот вариант
    for  variant in variants:
        if variant.get('directly_votes') == None: variant['directly_votes'] = await count_directly_votes(variant['id'])
        if variant.get('proxy_votes') == None: variant['proxy_votes'] = await count_proxy_votes(variant['id'])
        if variant.get('empty_votes') == None: variant['empty_votes'] = await count_directly_empty_votes(variant['id'])

    # Сортируем варианты по total_votes в порядке убывания
    variants = sorted(
        variants,
        key=lambda v: ((v.get('directly_votes') or 0) + (v.get('proxy_votes') or 0)),
        reverse=True
    )

    # Получаем выбор пользователя и его представителя
    choise = await extract_member_choise(member_id, voting_id)
    proxy_choice = await extract_proxy_choice(member_id, voting_id)

    # Формируем заголовок
#     status_title_map = LEXICON.get('status_title_map')
    status_title_map = get_text("status_title_map", lang=lang)

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

        if proxy_choice and variant_id in proxy_choice:
            proxy_mark = '🔹 ***Выбор вашего представителя***\n'

        # Экранируем HTML
        escaped_title = html.escape(title)
        escaped_text_var = html.escape(text_var)

        # Формируем кнопки
        markup = None

        if variant_status == 'valid':
            if voting_status in ['ongoing', 'confirmation'] and 'member' in member_status and not choise_mark:
#                 keyboard = {f'variant:{variant_id}': LEXICON["Vote for this variant"]}
                keyboard = {f'variant:{variant_id}': get_text("Vote for this variant", lang=lang)}
                markup = create_inline_kb(1, **keyboard)
            elif voting_status == 'add_variants' and 'admin' in member_status:
#                 keyboard = {f'delete_variant:{variant_id}': LEXICON["delete variant"]}
                keyboard = {f'delete_variant:{variant_id}': get_text("delete variant", lang=lang)}
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