from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder,InlineKeyboardBuilder
from LEXICON.LEXICON import *
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


"""
#Инлайн кнопка и клавиатура регистарции для новичков
"""
reg_button_1 = InlineKeyboardButton(
    text='ЗАРЕГИСТРИРОВАТЬСЯ',
    callback_data='reg_button_pressed'
)
#клавиатура
reg_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[reg_button_1]]
)

"""
#Кнопка отправки контакта
"""
contact_btn = KeyboardButton(
    text='Отправить телефон',
    request_contact=True)
#клавиатура:
contact_keyboard = ReplyKeyboardMarkup(resize_keyboard=True,
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
remove_keyboard = ReplyKeyboardRemove()

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
confirm_markup = InlineKeyboardMarkup(one_time_keyboard=True, inline_keyboard=confirm_keyboard)