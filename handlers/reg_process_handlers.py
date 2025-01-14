from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


from FSMs.FSMs import FSMRegistration,FSMRereg
from data_base.data_base import db_update
from keyboards.keyboards import reg_keyboard, contact_keyboard, remove_keyboard
from filters.filters import filter_contact
from data_base.telegram_bot_logic import (status_member, extract_user_data,
        new_status_tg, list_of_members_tg)
from config_data.config import Config, load_config

#инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)


# Инициализируем роутер уровня модуля
router = Router()




"""
Хэндлеры FSM регистраци участника
"""


#НАЖАТА КНОПКА "ЗАРЕГИСТРИРОВАТЬСЯ"
#Этот хэндлер будет срабатывать на апдейт типа CallbackQuery
# с data 'reg_button_pressed'

@router.callback_query(F.data == 'reg_button_pressed',StateFilter(default_state))
async def reg_button_press(callback: CallbackQuery,state: FSMContext):
    # Отвечаем на callback, чтобы убрать часики
    await callback.answer()
    tg_id = callback.from_user.id
    data = extract_user_data(tg_id)
    if not any(data[2:]): #если профиль пользователя пуст, кроме телеграм ID,
        print('status_member =',status_member(tg_id))
        if status_member(tg_id) == ['user']: #если пользователь не зарегистрирован в группе,
            print(1111111111111111)
            await callback.message.answer(   #приступаем к регистрации
             text='Сейчас мы последовательно заполним анкету регистрации.'
            '\nВведите ваше имя (только имя, без фамилии)',
             )
            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMRegistration.fill_name)
        else: #Если пользователь уже зареган в группе, но анкета почему-то пуста
            print(222222222222222)
                # Создаем объекты инлайн-кнопок
            yes_button = InlineKeyboardButton(
            text='Хочу',
            callback_data='yes_reg_member'
             )
            no_button = InlineKeyboardButton(
            text='Не хочу',
            callback_data='no_reg_member')
            # Добавляем кнопки в клавиатуру в один ряд
            keyboard: list[list[InlineKeyboardButton]] = [
            [yes_button, no_button]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.answer(   #приступаем к регистрации
             text='Вы уже зарегистрированы в группе'
            '\nХотите ли обновить ваши данные?',
             reply_markup = markup
             )
            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMRereg.fill_OK)
    else:
        if status_member(tg_id) == ['user']: #если пользователь не зарегистрирован в группе,
            print(333333333333333333)
                # Создаем объекты инлайн-кнопок
            yes_button = InlineKeyboardButton(
            text='Хочу',
            callback_data='yes_rereg_user'
             )
            no_button = InlineKeyboardButton(
            text='Не хочу',
            callback_data='no_rereg_user')
            # Добавляем кнопки в клавиатуру в один ряд
            keyboard: list[list[InlineKeyboardButton]] = [
            [yes_button, no_button]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.answer(   #приступаем к регистрации
             text='Вы уже зарегистрированы в системе голосований'
            '\nХотите ли обновить ваши данные?',
             reply_markup = markup
             )
            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMRereg.fill_OK)
        else: #сли пользователь зарегистрирован в группе
            print(444444444444444444444444)
                # Создаем объекты инлайн-кнопок
            yes_button = InlineKeyboardButton(
            text='Хочу',
            callback_data='yes_reg_member'
             )
            no_button = InlineKeyboardButton(
            text='Не хочу',
            callback_data='no_reg_member')
            # Добавляем кнопки в клавиатуру в один ряд
            keyboard: list[list[InlineKeyboardButton]] = [
            [yes_button, no_button]
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await callback.message.answer(   #приступаем к регистрации
             text='Вы уже зарегистрированы в группе'
            '\nХотите ли обновить ваши данные?',
             reply_markup = markup
             )
            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMRereg.fill_OK)

#Хендлер на обновление данных члена без регистрации
@router.callback_query(StateFilter(FSMRereg.fill_OK),
                   F.data =='yes_reg_member')
async def process_yes_reg_member(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    await callback.message.answer(   #приступаем к регистрации
             text='Сейчас мы последовательно заполним анкету регистрации.'
            '\nВведите ваше имя (только имя, без фамилии)',
             )
            # Устанавливаем состояние ожидания подтверждения
    await state.set_state(FSMRegistration.fill_name)
    #Устанавливаем состояние ожидания обновления данных без последующей регистрации
    await state.set_state(FSMRereg.fill_no_reg)



#Хэнлер на отказ от обновления члена (и без регистрации - то есть, выход)
@router.callback_query(StateFilter(FSMRereg.fill_OK),
                   F.data =='no_reg_member')
async def process_no_reg_member(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    await callback.message.answer(
        text='Вы вышли из анкеты регистрации\n\n'
             'Чтобы снова перейти к заполнению анкеты - '
             'снова нажмите кнопку "регистрация"'
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()

#Хэндлер на обновление данных пользователя с последующей регистрацией
@router.callback_query(StateFilter(FSMRereg.fill_OK),
                   F.data =='yes_rereg_user')
async def process_yes_rereg_user(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    await callback.message.answer(   #приступаем к регистрации
             text='Сейчас мы последовательно заполним анкету регистрации.'
            '\nВведите ваше имя (только имя, без фамилии)',
             )
            # Устанавливаем состояние ожидания подтверждения
    await state.set_state(FSMRegistration.fill_name)



#Хэндлер на необновление данных но на регистрации пользоателя в группе. Делаем сачок сразу к регистрации
@router.callback_query(StateFilter(FSMRereg.fill_OK),
                   F.data =='no_rereg_user')
async def process_no_rereg(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()

    #Создаем инлайн-кнопки

    #делаем клавиатуру
    buttons: list[InlineKeyboardButton] = []
    for name, famil,tg_id in answ:
        buttons.append([InlineKeyboardButton(
            text=f'{name} {famil}',
            callback_data = str(tg_id)
        )])
    buttons.append([InlineKeyboardButton(
        text='Никого из модераторов не знаю',
        callback_data = 'stranger'
        )])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    #Отправляем пользователю клавиатуру из
    await callback.message.answer(text = (f"Спасибо!\n"
                    f'Выберите модератора, которого знаете,\n'
                    f'чтобы он смог подтвердить вашу личность\n'
                    f'Если никого не знаете,\n'
                    f'Нажмите кнопку "Никого не знаю"'),
                         reply_markup=markup #клавиатура подтвержджения
                         )
    # Устанавливаем состояние ожидания выбора модератора
    await state.set_state(FSMRegistration.fill_registrator)



# Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# кроме состояния по умолчанию, и отключать машину состояний
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из анкеты регистрации\n\n'
             'Чтобы снова перейти к заполнению анкеты - '
             'снова нажмите кнопку "регистрация"'
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()

#Этот хендлер будет срабатывать, если

#

#

#


# Этот хэндлер будет срабатывать, если введено корректное имя
# и переводить в состояние ожидания ввода фамилии
@router.message(StateFilter(FSMRegistration.fill_name), F.text.isalpha())
async def process_name_sent(message: Message, state: FSMContext):
    # Cохраняем введенное имя в хранилище по ключу "name"
    await state.update_data(first_name=message.text)
    await message.answer(text='Ваша фамилия')
    # Устанавливаем состояние ожидания ввода фамилии
    await state.set_state(FSMRegistration.fill_last_name)

# Этот хэндлер будет срабатывать, если во время ввода имени
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_name))
async def warning_not_name(message: Message):
    await message.answer(
        text='То, что вы отправили не похоже на имя\n\n'
             'Пожалуйста, введите ваше имя\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать, если введена корректная фамилия
# и переводить в состояние ожидания ввода возраста
@router.message(StateFilter(FSMRegistration.fill_last_name), F.text.isalpha())
async def process_last_name_sent(message: Message, state: FSMContext):
    # Cохраняем введенное имя в хранилище по ключу "name"
    await state.update_data(last_name=message.text)
    await message.answer(text='Ваш год рождения')
    # Устанавливаем состояние ожидания ввода возраста
    await state.set_state(FSMRegistration.fill_age)


# Этот хэндлер будет срабатывать, если во время ввода фамилии
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_last_name))
async def warning_last_name(message: Message):
    await message.answer(
        text='То, что вы отправили не похоже на фамилию\n\n'
             'Пожалуйста, введите вашу фамилию\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать, если введен корректный возраст
# и переводить в состояние выбора пола
@router.message(StateFilter(FSMRegistration.fill_age),
            lambda x: x.text.isdigit() and 1910 <= int(x.text) <= 2020)
async def process_age_sent(message: Message, state: FSMContext):
    # Cохраняем возраст в хранилище по ключу "age"
    await state.update_data(birth_year=message.text)
    # Создаем объекты инлайн-кнопок
    male_button = InlineKeyboardButton(
        text='Мужской ♂',
        callback_data='male'
    )
    female_button = InlineKeyboardButton(
        text='Женский ♀',
        callback_data='female'
    )

    # Добавляем кнопки в клавиатуру (две в одном ряду)
    keyboard: list[list[InlineKeyboardButton]] = [
        [male_button, female_button]
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(one_time_keyboard=True, inline_keyboard=keyboard)
    # Отправляем пользователю сообщение с клавиатурой
    await message.answer(
        text='Спасибо!\n\nУкажите ваш пол',
        reply_markup=markup
    )
    # Устанавливаем состояние ожидания выбора пола
    await state.set_state(FSMRegistration.fill_gender)


# Этот хэндлер будет срабатывать, если во время ввода возраста
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_age))
async def warning_not_age(message: Message):
    await message.answer(
        text='Возраст должен быть целым числом от 4 до 120\n\n'
             'Попробуйте еще раз\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на нажатие кнопки при
# выборе пола и переводить в состояние отправки контакта
@router.callback_query(StateFilter(FSMRegistration.fill_gender),
                   F.data.in_(['male', 'female', 'undefined_gender']))
async def process_gender_press(callback: CallbackQuery, state: FSMContext):
    # Cохраняем пол (callback.data нажатой кнопки) в хранилище,
    # по ключу "gender"
    await state.update_data(gender=callback.data)
    # Удаляем сообщение с кнопками, потому что следующий этап - отправка контакта
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()

    await callback.message.answer(
        text='Отправьте ваш контакт\nНажмите для этого кнопку в самом низу экрана',
        reply_markup = contact_keyboard
    )

    # Устанавливаем состояние ожидания отправки контакта
    await state.set_state(FSMRegistration.fill_contact)


# Этот хэндлер будет срабатывать, если во время выбора пола
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_gender))
async def warning_not_gender(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             'при выборе пола\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


#Этот хэндлер срабатывает на кнопку "Прислать контакт".
#Данные из контакта записываются в базу данных в строку соотвествующего пользователя
@router.message(F.contact,StateFilter(FSMRegistration.fill_contact))
async def process_get_contact(message, state: FSMContext):
    contact = message.contact
    tg_true = filter_contact(message) #проверяем, действительно ли юзер прислал свой контакт - или чужой

    #сохраняем данные контакта в хранилище:
    await state.update_data(tg_phone_number = message.contact.phone_number,
               tg_first_name = message.contact.first_name ,
               tg_last_name = message.contact.last_name,
               tg_true = tg_true) #флаг 0 в БД будет означать что перед нами хакер

    # Создаем объекты инлайн-кнопок
    yes_button = InlineKeyboardButton(
        text='Да, всё верно',
        callback_data='yes_contact'
    )
    no_button = InlineKeyboardButton(
        text='Не верно',
        callback_data='no_contact')
    # Добавляем кнопки в клавиатуру в один ряд
    keyboard: list[list[InlineKeyboardButton]] = [
        [yes_button, no_button]
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    user_dict = await state.get_data()
    await message.delete()
    await message.answer(text = f'''Спасибо!\n
                         Ваш номер был получен.\n
                         Проверьте ваши данные:\n
                    Имя: {user_dict["first_name"]}\n'
                    Фамилия: {user_dict["last_name"]}\n'
                    Возраст: {user_dict["age"]}\n'
                    Пол: {user_dict["gender"]}\n'
                    Номер телефона: {user_dict["tg_phone_number"]}''',
                reply_markup=remove_keyboard
        )
    await message.answer(text = f'Всё правильно?',
                         reply_markup=markup #клавиатура подтвержджения
                         )
    print(contact)
    # Устанавливаем состояние ожидания подтверждения личных данных
    await state.set_state(FSMRegistration.fill_confirm1)

#Этот хэндлер срабатывает на всё, что пришлют вместо контакта в состоянии ожидания контакта
@router.message(StateFilter(FSMRegistration.fill_contact))
async def warning_get_contact(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопкй '
             '"Отправить контакт"\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на подтверждение личных данных

@router.callback_query(StateFilter(FSMRegistration.fill_confirm1),
                   F.data =='yes_contact')
async def process_yes_contact(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    # Создаем объекты инлайн-кнопок c городами
    Novosibirsk_button = InlineKeyboardButton(
        text='Новосибирск',
        callback_data='Новосибирск')

    Berdsk_button = InlineKeyboardButton(
        text='Бердск',
        callback_data='Бердск')

    Kolcovo_button = InlineKeyboardButton(
        text='Кольцово',
        callback_data='Кольцово')

    Krasnoobsk_button = InlineKeyboardButton(
        text='Краснообск',
        callback_data='Краснообск')

    Iskitim_button = InlineKeyboardButton(
        text='Искитим',
        callback_data='Искитим')

    Ob_button = InlineKeyboardButton(
        text='Обь',
        callback_data='Обь')

    Other_button = InlineKeyboardButton(
        text='Другое',
        callback_data='other')

    # Добавляем кнопки в клавиатуру в три ряда
    keyboard: list[list[InlineKeyboardButton]] = [
        [Novosibirsk_button, Berdsk_button],
        [Kolcovo_button, Krasnoobsk_button],
        [Iskitim_button, Ob_button],
        [Other_button]
    ]

    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.answer(
        text="""Спасибо! Осталось ответить на несколько вопросов.\n
        о том, где вы живете\n
        (мы не будем просить точный адрес).\n
        Укажите, из какого вы города.""",
        reply_markup=markup
        )
    # Устанавливаем состояние ожидания выбора города
    await state.set_state(FSMRegistration.fill_city)


#Этот хэндлер будет срабатывать на нажатие кнопки "Не верно" при подтверждении
#личных данных. Стираем кнопки и выходим из машины состояний.
@router.callback_query(StateFilter(FSMRegistration.fill_confirm1),
                   F.data =='no_contact')
async def process_no_contact(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Спасибо! Ваши данные не добавлены\nПопробуйте еще раз.\n'
             'Вы вышли из машины состояний'
    )


# Этот хэндлер будет срабатывать, если во время подтверждения
# личных данных будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_confirm1))
async def warning_not_contact(message: Message):
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на нажатие кнопки города
# и переводить в состояние ожидания ввода улицы
@router.callback_query(StateFilter(FSMRegistration.fill_city),
                   F.data.in_(['Новосибирск', 'Бердск', 'Кольцово',
                    'Краснообск', 'Искитим', 'Обь']))
async def process_сity_press(callback: CallbackQuery, state: FSMContext):
    # Cохраняем город (callback.data нажатой кнопки) в хранилище,
    # по ключу "city"
    await state.update_data(city=callback.data)
    # Удаляем сообщение с кнопками, потому что следующий этап - ввод улицы
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()
    await callback.message.answer(
        text='Спасибо! А теперь введите название вашей улицы.',
        reply_markup=remove_keyboard
    )
    # Устанавливаем состояние ожидания ввода названия улицы
    await state.set_state(FSMRegistration.fill_street)

#Этот хэндлер срабатывает нанажатие кнопки "Другое" при выборе города
#И переводит в состояние ожидания ввода названия населенного пункта
@router.callback_query(StateFilter(FSMRegistration.fill_city),
                   F.data == 'other')
async def process_new_city_press(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками, потому что следующий этап - ввод города
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()
    await callback.message.answer(
        text='Введите название вашего города или населенного пункта.',
        reply_markup=remove_keyboard
    )
    # Устанавливаем состояние ожидания ввода названия города
    await state.set_state(FSMRegistration.fill_new_city)


# Этот хэндлер будет срабатывать, если во время выбора города
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_city))
async def warning_not_city(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками при выборе города\n\n'
             'Если вы хотите прервать заполнение анкеты - отправьте '
             'команду /cancel'
    )

# Этот хэндлер будет срабатывать, если введено корректное название города
# и переводить в состояние ожидания ввода улицы
@router.message(StateFilter(FSMRegistration.fill_new_city), F.text.isalpha())
async def process_city_sent(message: Message, state: FSMContext):
    # Cохраняем введенное название в хранилище по ключу "city"
    await state.update_data(city=message.text)
    await message.answer(text='Спасибо!\n\nА теперь введите название вашей улицы')
    # Устанавливаем состояние ожидания ввода названия улицы
    await state.set_state(FSMRegistration.fill_street)


# Этот хэндлер будет срабатывать, если во время ввода названия города
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_new_city))
async def warning_not_city(message: Message):
    await message.answer(
        text='То, что вы отправили не похоже на название населенного пункта\n\n'
             'Пожалуйста, введите название только буквами\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать, если введено корректное название улицы
# и переводить в состояние ожидания ввода улицы
@router.message(StateFilter(FSMRegistration.fill_street))
async def process_street_sent(message: Message, state: FSMContext):
    # Cохраняем введенное название в хранилище по ключу "street"
    await state.update_data(street=message.text)
    # Создаем объекты инлайн-кнопок
    mkd_button = InlineKeyboardButton(
        text='Многоквартирном',
        callback_data='mkd'
    )
    ijs_button = InlineKeyboardButton(
        text='Частном',
        callback_data='ijs'
    )

    # Добавляем кнопки в клавиатуру
    keyboard: list[list[InlineKeyboardButton]] = [
        [mkd_button, ijs_button],
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text="""Спасибо!\n\nУкажите - вы проживаете в многоквартирном доме?\n
                         Или в частном?""",
                         reply_markup=markup
                         )
    # Устанавливаем состояние ожидания выбора типа дома
    await state.set_state(FSMRegistration.fill_yes_mkd)

# Этот хэндлер будет срабатывать на нажатие кнопки МНОГОКВАРТИРНОМ
# при выборе типа дома и переводить в состояние ввода номер
@router.callback_query(StateFilter(FSMRegistration.fill_yes_mkd),
                   F.data == 'mkd')
async def process_mkd_press(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками,
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()
    await callback.message.answer(
        text='Спасибо! А теперь введите номер дома'
    )
    # Устанавливаем состояние ожидания ввода номера дома
    await state.set_state(FSMRegistration.fill_number_mkd)

# Этот хэндлер будет срабатывать на нажатие кнопки ЧАСТНОМ
# при выборе типа дома и переводить в состояние ожидания выбора диапазона номеров
@router.callback_query(StateFilter(FSMRegistration.fill_yes_mkd),
                   F.data == 'ijs')
async def process_ijs_press(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками,
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()

    #Делаем клаиватуру из диапазанов номеров
    d0120_button = InlineKeyboardButton(
        text='1-20',
        callback_data='1-20'
    )
    d2140_button = InlineKeyboardButton(
        text='21-40',
        callback_data='21-40'
    )
    d4160_button = InlineKeyboardButton(
        text='41-60',
        callback_data='41-60'
    )
    d6180_button = InlineKeyboardButton(
        text='61-80',
        callback_data='61-80'
    )
    d81100_button = InlineKeyboardButton(
        text='81-100',
        callback_data='81-100'
    )
    d101120_button = InlineKeyboardButton(
        text='101-120',
        callback_data='101-120'
    )
    d121140_button = InlineKeyboardButton(
        text='121-140',
        callback_data='121-140'
    )
    d141160_button = InlineKeyboardButton(
        text='141-160',
        callback_data='141-160'
    )
    d161180_button = InlineKeyboardButton(
        text='161-180',
        callback_data='161-180'
    )
    d181200_button = InlineKeyboardButton(
        text='181-200',
        callback_data='181-200'
    )
    d201220_button = InlineKeyboardButton(
        text='201-220',
        callback_data='201-220'
    )
    d221240_button = InlineKeyboardButton(
        text='221-240',
        callback_data='221-240'
    )
    d241260_button = InlineKeyboardButton(
        text='241-260',
        callback_data='241-260'
    )
    d261280_button = InlineKeyboardButton(
        text='261-80',
        callback_data='261-280'
    )
    d281300_button = InlineKeyboardButton(
        text='281-300',
        callback_data='281-300'
    )
    d301320_button = InlineKeyboardButton(
        text='301-320',
        callback_data='301-320'
    )
    d321340_button = InlineKeyboardButton(
        text='321-340',
        callback_data='321-340'
    )
    d341360_button = InlineKeyboardButton(
        text='341-360',
        callback_data='341-360'
    )
    d361380_button = InlineKeyboardButton(
        text='361-380',
        callback_data='361-380'
    )
    d381400_button = InlineKeyboardButton(
        text='381-400',
        callback_data='381-400'
    )
    d401420_button = InlineKeyboardButton(
        text='401-420',
        callback_data='401-420'
    )
    d421440_button = InlineKeyboardButton(
        text='421-440',
        callback_data='421-440'
    )
    d441460_button = InlineKeyboardButton(
        text='441-460',
        callback_data='441-460'
    )
    d461480_button = InlineKeyboardButton(
        text='461-480',
        callback_data='461-480'
    )
    d481500_button = InlineKeyboardButton(
        text='481-500',
        callback_data='481-500'
    )
    d501520_button = InlineKeyboardButton(
        text='501-520',
        callback_data='501-520'
    )
    d521540_button = InlineKeyboardButton(
        text='521-540',
        callback_data='521-540'
    )
    d541560_button = InlineKeyboardButton(
        text='541-560',
        callback_data='541-560'
    )
    d561580_button = InlineKeyboardButton(
        text='561-580',
        callback_data='561-580'
    )
    d581600_button = InlineKeyboardButton(
        text='581-600',
        callback_data='581-600'
    )
    d601620_button = InlineKeyboardButton(
        text='601-620',
        callback_data='601-620'
    )
    d621640_button = InlineKeyboardButton(
        text='621-640',
        callback_data='621-640'
    )
    d_more_button = InlineKeyboardButton(
        text='Больше, чем 640',
        callback_data='Больше, чем 640'
    )
    # Добавляем кнопки в клавиатуру
    keyboard: list[list[InlineKeyboardButton]] = [
        [d0120_button, d2140_button, d4160_button, d6180_button],
        [d81100_button, d101120_button, d121140_button, d141160_button],
        [d161180_button, d181200_button, d201220_button, d221240_button],
        [d241260_button, d261280_button, d281300_button, d301320_button],
        [d321340_button, d341360_button, d361380_button, d381400_button],
        [d401420_button, d421440_button, d441460_button, d461480_button],
        [d481500_button, d501520_button, d521540_button, d541560_button],
        [d561580_button, d581600_button, d601620_button, d621640_button],
        [d_more_button]
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)


    await callback.message.answer(
        text='Спасибо! А теперь укажите  интервал, \nв котором находится'
        'номер вашего дома',
        reply_markup=markup
    )
    # Устанавливаем состояние ожидания выбора интервала номеров
    await state.set_state(FSMRegistration.fill_range_num)

# Этот хэндлер будет срабатывать, если во время выбора типа дома
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_yes_mkd))
async def warning_not_mkd(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             'при выборе пола\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )

#Этот хэндлер будет срабатывать на ввод номера многоквартирного дома
#и переводить  в состояние ожидания подтверждения адреса
@router.message(StateFilter(FSMRegistration.fill_number_mkd))
async def process_last_name_sent(message: Message, state: FSMContext):
    # Cохраняем введенное имя в хранилище по ключу "house"
    await state.update_data(house = message.text)
    # Создаем объекты инлайн-кнопок
    yes_button = InlineKeyboardButton(
        text='Да, всё верно',
        callback_data='yes_address'
    )
    no_button = InlineKeyboardButton(
        text='Не верно',
        callback_data='no_address')
    # Добавляем кнопки в клавиатуру в один ряд
    keyboard: list[list[InlineKeyboardButton]] = [
        [yes_button, no_button]
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    #Выводим данные адреса для подтверждения
    user_dict = await state.get_data()
    await message.answer(text = (f'Спасибо!\n'
                    'Проверьте ваш адрес:\n'
                    f'Город: {user_dict["city"]}\n'
                    f'Улица: {user_dict["street"]}\n'
                    f'Дом: {user_dict["house"]}\n'
                    f"Всё правильно?"),
                         reply_markup=markup #клавиатура подтвержджения
                         )
    print(user_dict)
    # Устанавливаем состояние ожидания подтверждения адреса
    await state.set_state(FSMRegistration.fill_confirm2)

#Этот хэндлер будет срабатывать на нажатие кнопки диапазона домов
@router.callback_query(StateFilter(FSMRegistration.fill_range_num))#,
                   #re.match(r'[0-9]+[-][0-9]+', str(F.data)) is not None or
                   #F.data == 'Больше, чем 640')
async def process_range_house_press(callback: CallbackQuery, state: FSMContext):
    # Cохраняем диапазон (callback.data нажатой кнопки) в хранилище,
    print(callback.data)
    # по ключу "house"
    await state.update_data(house=callback.data)
    # Удаляем сообщение с кнопками
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()
    # Создаем объекты инлайн-кнопок
    yes_button = InlineKeyboardButton(
        text='Да, всё верно',
        callback_data='yes_address'
    )
    no_button = InlineKeyboardButton(
        text='Не верно',
        callback_data='no_address')
    # Добавляем кнопки в клавиатуру в один ряд
    keyboard: list[list[InlineKeyboardButton]] = [
        [yes_button, no_button]
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    #Выводим данные адреса для подтверждения
    user_dict = await state.get_data()
    await callback.message.answer(text = (f"Спасибо!\n"
                    "Проверьте ваш адрес:\n"
                    f'Город: {user_dict["city"]}\n'
                    f'Улица: {user_dict["street"]}\n'
                    f'Дом: {user_dict["house"]}\n'
                    f"Всё правильно?"),
                         reply_markup=markup #клавиатура подтвержджения
                         )
    print(user_dict)
    # Устанавливаем состояние ожидания подтверждения адреса
    await state.set_state(FSMRegistration.fill_confirm2)

# Этот хэндлер будет срабатывать, если во время выбора диапазона номеров домов
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_range_num))
async def warning_not_range(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             'при выборе диапазона номеров.\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )

#Этот хэндлер будет срабатывать на подтверждение адреса, если дальнейшая регистрация не требуется (и на выход)
@router.callback_query(StateFilter(FSMRegistration.fill_confirm2, FSMRereg.fill_no_reg),
                   F.data =='yes_address')
async def process_yes_adress_no_reg(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    tg_id = callback.from_user.id
    #Заносим данные регистрации в строку соответствующего пользователя в  базе данных
    user_dict = await state.get_data()
    db_update('Users','tg_id',tg_id, **user_dict) #записываем данные в БД
    new_status_tg(0, tg_id, 'candidate')  #меняем статус пользователя на 'candidate'
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.answer(#возможно answer
        text='Спасибо! Ваши данные сохранены',
        )



# Этот хэндлер будет срабатывать на подтверждение адреса

@router.callback_query(StateFilter(FSMRegistration.fill_confirm2),
                   F.data =='yes_address')
async def process_yes_adress(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()

    #Создаем инлайн-кнопки
    list_of_registrators = list_of_members_tg('registrator')

    #делаем клавиатуру
    buttons: list[InlineKeyboardButton] = []
    for item in list_of_registrators:
        buttons.append([InlineKeyboardButton(
            text=f'{item[0]} {item[1]}',
            callback_data = str(item[2])
        )])
    buttons.append([InlineKeyboardButton(
        text='Никого из регистраторов не знаю',
        callback_data = 'stranger'
        )])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    #Отправляем пользователю клавиатуру из
    await callback.message.answer(text = (f"Спасибо!\n"
                    f'Выберите регистратора, которого знаете,\n'
                    f'чтобы он смог подтвердить вашу личность\n'
                    f'Если никого не знаете,\n'
                    f'Нажмите кнопку "Никого не знаю"'),
                         reply_markup=markup #клавиатура подтвержджения
                         )
    # Устанавливаем состояние ожидания выбора модератора
    await state.set_state(FSMRegistration.fill_registrator)

#Этот хэндлер будет срабатывать на отказ подтвердить адрес
@router.callback_query(StateFilter(FSMRegistration.fill_confirm2),
                   F.data =='no_address')
async def process_no_address(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Спасибо! Ваши данные не добавлены\nПопробуйте еще раз.\n'
             'Вы вышли из машины состояний'
    )

# Этот хэндлер будет срабатывать, если вместо подтверждения адреса
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_confirm2))
async def warning_not_address(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             '\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на выбор регистратора
@router.callback_query(StateFilter(FSMRegistration.fill_registrator),
                   F.data.isdigit() or F.data == 'stranger')
async def process_registrator_press(callback: CallbackQuery, state: FSMContext):
    # Удаляем сообщение с кнопками подтверждения
    await callback.message.delete()
    # Cохраняем знакомого модератора (callback.data нажатой кнопки) в хранилище,
    # по ключу "familiar"
    await state.update_data(familiar=callback.data)
    tg_id = callback.from_user.id
    #Заносим данные регистрации в строку соответствующего пользователя в  базе данных
    user_dict = await state.get_data()
    db_update('Users','tg_id',tg_id, **user_dict) #записываем данные в БД
    new_status_tg(None, tg_id, 'candidate')  #меняем статус пользователя на 'candidate'
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.answer(#возможно answer
        text='Спасибо! Ваши данные сохранены.\nАдминистрация их проверит и'
        'даст вам оотвествующие права\n'
             'Вы вышли из машины состояний'
    )
    #Отправляем сообщение модератору, что пользователь просит его зарегистрировать
    if callback.data.isdigit():  #если в колл-бэке tg-ID модератора
        # Создаем объекты инлайн-кнопок
        confirm_button = InlineKeyboardButton(
            text='Подтверждаю',
            callback_data=f"yes_confirm:{tg_id}"
          )
        not_confirm_button = InlineKeyboardButton(
            text='Не подтверждаю',
            callback_data=f"no_confirm:{tg_id}"
            )
        # Добавляем кнопки в клавиатуру в один ряд
        keyboard: list[list[InlineKeyboardButton]] = [
            [confirm_button, not_confirm_button]
        ]
        # Создаем объект инлайн-клавиатуры
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await bot.send_message(int(callback.data), #посылаем письмо модератору
            text = (f"Пользователь с данными:\n"
                    f'Имя: {user_dict["first_name"]}\n'
                    f'Фамилия: {user_dict["last_name"]}\n'
                    f'Возраст: {user_dict["age"]}\n'
                    f'Пол: {user_dict["gender"]}\n'
                    f'Город: {user_dict["city"]}\n'
                    f'Улица: {user_dict["gender"]}\n'
                    f'Дом: {user_dict["house"]}\n'
                    f'Истинность контакта: {user_dict["tg_true"]}\n'
                    f'Номер телефона: {user_dict["tg_phone_number"]}\n'
                    f"Просит вас подтвердить его право\n"
                    f"стать членом клуба.\n"
                    f"Подтверждаете?"),
                         reply_markup=markup #клавиатура подтвержджения
                         )

# Этот хэндлер будет срабатывать, если во время выбора модератора
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_registrator))
async def warning_not_registrator(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             'при выборе модератора.\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )
