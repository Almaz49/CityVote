# Модуль keyboards
# Содержит кнопки и клавиатуры

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from LEXICON.LEXICON import *
from data_base.telegram_bot_logic import extract_status_tg
from utils import log_function_call
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

"""
КНОПКИ И КЛАВИАТУРЫ
"""

# Функция для формирования инлайн-клавиатуры на лету
@log_function_call
def create_inline_kb(width: int, *args: str, **kwargs: str) -> InlineKeyboardMarkup:
    """
    Создает инлайн-клавиатуру из списка или словаря.
    :param width: Количество кнопок в ряду.
    :param args: Список callback_data для кнопок.
    :param kwargs: Словарь {callback_data: text} для кнопок.
    :return: Объект InlineKeyboardMarkup.
    """
    try:
        # Инициализируем билдер
        kb_builder = InlineKeyboardBuilder()
        buttons: list[InlineKeyboardButton] = []

        # Добавляем кнопки из args
        if args:
            for button in args:
                text = LEXICON.get(button, button)  # Пытаемся найти текст в LEXICON
                if not text:  # Если текст не найден ни в LEXICON, ни в callback_data
                    text = button  # Используем callback_data как текст
                buttons.append(InlineKeyboardButton(
                    text=text,
                    callback_data=button
                ))

        # Добавляем кнопки из kwargs
        if kwargs:
            for button, text in kwargs.items():
                buttons.append(InlineKeyboardButton(
                    text=text,
                    callback_data=button
                ))

        # Распаковываем кнопки в билдер
        kb_builder.row(*buttons, width=width)
        return kb_builder.as_markup()
    except Exception as e:
        logging.error(f"Ошибка при создании инлайн-клавиатуры: {e}")
        raise


# Функция создания инлайн-кнопки
@log_function_call
def button(button: str, text: str = None) -> InlineKeyboardButton:
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
            text = LEXICON.get(button, button)  # Пытаемся найти текст в LEXICON
            if not text:  # Если текст не найден ни в LEXICON, ни в callback_data
                text = button  # Используем callback_data как текст
        return InlineKeyboardButton(text=text, callback_data=button)
    except Exception as e:
        logging.error(f"Ошибка при создании кнопки: {e}")
        raise


buttons = {
    'votings': {  # Категория: Голосования
        'user': ['completed_votings'],                  # Для статуса 'user'
        'member': ['ongoing_votings', 'completed_votings', 'future_votings'],  # Для статуса 'member'
        'candidate': ['ongoing_votings', 'completed_votings'],                  # Для статуса 'candidate'
        'admin': ['ongoing_votings', 'completed_votings', 'future_votings'],  # Для статуса 'admin'
        'owner': ['ongoing_votings', 'completed_votings', 'future_votings']  # Для статуса 'owner'
    },
    'actions': {  # Категория: Действия
        'user':['registration'],                                      #Для статуса 'user'
        'candidate':['leave_the_group'],                             #Для статуса 'candidate'
        'member': ['select_proxy', 'become_proxy','leave_the_group'],      # Для статуса 'member'
        'proxy': ['resign_from_proxy'],                  # Для статуса 'proxy'
        'delegate': ['new_voting', 'new_variant'],          # Для статуса 'delegate'
        'admin':['voting_start']                           #для статуса 'админ'
    },
    'settings': {  # Категория: Настройки
        'admin': ['new_status'],                         # Для статуса 'admin'
        'owner': ['new_status']                          # Для статуса 'owner'
    }
}

@log_function_call
def get_keyboard_for_status(status: list[str]) -> list[list[InlineKeyboardButton]]:
    # Множество для отслеживания уникальных callback_data
    unique_buttons = set()
    keyboard = []


    # Список категорий в порядке приоритета
    categories_order = ['votings', 'actions', 'settings']

    for category in categories_order:
        if category not in buttons:
            continue

        for item in status:
            if item in buttons[category]:
                current_buttons = []
                for btn in buttons[category][item]:
                    # Исключаем "Стать представителем", если есть 'proxy'
                    if btn == 'become_proxy' and 'proxy' in status:
                        continue

                    # Переименовываем "Выбрать представителя" для 'proxy'
                    if btn == 'select_proxy' and 'proxy' in status:
                        text = "Выбрать заместителя"
                    else:
                        text = LEXICON.get(btn, btn)  # Используем текст из LEXICON или callback_data

                    # Добавляем кнопку, если её callback_data уникальна
                    if btn not in unique_buttons:
                        unique_buttons.add(btn)
                        current_buttons.append(InlineKeyboardButton(text=text, callback_data=btn))

                # Добавляем текущие кнопки в клавиатуру
                keyboard.extend([[btn] for btn in current_buttons])

    return keyboard

@log_function_call
async def user_menu(tg_id: int = None, status:list[str] = None) -> InlineKeyboardMarkup | None:
    try:
        if not status:
            status = await extract_status_tg(tg_id)
        logging.info(f"Создание меню для пользователя {tg_id} со статусами: {status}")
        # if not status or 'member' not in status:
        #     if 'user' in status:
        #         keyboard = get_keyboard_for_status(['user'])
        #     elif 'candidate' in status:
        #         keyboard = get_keyboard_for_status(['candidate'])
        #     elif 'owner' in status:
        #         keyboard = get_keyboard_for_status(['user','owner'])
        #     elif 'admin' in status:
        #         keyboard = get_keyboard_for_status(['user','admin'])
        #     else:
        #         unknown_button = {'unknown': 'Я не знаю кто ты'}
        #         return create_inline_kb(1, **unknown_button)
        # else:
        #     keyboard = get_keyboard_for_status(status)
        keyboard = get_keyboard_for_status(status)

        # Добавляем кнопку "помощь"
        help_button = InlineKeyboardButton(text=LEXICON.get('help', 'Помощь'), callback_data='help')
        keyboard.append([help_button])

        kb_builder = InlineKeyboardBuilder()
        for row in keyboard:
            kb_builder.row(*row)
        return kb_builder.as_markup()
    except Exception as e:
        logging.error(f"Ошибка при создании меню для пользователя {tg_id}: {e}")
        raise



"""
ИНЛАЙН-КЛАВИАТУРЫ
"""

# Инлайн-клавиатура для регистрации
reg_button_1 = InlineKeyboardButton(
    text='ЗАРЕГИСТРИРОВАТЬСЯ',
    callback_data='reg_button_pressed'
)
reg_markup = InlineKeyboardMarkup(inline_keyboard=[[reg_button_1]])

# Клавиатура для подтверждения
ok_mod_button = InlineKeyboardButton(
    text='ВСЁ ВЕРНО',
    callback_data='ConfirmOK'
)
no_mod_button = InlineKeyboardButton(
    text='НЕВЕРНО',
    callback_data='ConfirmNotOK'
)
back_to_menu_button = InlineKeyboardButton(
    text = LEXICON.get('return_to_main_menu','Назад в главное меню'),
    callback_data='main_menu'
    )

confirm_markup = InlineKeyboardMarkup(
    inline_keyboard=[[ok_mod_button, no_mod_button],[back_to_menu_button]],
    one_time_keyboard=True
)

# Клавиатура для возврата в главное меню (для прерывания какого-то процесса)

return_to_main_menu_keyboards = {'main_menu' : LEXICON.get('return_to_main_menu','Назад в главное меню')}
return_to_main_menu_markup = create_inline_kb(1, **return_to_main_menu_keyboards)

# Клавиатура для вызова главного меню

main_menu_keyboards = {'main_menu' : LEXICON.get('main_menu','Главное меню')}
main_menu_markup = create_inline_kb(1, **return_to_main_menu_keyboards)

# Клавиатура для добавления вариантов голосования
ok_var_button = InlineKeyboardButton(
    text='Добавить еще вариант',
    callback_data='NewVariant'
)
finish_var_button = InlineKeyboardButton(
    text='Завершить добавление вариантов',
    callback_data='main_menu'
)
variant_markup = InlineKeyboardMarkup(
    inline_keyboard=[[ok_var_button, finish_var_button]],
    one_time_keyboard=True
)


"""
ОБЫЧНЫЕ КЛАВИАТУРЫ
"""

# Клавиатура для отправки контакта
contact_btn = KeyboardButton(
    text='Отправить телефон',
    request_contact=True
)
contact_markup = ReplyKeyboardMarkup(
    resize_keyboard=True,
    one_time_keyboard=True,
    keyboard=[[contact_btn]]
)

# Клавиатура для удаления предыдущей клавиатуры
remove_markup = ReplyKeyboardRemove()


"""
ДОПОЛНИТЕЛЬНЫЕ КОММЕНТАРИИ
"""

# Если нужно добавить новые клавиатуры или кнопки, можно расширить словарь `status_keyboards`
# или добавить новые функции для их создания.