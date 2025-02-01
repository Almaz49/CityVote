from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder,InlineKeyboardBuilder
from LEXICON.LEXICON import *
from data_base.telegram_bot_logic import extract_status_tg
"""
КНОПКИ И КЛАВИАТУРЫ
"""

"""
Функция создания инлайн клавиатуры из списка или словаря
"""

# Функция для формирования инлайн-клавиатуры на лету
def create_inline_kb(width: int,
                     *args: str,
                     **kwargs: str) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из аргументов args и kwargs
    if args:
        for button in args:
            buttons.append(InlineKeyboardButton(
                text=LEXICON[button] if button in LEXICON else button,
                callback_data=button))
    if kwargs:
        for button, text in kwargs.items():
            buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=button))

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()

# Функция создания инлайн-кнопки по callback_data. Необязательный аргумент text
# если есть text, то он становится надписью на кнопке. Если нет - смотрит в LEXICON
# Если и там нет - надписью становится callback_data
def button(button: str, text: str = None) -> InlineKeyboardButton:
    if text:
        btn = InlineKeyboardButton(text=text, callback_data=button)
    else:
        btn = InlineKeyboardButton(
                text=LEXICON[button] if button in LEXICON else button,
                callback_data=button)
    return(btn)

# Клавиатуры-меню в зависимости от статуса:
user_keyboard = [
    [button('list_of_votes')],
    [button('registration')]
    ]
candidate_keyboard = [
    [button('list_of_votes')],
    [button('select_proxy')]
    ]
member_keyboard = [
    [button('list_of_votes')],
    [button('archive_of_votes')],
    [button('select_proxy')],
    [button('become_proxy')]
    ]
registrator_keyboard = [
    [button('new_member')]
    ]
proxy_keyboard = [
    [button('resign_from_proxy')]
    ]
delegate_keyboard = [
    [button('new_vote')],
    [button('new_variant')]
    ]
admin_keyboard = [
    [button('new_status')]
    ]

# Словарь соотвествия стстус:клавиатура.
# Нужен для автоматического создания меню для пользователя с несколькими статусами
status_keyboards = {
    'user' : user_keyboard,
    'candidate' : candidate_keyboard,
    'member' : member_keyboard,
    'registrator' : registrator_keyboard,
    'proxy' : proxy_keyboard,
    'delegate' :delegate_keyboard,
    'admin' : admin_keyboard,
    'owner' : admin_keyboard
}
# Функция создания инлайн-клавиатуры (меню) участника в зависимости от его статусов

# async def user_menu(tg_id):
#     status = extract_status_tg(tg_id)
#     # print('status:', status)
#     if 'member' not in status:
#         if 'user' in status:
#             keyboard = user_keyboard
#         elif 'candidate' in status:
#             keyboard = candidate_keyboard
#         else:
#             keyboard = [['Я не знаю кто ты']]
#     else:
#         keyboard = []
#         for item in status:
#             if item in status_keyboards:
#                 keyboard += status_keyboards[item]
#     # print('keyboard', keyboard)
#     return(InlineKeyboardMarkup(inline_keyboard=keyboard))

async def user_menu(tg_id):
    status = await extract_status_tg(tg_id)
    if 'member' not in status:
        if 'user' in status:
            keyboard = user_keyboard
        elif 'candidate' in status:
            keyboard = candidate_keyboard
        else:
            keyboard = [['Я не знаю кто ты']]
    else:
        keyboard = []
        for item in status:
            if item in status_keyboards:
                keyboard += status_keyboards[item]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

"""
#Инлайн кнопка и клавиатура регистарции для новичков
"""
reg_button_1 = InlineKeyboardButton(
    text='ЗАРЕГИСТРИРОВАТЬСЯ',
    callback_data='reg_button_pressed'
)
#клавиатура
reg_markup = InlineKeyboardMarkup(
    inline_keyboard=[[reg_button_1]]
)

"""
#Кнопка отправки контакта
"""
contact_btn = KeyboardButton(
    text='Отправить телефон',
    request_contact=True)
#клавиатура:
contact_markup = ReplyKeyboardMarkup(resize_keyboard=True,
                                       one_time_keyboard=True,
                                       keyboard=[[contact_btn]])

"""
Клавиатура создания варианта голосования
"""
# Создаем объекты инлайн-кнопок
ok_mod_button = InlineKeyboardButton(
    text='Добавить еще вариант',
     callback_data='NewVariant'
    )
no_mod_button = InlineKeyboardButton(
        text='Завершить добавление вариантов',
        callback_data='Finish_Variant'
    )

# Добавляем кнопки в клавиатуру
variant_keyboard = [
        [ok_mod_button, no_mod_button],
    ]
    # Создаем объект инлайн-клавиатуры
variant_markup = InlineKeyboardMarkup(one_time_keyboard=True, inline_keyboard=variant_keyboard)
    # Отправляем пользователю сообщение с клавиатурой

"""
#Клаиватура для стирания предыдущей
"""
remove_markup = ReplyKeyboardRemove()

"""
Клавиатура подтверждения
"""

    # Создаем объекты инлайн-кнопок
ok_mod_button = InlineKeyboardButton(
        text='ВСЁ ВЕРНО',
        callback_data='ConfirmOK'
    )
no_mod_button = InlineKeyboardButton(
        text='НЕВЕРНО',
        callback_data='ConfirmNotOK'
    )

    # Добавляем кнопки в клавиатуру
confirm_keyboard: list[list[InlineKeyboardButton]] = [
        [ok_mod_button, no_mod_button],
    ]
    # Создаем объект инлайн-клавиатуры
confirm_markup = InlineKeyboardMarkup(one_time_keyboard=True,
                                      inline_keyboard=confirm_keyboard)