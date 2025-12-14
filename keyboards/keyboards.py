# Модуль keyboards
# Содержит кнопки, клавиатуры и функции для их создания

import logging

from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# В самом начале keyboards/keyboards.py, после импортов aiogram
from LEXICON import get_text
from LEXICON.RU.LEXICON_RU import LEXICON_RU
# Ensure LEXICON_RU is not None, fallback to empty dict
LEXICON: dict = LEXICON_RU if LEXICON_RU is not None else {}
from utils import log_function_call

# Настройка логирования
logger = logging.getLogger(__name__)

"""
КНОПКИ И КЛАВИАТУРЫ
"""


# Функция для формирования инлайн-клавиатуры на лету
@log_function_call
def create_inline_kb(
    width: int,
    *args: str,
    lang: str = "en",
    **kwargs: str
) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру из списка или словаря.
    :param width: Количество кнопок в ряду.
    :param args: Список callback_data для кнопок. Текст берётся из лексикона по callback_data.
    :param lang: Язык для локализации (по умолчанию "ru").
    :param kwargs: Словарь {callback_data: text} — текст задан явно, не локализуется.
    :return: Объект InlineKeyboardMarkup.
    """
    try:
        kb_builder = InlineKeyboardBuilder()
        buttons: list[InlineKeyboardButton] = []

        if args:
            for button in args:
                # Используем get_text для локализации
                text = get_text(button, lang=lang)
                buttons.append(InlineKeyboardButton(text=text, callback_data=button))

        if kwargs:
            for button, text in kwargs.items():
                # В kwargs текст задан явно — не локализуем
                buttons.append(InlineKeyboardButton(text=text, callback_data=button))

        kb_builder.row(*buttons, width=width)
        return kb_builder.as_markup()
    except Exception as e:
        logger.error(f"Ошибка при создании инлайн-клавиатуры: {e}")
        raise


# Функция создания инлайн-кнопки
@log_function_call
def button(button: str, lang: str = "en", text: str | None = None) -> InlineKeyboardButton:
    """
    Создает инлайн-кнопку.
    :param button: Callback_data кнопки.
    :param text: Текст на кнопке (если не указан, берется из LEXICON или callback_data).
    :return: Объект InlineKeyboardButton.
    """
    try:
        if text:  # Если текст указан явно
            return InlineKeyboardButton(text=text, callback_data=button)
        else:  # Если текст не указан
            text = get_text(button, lang=lang)  # Пытаемся найти текст в LEXICON
            if not text:  # Если текст не найден ни в LEXICON, ни в callback_data
                text = button  # Используем callback_data как текст
        return InlineKeyboardButton(text=text, callback_data=button)
    except Exception as e:
        logger.error(f"Ошибка при создании кнопки: {e}")
        raise


buttons = {
    "votings": {  # Категория: Голосования
        "user": ["completed_votings"],  # Для статуса 'user'
        "member": [
            "ongoing_votings",
            "completed_votings",
            "future_votings",
        ],  # Для статуса 'member'
        "candidate": [
            "ongoing_votings",
            "completed_votings",
        ],  # Для статуса 'candidate'
        "admin": [
            "ongoing_votings",
            "completed_votings",
            "future_votings",
        ],  # Для статуса 'admin'
        "owner": [
            "ongoing_votings",
            "completed_votings",
            "future_votings",
        ],  # Для статуса 'owner'
    },
    "actions": {  # Категория: Действия
        "user": ["registration", "list_of_proxy"],  # Для статуса 'user'
        "candidate": ["profile", "list_of_proxy"],  # Для статуса 'candidate'
        "member": ["profile", "list_of_proxy"],  # Для статуса 'member'
        "proxy": ["mailing_followers"], # Для статуса 'proxy'
        "delegate": ["new_voting"],  # Для статуса 'delegate'
        "admin": ["mailing_list"],  # Для статуса 'admin'
    },
    "settings": {  # Категория: Настройки
        "admin": ["new_registrator", "registrators_list","tokens","admin_members"],  # Для статуса 'admin'
        "owner": ["new_status", "admin_bot"],  # Для статуса 'owner'
        "superregistrator": ["tokens"],  # Для статуса 'superregistrator'"
    },
}


@log_function_call
def get_keyboard_for_status(status: list[str], lang: str = "en") -> list[list[InlineKeyboardButton]]:
    """
    Возвращает клавиатуру для указанного статуса.

    :param status: Статус, для которого нужно получить клавиатуру.
    :param lang: Язык, для которого нужно получить клавиатуру.
    :return: Клавиатура для указанного статуса.
    """
    data = {"status": status, "lang": lang}


    # Множество для отслеживания уникальных callback_data
    unique_buttons = set()
    keyboard = []

    # Список категорий в порядке приоритета
    categories_order = ["votings", "actions", "settings"]

    for category in categories_order:
        if category not in buttons:
            continue

        for item in status:
            if item in buttons[category]:
                current_buttons = []
                for btn in buttons[category][item]:
                    # Исключаем "Стать представителем", если есть 'proxy'
                    if btn == "become_proxy" and "proxy" in status:
                        continue

                    # Переименовываем "Выбрать представителя" для 'proxy'
                    if btn == "select_proxy" and "proxy" in status:
                        text = "Выбрать заместителя"
                    else:
                        text = get_text(
                            btn, lang=lang
                        )  # Используем текст из LEXICON или callback_data

                    # Добавляем кнопку, если её callback_data уникальна
                    if btn not in unique_buttons:
                        unique_buttons.add(btn)
                        current_buttons.append(
                            InlineKeyboardButton(text=text, callback_data=btn)
                        )

                # Добавляем текущие кнопки в клавиатуру
                keyboard.extend([[btn] for btn in current_buttons])

    return keyboard


@log_function_call
async def user_menu(status: list[str] | None = None, lang:str = "en") -> InlineKeyboardMarkup | None:
    # TODO: Поменять tg_id на member_id в функции и всех ее вызовах. Или вообще убрать tg_id
    data = {"lang": lang}
    try:
        if not status:
            raise ValueError("Не был передан статус пользователя")
        keyboard = get_keyboard_for_status(status)

        # Добавляем кнопку "Информация"
        info_button = InlineKeyboardButton(
#             text=LEXICON.get("info", "Информация"), callback_data="info"
            text=get_text("info", lang=lang), callback_data="info"
        )
        keyboard.append([info_button])

        # Добавляем кнопку "помощь"
        help_button = InlineKeyboardButton(
#             text=LEXICON.get("help", "Помощь"), callback_data="help"
            text=get_text("help", lang=lang), callback_data="help"
        )
        keyboard.append([help_button])

        kb_builder = InlineKeyboardBuilder()
        for row in keyboard:
            kb_builder.row(*row)
        return kb_builder.as_markup()
    except Exception as e:
        logger.error(f"Ошибка при создании меню для пользователя со статусом {status}: {e}")
        raise


# Функция для создания клавиатуры администрирования бота
@log_function_call
def get_admin_menu_keyboard(lang: str = "en"):
    builder = InlineKeyboardBuilder()
    # Основные кнопки администрирования
    builder.button(text="Изменить имя группы", callback_data="edit_club_name")
    builder.button(text="Изменить описание", callback_data="edit_club_description")
    builder.button(
        text="Изменить условия участия", callback_data="edit_club_conditions"
    )
    builder.button(text="Добавить канал", callback_data="add_channel")
    builder.button(text="Удалить канал", callback_data="remove_channel")
    builder.button(text="Установить основной канал", callback_data="set_main_channel")
    builder.button(
#         text=LEXICON.get("set_stage_durations", "Установить продолжительность этапов"),
        text=get_text("set_stage_durations", lang=lang),
        callback_data="set_stage_durations",
    )
    builder.button(
#         text=LEXICON.get("set_threshold", "Установить порог для делегатов"),
        text=get_text("set_threshold", lang=lang),
        callback_data="set_threshold",
    )
    builder.button(
#         text=LEXICON.get("return_to_main_menu", "Назад в главное меню"),
        text=get_text("return_to_main_menu", lang=lang),
        callback_data="main_menu",
    )



    # Настройка расположения кнопок (6 кнопок в 3 ряда по 2, 1 кнопка в последнем ряду)
    builder.adjust(2, 2, 2, 2, 1)

    return builder.as_markup()


# Функция для создания клавиатуры профиля пользователя
@log_function_call
def get_profile_menu_keyboard(status: list, lang: str = 'en'):
    data = {'status': status, 'lang': lang}
    builder = InlineKeyboardBuilder()
    # Основные кнопки профиля
    builder.button(
#         text=LEXICON.get("edit_username", "Изменить псевдоним"),
        text=get_text("edit_username", lang=lang),
        callback_data="edit_username",
    )
    builder.button(
#         text=LEXICON.get("edit_description", "О себе"), callback_data="edit_description"
        text=get_text("edit_description", lang=lang), callback_data="edit_description"
    )
    builder.button(
#         text=LEXICON.get("change_info_level", "Изменить уровень информирования"),
        text=get_text("change_info_level", lang=lang),
        callback_data="change_info_level",
    )

    builder.button(
#         text=LEXICON.get("enter_token", "Ввести токен"),
        text=get_text("enter_token", lang=lang),
        callback_data="enter_token",
    )

    builder.button(
#         text=LEXICON.get("request_token", "Запросить токен"),
        text=get_text("request_token", lang=lang),
        callback_data="request_token",
    )

    # Кнопки в зависимости от статуса
    # Представитель
    if "proxy" in status:
        builder.button(
#             text=LEXICON.get("resign_from_proxy", "Уйти из представителей"),
            text=get_text("resign_from_proxy", lang=lang),
            callback_data="resign_from_proxy",
        )
        builder.button(
#             text=LEXICON.get("select_subproxy", "Выбрать заместителя"),
            text=get_text("select_subproxy", lang=lang),
            callback_data="select_subproxy",
        )
    else:
        builder.button(
#             text=LEXICON.get("select_proxy", "Выбрать представителя"),
            text=get_text("select_proxy", lang=lang),
            callback_data="select_proxy",
        )
        builder.button(
#             text=LEXICON.get("become_proxy", "Стать представителем"),
            text=get_text("become_proxy", lang=lang),
            callback_data="become_proxy",
        )

    # Админ
    if "admin" in status:
        builder.button(
#             text=LEXICON.get("resign_from_admin", "Отказаться от роли администратора"),
            text=get_text("resign_from_admin", lang=lang),
            callback_data="resign_from_admin",
        )

    # Регистратор
    if "registrator" in status:
        builder.button(
#             text=LEXICON.get(
#                 "resign_from_registrator", "Отказаться от роли регистратора"
#             ),
            text=get_text("resign_from_registrator", lang=lang),
            callback_data="resign_from_registrator",
        )

    # Кандидат в регистраторы
    if "pre-registrator" in status:
        builder.button(
#             text=LEXICON.get("become_registrator", "Стать регистратором"),
            text=get_text("become_registrator", lang=lang),
            callback_data="become_registrator",
        )
        builder.button(
#             text=LEXICON.get(
#                 "resign_from_registrator", "Отказаться от роли регистратора"
#             ),
            text=get_text("resign_from_registrator", lang=lang),
            callback_data="resign_from_registrator",
        )

    # Кандидат в участники
    if "candidate" in status:
        builder.button(
#             text=LEXICON.get("registration", "Повторить регистрацию"),
            text=get_text("registration", lang=lang),
            callback_data="registration",
        )

    builder.button(
#         text=LEXICON.get("leave_the_group", "Покинуть группу"),
        text=get_text("leave_the_group", lang=lang),
        callback_data="leave_the_group",
    )

    builder.button(
#         text=LEXICON.get("main_menu", "Назад в главное меню"), callback_data="main_menu"
        text=get_text("main_menu", lang=lang), callback_data="main_menu"
    )

    # Настройка расположения кнопок ( по 2)
    builder.adjust(2)

    return builder.as_markup()


# Функция для создания клавиатуры справочной информации
@log_function_call
def get_info_menu_keyboard(exc: str | None = None, lang: str = 'en'):
    builder = InlineKeyboardBuilder()

    # Список кнопок с их текстами и callback_data
    buttons = [
#         ("club_info", LEXICON.get("club_info", "О группе")),
        ("club_info", get_text("club_info", lang=lang)),
#         ("proxy_list", LEXICON.get("proxy_list", "Список представителей")),
        ("proxy_list", get_text("proxy_list", lang=lang)),
#         ("bot_info", LEXICON.get("bot_info", "О боте")),
        ("bot_info", get_text("bot_info", lang=lang)),
        # ("status_info", LEXICON.get("status_info", "Статусы")),
        # ("status_info", get_text("status_info", lang=lang)),
#         ("about", LEXICON.get("about", "Общие принципы")),
        ("about", get_text("about", lang=lang)),
#         ("main_menu", LEXICON.get("main_menu", "Назад в главное меню")),
        ("main_menu", get_text("main_menu", lang=lang)),
    ]

    # Добавляем кнопки, если их callback_data не совпадает с exc
    for callback_data, text in buttons:
        if callback_data != exc:
            builder.button(text=text, callback_data=callback_data)

    # Настройка расположения кнопок (по 1)
    builder.adjust(1)

    return builder.as_markup()


"""
ИНЛАЙН-КЛАВИАТУРЫ
"""

# # Инлайн-клавиатура для регистрации
# reg_button_1 = InlineKeyboardButton(
#     text="ЗАРЕГИСТРИРОВАТЬСЯ", callback_data="reg_button_pressed"
# )
# reg_markup = InlineKeyboardMarkup(inline_keyboard=[[reg_button_1]])

# Клавиатура для подтверждения
def confirm_markup(lang:str = 'en') -> InlineKeyboardMarkup:
    ok_mod_button = InlineKeyboardButton(text="ВСЁ ВЕРНО", callback_data="ConfirmOK")
    no_mod_button = InlineKeyboardButton(text="НЕВЕРНО", callback_data="ConfirmNotOK")
    back_to_menu_button = InlineKeyboardButton(
#         text=LEXICON.get("main_menu", "Назад в главное меню"), callback_data="main_menu"
        text=get_text("main_menu", lang=lang), callback_data="main_menu"
    )

    confirm = InlineKeyboardMarkup(
        inline_keyboard=[[ok_mod_button, no_mod_button], [back_to_menu_button]],
        one_time_keyboard=True,
    )
    return confirm

# Клавиатура для возврата в главное меню (для прерывания какого-то процесса)
def return_to_main_menu_markup(lang:str = 'en') -> InlineKeyboardMarkup:
    return_to_main_menu_keyboards = {
#         "main_menu": LEXICON.get("return_to_main_menu", "Назад в главное меню")
        "main_menu": get_text("return_to_main_menu", lang=lang)
    }
    return_to_main_menu = create_inline_kb(1, **return_to_main_menu_keyboards)
    return return_to_main_menu

# Клавиатура для вызова главного меню
def main_menu_markup(lang:str = 'en') -> InlineKeyboardMarkup:
#     main_menu_keyboards = {"main_menu": LEXICON.get("main_menu", "Главное меню")}
    main_menu_keyboards = {"main_menu": get_text("main_menu", lang=lang)}
    main_markup = create_inline_kb(1, **main_menu_keyboards)
    return main_markup

# Клавиатура для вызова главного меню на ENG - используется по умолчанию
main_menu_markup_en = main_menu_markup('en')

def variant_markup(lang:str = 'en') -> InlineKeyboardMarkup:
    # Клавиатура для добавления вариантов голосования
    ok_var_button = InlineKeyboardButton(
        text="Добавить еще вариант", callback_data="NewVariant"
    )
    finish_var_button = InlineKeyboardButton(
        text="Завершить добавление вариантов", callback_data="main_menu"
    )
    var_markup = InlineKeyboardMarkup(
        inline_keyboard=[[ok_var_button, finish_var_button]], one_time_keyboard=True
    )
    return var_markup



"""
ОБЫЧНЫЕ КЛАВИАТУРЫ
"""

# # Клавиатура для отправки контакта
# contact_btn = KeyboardButton(text="Отправить телефон", request_contact=True)
# contact_markup = ReplyKeyboardMarkup(
#     resize_keyboard=True, one_time_keyboard=True, keyboard=[[contact_btn]]
# )

# Клавиатура для удаления предыдущей клавиатуры
remove_markup = ReplyKeyboardRemove()

# # Функция для создания клавиатуры администрирования бот
# def get_admin_menu_keyboard():
#     builder = InlineKeyboardBuilder()
#     builder.button(text="Изменить имя группы", callback_data="edit_club_name")
#     builder.button(text="Изменить описание", callback_data="edit_club_description")
#     builder.button(text="Изменить условия участия", callback_data="edit_club_conditions")
#     builder.button(text="Добавить канал", callback_data="add_channel")
#     builder.button(text="Удалить канал", callback_data="remove_channel")
#     builder.button(text="Установить основной канал", callback_data="set_main_channel")
#     builder.adjust(2)
#     return builder.as_markup()

# """
# ДОПОЛНИТЕЛЬНЫЕ КОММЕНТАРИИ
# """

# Если нужно добавить новые клавиатуры или кнопки, можно расширить словарь `status_keyboards`
# или добавить новые функции для их создания.
