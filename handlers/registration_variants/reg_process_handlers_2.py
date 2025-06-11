# Модуль reg_process_handlers
# Содержит хэндлеры процесса регистрации

import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from FSMs.FSMs import FSMRegistration, FSMRereg, FSM_short_registration
from data_base.telegram_bot_logic import status_member, new_status_tg, list_of_members_tg, update_address, get_profile
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, return_to_main_menu_markup
from filters.filters import ContactFilter
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from LEXICON.LEXICON import LEXICON
from services.services import notify_registrator, notify_registrator_short, notify_super_registrator_short

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()



"""
Хэндлеры FSM регистраци участника с максимально полной информацией
"""


#НАЖАТА КНОПКА "ЗАРЕГИСТРИРОВАТЬСЯ"
# Этот хэндлер будет срабатывать на апдейт типа CallbackQuery с data 'reg_button_pressed'
@router.callback_query(F.data == 'reg_button_pressed', StateFilter(default_state))
@log_handler_call
async def reg_button_press(callback: CallbackQuery, state: FSMContext, data:dict):
    # Отвечаем на callback, чтобы убрать часики
    await callback.answer()
    tg_id = callback.from_user.id
    try:
        profile = await get_profile(data['member_id'])
        logger.info(f"Данные пользователя с tg_id={tg_id}: {profile}")

        if not any(value is not None for key, value in profile.items() if (key not in ['tg_id','user_id','member_id']):  # если профиль пользователя пуст, кроме ID
            member_status = await status_member(tg_id)
            logger.info(f"Статус пользователя с tg_id={tg_id}: {member_status}"
                         f'Статус в пользовательском словаре: {data['user_status']}')

            if member_status == ['user']:  # если пользователь не зарегистрирован в группе
                logger.info(f"Пользователь с tg_id={tg_id} начинает регистрацию.")
                await callback.message.answer(
                    text='Сейчас мы последовательно заполним анкету регистрации.\nВведите ваше имя (только имя, без фамилии)',
                )
                # Устанавливаем состояние ожидания ввода имени
                await state.set_state(FSMRegistration.fill_name)
            else:  # Если пользователь уже зарегистрирован в группе, но анкета почему-то пуста
                logger.info(f"Пользователь с tg_id={tg_id} хочет обновить данные.")
                # Создаем объекты инлайн-кнопок
                yes_button = InlineKeyboardButton(
                    text='Хочу',
                    callback_data='yes_reg_member'
                )
                no_button = InlineKeyboardButton(
                    text='Не хочу',
                    callback_data='no_reg_member'
                )
                # Добавляем кнопки в клавиатуру в один ряд
                keyboard: list[list[InlineKeyboardButton]] = [
                    [yes_button, no_button]
                ]
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                await callback.message.answer(
                    text='Вы уже зарегистрированы в группе.\nХотите ли обновить ваши данные?',
                    reply_markup=markup
                )
                # Устанавливаем состояние ожидания подтверждения
                await state.set_state(FSMRereg.fill_OK)
        else:
            member_status = await status_member(tg_id)
            logger.info(f"Статус пользователя с tg_id={tg_id}: {member_status}")

            if member_status == ['user']:  # если пользователь не зарегистрирован в группе
                logger.info(f"Пользователь с tg_id={tg_id} хочет обновить данные.")
                # Создаем объекты инлайн-кнопок
                yes_button = InlineKeyboardButton(
                    text='Хочу',
                    callback_data='yes_rereg_user'
                )
                no_button = InlineKeyboardButton(
                    text='Не хочу',
                    callback_data='no_rereg_user'
                )
                # Добавляем кнопки в клавиатуру в один ряд
                keyboard: list[list[InlineKeyboardButton]] = [
                    [yes_button, no_button]
                ]
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                await callback.message.answer(
                    text='Вы уже зарегистрированы в системе голосований.\nХотите ли обновить ваши данные?',
                    reply_markup=markup
                )
                # Устанавливаем состояние ожидания подтверждения
                await state.set_state(FSMRereg.fill_OK)
            else:  # если пользователь зарегистрирован в группе
                logger.info(f"Пользователь с tg_id={tg_id} уже зарегистрирован в группе.")
                # Создаем объекты инлайн-кнопок
                yes_button = InlineKeyboardButton(
                    text='Хочу',
                    callback_data='yes_reg_member'
                )
                no_button = InlineKeyboardButton(
                    text='Не хочу',
                    callback_data='no_reg_member'
                )
                # Добавляем кнопки в клавиатуру в один ряд
                keyboard: list[list[InlineKeyboardButton]] = [
                    [yes_button, no_button]
                ]
                markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
                await callback.message.answer(
                    text='Вы уже зарегистрированы в группе.\nХотите ли обновить ваши данные?',
                    reply_markup=markup
                )
                # Устанавливаем состояние ожидания подтверждения
                await state.set_state(FSMRereg.fill_OK)
    except Exception as e:
        logger.error(f"Ошибка при обработке нажатия кнопки регистрации: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')



# Хендлер на обновление данных члена без регистрации
@router.callback_query(StateFilter(FSMRereg.fill_OK), F.data == 'yes_reg_member')
@log_handler_call
async def process_yes_reg_member(callback: CallbackQuery, state: FSMContext):
    try:
        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()
        await callback.message.answer(
            text='Сейчас мы последовательно заполним анкету регистрации.\nВведите ваше имя (только имя, без фамилии)',
        )
        # Устанавливаем состояние ожидания ввода имени
        await state.set_state(FSMRegistration.fill_name)
        # Устанавливаем состояние ожидания обновления данных без последующей регистрации
        await state.update_data(is_registration=False)  # Добавляем дополнительное поле в контексте состояния
        await state.set_state(FSMRereg.fill_no_reg)
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления данных члена без регистрации: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')



# Хэндлер на отказ от обновления члена (и без регистрации - то есть, выход)
@router.callback_query(StateFilter(FSMRereg.fill_OK), F.data == 'no_reg_member')
@log_handler_call
async def process_no_reg_member(callback: CallbackQuery, state: FSMContext):
    try:
        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()
        await callback.message.answer(
            text='Вы вышли из анкеты регистрации\n\nЧтобы снова перейти к заполнению анкеты - снова нажмите кнопку "регистрация"'
        )
        # Сбрасываем состояние и очищаем данные, полученные внутри состояний
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обработке отказа от обновления данных: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')

# Хэндлер на обновление данных пользователя с последующей регистрацией
@router.callback_query(StateFilter(FSMRereg.fill_OK), F.data == 'yes_rereg_user')
@log_handler_call
async def process_yes_rereg_user(callback: CallbackQuery, state: FSMContext):
    try:
        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()
        await callback.message.answer(
            text='Сейчас мы последовательно заполним анкету регистрации.\nВведите ваше имя (только имя, без фамилии)',
        )
        # Устанавливаем состояние ожидания ввода имени
        await state.set_state(FSMRegistration.fill_name)
    except Exception as e:
        logger.error(f"Ошибка при обработке обновления данных пользователя с регистрацией: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')



# Хэндлер на необновление данных, но на регистрации пользователя в группе. Делаем сразу к регистрации
@router.callback_query(StateFilter(FSMRereg.fill_OK), F.data == 'no_rereg_user')
@log_handler_call
async def process_no_rereg(callback: CallbackQuery, state: FSMContext):
    try:
        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()

        # Получаем список модераторов
        moderators = await list_of_members_tg('registrator')  # Предполагается, что этот метод возвращает список модераторов

        buttons = []
        for member in moderators:
            name, famil, tg_id = member  # Предполагаем, что каждый элемент списка содержит имя, фамилию и tg_id
            buttons.append([InlineKeyboardButton(
                text=f'{name} {famil}',
                callback_data=str(tg_id)
            )])

        buttons.append([InlineKeyboardButton(
            text='Никого из модераторов не знаю',
            callback_data='stranger'
        )])

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        # Отправляем пользователю клавиатуру для выбора модератора
        await callback.message.answer(
            text=("Спасибо!\n"
                  "Выберите модератора, которого знаете,\n"
                  "чтобы он смог подтвердить вашу личность\n"
                  "Если никого не знаете,\n"
                  "Нажмите кнопку 'Никого не знаю'"),
            reply_markup=markup  # клавиатура подтверждения
        )
        # Устанавливаем состояние ожидания выбора модератора
        await state.set_state(FSMRegistration.fill_registrator)
    except Exception as e:
        logger.error(f"Ошибка при обработке необновления данных с регистрацией: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')



# Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# кроме состояния по умолчанию, и отключать машину состояний
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
@log_handler_call
async def process_cancel_command_state(message: Message, state: FSMContext, data:dict):
    try:
        await message.answer(
            text='Вы вышли из машины состояний',
            reply_markup=await user_menu(message.from_user.id,data['user_status'])
        )
        # Сбрасываем состояние и очищаем данные, полученные внутри состояний
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /cancel: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')



# Этот хэндлер будет срабатывать, если введено корректное имя
# и переводить в состояние ожидания ввода фамилии
@router.message(StateFilter(FSMRegistration.fill_name), F.text.isalpha())
@log_handler_call
async def process_name_sent(message: Message, state: FSMContext):
    logger.info(f"Введено имя кандидата: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем введенное имя в контексте состояния
    await state.update_data(first_name=message.text)
    await message.answer(text='Введите вашу фамилию')
    # Устанавливаем состояние ожидания ввода фамилии
    await state.set_state(FSMRegistration.fill_last_name)

# Этот хэндлер будет срабатывать, если во время ввода имени
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_name))
@log_handler_call
async def warning_not_name(message: Message):
    logger.warning(f"Некорректный ввод имени от пользователя {message.from_user.id}")
    await message.answer(
        text='То, что вы отправили не похоже на имя\n\n'
             'Пожалуйста, введите ваше имя\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать, если введена корректная фамилия
# и переводить в состояние ожидания ввода возраста
@router.message(StateFilter(FSMRegistration.fill_last_name), F.text.isalpha())
@log_handler_call
async def process_last_name_sent(message: Message, state: FSMContext):
    logger.info(f"Введена фамилия кандидата: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем введенную фамилию в контексте состояния
    await state.update_data(last_name=message.text)
    await message.answer(text='Введите ваш год рождения (формат YYYY)')
    # Устанавливаем состояние ожидания ввода возраста
    await state.set_state(FSMRegistration.fill_age)

# Этот хэндлер будет срабатывать, если во время ввода фамилии
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_last_name))
@log_handler_call
async def warning_last_name(message: Message):
    logger.warning(f"Некорректный ввод фамилии от пользователя {message.from_user.id}")
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
@log_handler_call
async def process_age_sent(message: Message, state: FSMContext):
    logger.info(f"Введен год рождения кандидата: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем возраст в контексте состояния
    await state.update_data(birth_year=int(message.text))

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
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
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
@log_handler_call
async def warning_age(message: Message):
    logger.warning(f"Некорректный ввод года рождения от пользователя {message.from_user.id}")
    await message.answer(
        text='То, что вы отправили не похоже на год рождения\n\n'
             'Пожалуйста, введите ваш год рождения в формате YYYY (например, 1990)\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на нажатие кнопки при
# выборе пола и переводить в состояние отправки контакта
@router.callback_query(StateFilter(FSMRegistration.fill_gender),
                      F.data.in_(['male', 'female', 'undefined_gender']))
@log_handler_call
async def process_gender_press(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Выбран пол {callback.data} пользователем {callback.from_user.id}")
        # Сохраняем пол (callback.data нажатой кнопки) в хранилище по ключу "gender"
        await state.update_data(gender=callback.data)
        # Удаляем сообщение с кнопками, потому что следующий этап - отправка контакта
        # чтобы у пользователя не было желания тыкать кнопки
        await callback.message.delete()
        await callback.message.answer(
            text='Отправьте ваш контакт\nНажмите для этого кнопку в самом низу экрана',
            reply_markup=contact_markup
        )
        # Устанавливаем состояние ожидания отправки контакта
        await state.set_state(FSMRegistration.fill_contact)
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора пола: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')


# Этот хэндлер будет срабатывать, если во время выбора пола
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_gender))
@log_handler_call
async def warning_not_gender(message: Message):
    logger.warning(f"Некорректный ввод при выборе пола от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками при выборе пола\n\n'
             'Если вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер срабатывает на кнопку "Прислать контакт".
# Данные из контакта записываются в базу данных в строку соответствующего пользователя
@router.message(F.contact, StateFilter(FSMRegistration.fill_contact))
@log_handler_call
async def process_get_contact(message: Message, state: FSMContext):
    try:
        contact: Contact = message.contact
        tg_true = await ContactFilter(message)  # проверяем, действительно ли юзер прислал свой контакт - или чужой

        # Сохраняем данные контакта в контексте состояния
        await state.update_data(
            tg_phone_number=contact.phone_number,
            tg_first_name=contact.first_name,
            tg_last_name=contact.last_name,
            tg_true=tg_true  # флаг 0 в БД будет означать что перед нами хакер
        )

        user_dict = await state.get_data()

        # Создаем объекты инлайн-кнопок
        yes_button = InlineKeyboardButton(
            text='Да, всё верно',
            callback_data='yes_contact'
        )
        no_button = InlineKeyboardButton(
            text='Не верно',
            callback_data='no_contact'
        )
        # Добавляем кнопки в клавиатуру в один ряд
        keyboard: list[list[InlineKeyboardButton]] = [
            [yes_button, no_button]
        ]
        # Создаем объект инлайн-клавиатуры
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(
        "Спасибо за контакт!",
        reply_markup=remove_markup  # Удаляем клавиатуру с кнопкой "Отправить контакт"
    )

        await message.delete()
        await message.answer(
            text=f'''Спасибо!\n
                    Ваш номер был получен.\n
                    Проверьте ваши данные:\n
                    Имя: {user_dict["first_name"]}\n
                    Фамилия: {user_dict["last_name"]}\n
                    Возраст: {user_dict["birth_year"]}\n
                    Пол: {user_dict["gender"]}\n
                    Номер телефона: {user_dict["tg_phone_number"]}''',
            reply_markup=remove_markup
        )
        await message.answer(
            text='Всё правильно?',
            reply_markup=markup  # клавиатура подтверждения
        )
        logger.info(f"Контакт получен от пользователя {message.from_user.id}: {contact}")
        # Устанавливаем состояние ожидания подтверждения личных данных
        await state.set_state(FSMRegistration.fill_confirm1)
    except Exception as e:
        logger.error(f"Ошибка при обработке получения контакта: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер срабатывает на всё, что пришлют вместо контакта в состоянии ожидания контакта
@router.message(StateFilter(FSMRegistration.fill_contact))
@log_handler_call
async def warning_get_contact(message: Message):
    logger.warning(f"Некорректный ввод вместо контакта от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопкой "Отправить контакт"\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на подтверждение личных данных
@router.callback_query(StateFilter(FSMRegistration.fill_confirm1), F.data == 'yes_contact')
@log_handler_call
async def process_yes_contact(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Кнопка 'Да, всё верно' нажата пользователем {callback.from_user.id}")
        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()

        # Создаем объекты инлайн-кнопок c городами
        Novosibirsk_button = InlineKeyboardButton(
            text='Новосибирск',
            callback_data='Новосибирск'
        )
        Berdsk_button = InlineKeyboardButton(
            text='Бердск',
            callback_data='Бердск'
        )
        Kolcovo_button = InlineKeyboardButton(
            text='Кольцово',
            callback_data='Кольцово'
        )
        Krasnoobsk_button = InlineKeyboardButton(
            text='Краснообск',
            callback_data='Краснообск'
        )
        Iskitim_button = InlineKeyboardButton(
            text='Искитим',
            callback_data='Искитим'
        )
        Ob_button = InlineKeyboardButton(
            text='Обь',
            callback_data='Обь'
        )
        Other_button = InlineKeyboardButton(
            text='Другое',
            callback_data='other'
        )
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
    except Exception as e:
        logger.error(f"Ошибка при подтверждении личных данных: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')


# Этот хэндлер будет срабатывать на нажатие кнопки "Не верно" при подтверждении личных данных.
# Стираем кнопки и выходим из машины состояний.
@router.callback_query(StateFilter(FSMRegistration.fill_confirm1), F.data == 'no_contact')
@log_handler_call
async def process_no_contact(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Кнопка 'Не верно' нажата пользователем {callback.from_user.id}")

        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()

        # Завершаем машину состояний
        await state.clear()

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Спасибо! Ваши данные не добавлены\nПопробуйте еще раз.\nВы вышли из машины состояний'
        data['reply_markup'] = None  # Клавиатура не нужна

        # Отправляем сообщение о выходе из машины состояний
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при отказе от подтверждения личных данных: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = None  # Клавиатура не нужна

        # Отправляем сообщение об ошибке
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать, если во время подтверждения личных данных будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_confirm1))
@log_handler_call
async def warning_not_contact(message: Message):
    logger.warning(f"Некорректный ввод при подтверждении личных данных от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на нажатие кнопки города и переводить в состояние ожидания ввода улицы
@router.callback_query(StateFilter(FSMRegistration.fill_city),
                      F.data.in_(['Новосибирск', 'Бердск', 'Кольцово', 'Краснообск', 'Искитим', 'Обь']))
@log_handler_call
async def process_city_press(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Выбран город {callback.data} пользователем {callback.from_user.id}")
        # Сохраняем город (callback.data нажатой кнопки) в контексте состояния по ключу "city"
        await state.update_data(city=callback.data)
        # Удаляем сообщение с кнопками, потому что следующий этап - ввод улицы
        await callback.message.delete()
        await callback.message.answer(
            text='Спасибо! А теперь введите название вашей улицы.',
            reply_markup=remove_markup
        )
        # Устанавливаем состояние ожидания ввода названия улицы
        await state.set_state(FSMRegistration.fill_street)
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора города: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать на нажатие кнопки "Другое" при выборе города
@router.callback_query(StateFilter(FSMRegistration.fill_city), F.data == 'other')
@log_handler_call
async def process_other_city_press(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Кнопка 'Другое' нажата пользователем {callback.from_user.id}")
        # Удаляем сообщение с кнопками выбора города
        await callback.message.delete()
        await callback.message.answer(
            text='Введите название вашего города',
            reply_markup=remove_markup
        )
        # Устанавливаем состояние ожидания ввода названия города
        await state.set_state(FSMRegistration.fill_new_city)
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора другого города: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать, если во время ввода названия города
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_new_city))
@log_handler_call
async def warning_not_city(message: Message):
    logger.warning(f"Некорректный ввод названия города от пользователя {message.from_user.id}")
    await message.answer(
        text='То, что вы отправили не похоже на название населенного пункта\n\n'
             'Пожалуйста, введите название только буквами\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )


# Этот хэндлер будет срабатывать, если введено корректное название города
# и переводить в состояние ожидания ввода улицы
@router.message(StateFilter(FSMRegistration.fill_new_city), F.text.isalpha())
@log_handler_call
async def process_city_sent(message: Message, state: FSMContext):
    # Cохраняем введенное название в хранилище по ключу "city"
    await state.update_data(city=message.text)
    await message.answer(text='Спасибо!\n\nА теперь введите название вашей улицы')
    # Устанавливаем состояние ожидания ввода названия улицы
    await state.set_state(FSMRegistration.fill_street)


# Этот хэндлер будет срабатывать, если во время ввода названия города
# будет введено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_new_city))
@log_handler_call
async def warning_not_city(message: Message):
    await message.answer(
        text='То, что вы отправили не похоже на название населенного пункта\n\n'
             'Пожалуйста, введите название только буквами\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать, если введено корректное название улицы
# и переводить в состояние ожидания выбора типа дома
@router.message(StateFilter(FSMRegistration.fill_street))
@log_handler_call
async def process_street_sent(message: Message, state: FSMContext):
    try:
        logger.info(f"Введена улица {message.text} от пользователя {message.from_user.id}")
        # Сохраняем введенное название улицы в контексте состояния по ключу "street"
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

        await message.answer(
            text="""Спасибо!\n\nУкажите - вы проживаете в многоквартирном доме?\n
                    Или в частном?""",
            reply_markup=markup
        )
        # Устанавливаем состояние ожидания выбора типа дома
        await state.set_state(FSMRegistration.fill_yes_mkd)
    except Exception as e:
        logger.error(f"Ошибка при обработке ввода названия улицы: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')


# Этот хэндлер будет срабатывать на нажатие кнопки "Многоквартирном"
# при выборе типа дома и переводить в состояние ввода номера дома
@router.callback_query(StateFilter(FSMRegistration.fill_yes_mkd), F.data == 'mkd')
@log_handler_call
async def process_mkd_press(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Кнопка 'Многоквартирном' нажата пользователем {callback.from_user.id}")
        # Удаляем сообщение с кнопками,
        # чтобы у пользователя не было желания тыкать кнопки
        await callback.message.delete()
        await callback.message.answer(
            text='Спасибо! А теперь введите номер дома'
        )
        # Устанавливаем состояние ожидания ввода номера дома
        await state.set_state(FSMRegistration.fill_number_mkd)
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора многоквартирного дома: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать на нажатие кнопки "Частном"
# при выборе типа дома и переводить в состояние ожидания выбора диапазона номеров
@router.callback_query(StateFilter(FSMRegistration.fill_yes_mkd), F.data == 'ijs')
@log_handler_call
async def process_ijs_press(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Кнопка 'Частном' нажата пользователем {callback.from_user.id}")
        # Удаляем сообщение с кнопками,
        # чтобы у пользователя не было желания тыкать кнопки
        await callback.message.delete()

        # Делаем клавиатуру из диапазонов номеров домов
        buttons = []
        for start in range(0, 621, 20):
            end = start + 20 if start < 620 else 'Больше, чем 640'
            button = InlineKeyboardButton(
                text=f'{start + 1}-{end}',
                callback_data=f'{start + 1}-{end}'
            )
            buttons.append(button)

        keyboard: list[list[InlineKeyboardButton]] = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await callback.message.answer(
            text='Спасибо! А теперь укажите интервал, \nв котором находится номер вашего дома',
            reply_markup=markup
        )
        # Устанавливаем состояние ожидания выбора интервала номеров
        await state.set_state(FSMRegistration.fill_range_num)
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора частного дома: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать, если во время выбора типа дома
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_yes_mkd))
@log_handler_call
async def warning_not_mkd(message: Message):
    logger.warning(f"Некорректный ввод при выборе типа дома от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками при выборе типа дома\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на ввод номера многоквартирного дома
# и переводить в состояние ожидания подтверждения адреса
@router.message(StateFilter(FSMRegistration.fill_number_mkd), lambda x: x.text.isdigit())
@log_handler_call
async def process_house_number_sent(message: Message, state: FSMContext):
    try:
        logger.info(f"Введен номер дома {message.text} от пользователя {message.from_user.id}")
        # Сохраняем введенный номер дома в контексте состояния по ключу "house"
        await state.update_data(house=message.text)

        # Создаем объекты инлайн-кнопок
        yes_button = InlineKeyboardButton(
            text='Да, всё верно',
            callback_data='yes_address'
        )
        no_button = InlineKeyboardButton(
            text='Не верно',
            callback_data='no_address'
        )
        # Добавляем кнопки в клавиатуру в один ряд
        keyboard: list[list[InlineKeyboardButton]] = [
            [yes_button, no_button]
        ]
        # Создаем объект инлайн-клавиатуры
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        # Выводим данные адреса для подтверждения
        user_dict = await state.get_data()
        await message.answer(
            text=f'Спасибо!\n'
                 'Проверьте ваш адрес:\n'
                 f'Город: {user_dict["city"]}\n'
                 f'Улица: {user_dict["street"]}\n'
                 f'Дом: {user_dict["house"]}\n'
                 'Всё правильно?',
            reply_markup=markup  # клавиатура подтверждения
        )
        logger.info(f"Данные адреса для подтверждения: {user_dict}")
        # Устанавливаем состояние ожидания подтверждения адреса
        await state.set_state(FSMRegistration.fill_confirm2)
    except Exception as e:
        logger.error(f"Ошибка при обработке ввода номера дома: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать на нажатие кнопки диапазона домов
@router.callback_query(StateFilter(FSMRegistration.fill_range_num))
@log_handler_call
async def process_range_house_press(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Выбран диапазон домов {callback.data} пользователем {callback.from_user.id}")
        # Сохраняем диапазон (callback.data нажатой кнопки) в контексте состояния по ключу "house"
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
            callback_data='no_address'
        )
        # Добавляем кнопки в клавиатуру в один ряд
        keyboard: list[list[InlineKeyboardButton]] = [
            [yes_button, no_button]
        ]
        # Создаем объект инлайн-клавиатуры
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        # Выводим данные адреса для подтверждения
        user_dict = await state.get_data()
        await callback.message.answer(
            text=f"Спасибо!\nПроверьте ваш адрес:\n"
                 f'Город: {user_dict["city"]}\n'
                 f'Улица: {user_dict["street"]}\n'
                 f'Дом: {user_dict["house"]}\n'
                 "Всё правильно?",
            reply_markup=markup  # клавиатура подтверждения
        )
        logger.info(f"Данные адреса для подтверждения: {user_dict}")
        # Устанавливаем состояние ожидания подтверждения адреса
        await state.set_state(FSMRegistration.fill_confirm2)
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора диапазона домов: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать, если во время выбора диапазона номеров домов
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_range_num))
@log_handler_call
async def warning_not_range(message: Message):
    logger.warning(f"Некорректный ввод при выборе диапазона номеров домов от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками при выборе диапазона номеров.\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на подтверждение адреса, если дальнейшая регистрация не требуется (и на выход)
@router.callback_query(StateFilter(FSMRegistration.fill_confirm2, FSMRereg.fill_no_reg), F.data == 'yes_address')
@log_handler_call
async def process_yes_adress_no_reg(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Кнопка 'Да, всё верно' нажата пользователем {callback.from_user.id} без дальнейшей регистрации")
        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()
        tg_id = callback.from_user.id

        # Заносим данные регистрации в строку соответствующего пользователя в базе данных
        user_dict = await state.get_data()
        success, result = await update_address(tg_id, user_dict['city'], user_dict['street'], user_dict['house'])

        if not success:
            await callback.message.answer(text=result)
            return

        # Меняем статус пользователя на 'candidate'
        success, result = await new_status_tg(0, tg_id, 'candidate')  # меняем статус пользователя на 'candidate'
        if not success:
            await callback.message.answer(text=result)
            return

        # Завершаем машину состояний
        await state.clear()
        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.answer(
            text='Спасибо! Ваши данные сохранены'
        )
    except Exception as e:
        logger.error(f"Ошибка при подтверждении адреса без дальнейшей регистрации: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')



# Этот хэндлер будет срабатывать на подтверждение адреса
@router.callback_query(StateFilter(FSMRegistration.fill_confirm2), F.data == 'yes_address')
@log_handler_call
async def process_yes_adress(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Кнопка 'Да, всё верно' нажата пользователем {callback.from_user.id} с дальнейшей регистрацией")
        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()

        # Создаем инлайн-кнопки для выбора регистратора
        registrators = await list_of_members_tg('registrator')
        buttons: list[list[InlineKeyboardButton]] = []
        for item in registrators:
            name, last_name, tg_id = item
            buttons.append([InlineKeyboardButton(
                text=f'{name} {last_name}',
                callback_data=str(tg_id)
            )])

        buttons.append([InlineKeyboardButton(
            text='Никого из регистраторов не знаю',
            callback_data='stranger'
        )])

        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        # Отправляем пользователю клавиатуру для выбора регистратора
        await callback.message.answer(
            text="Спасибо!\nВыберите регистратора, которого знаете,\nчтобы он смог подтвердить вашу личность\nЕсли никого не знаете,\nНажмите кнопку 'Никого не знаю'",
            reply_markup=markup  # клавиатура подтверждения
        )
        # Устанавливаем состояние ожидания выбора модератора
        await state.set_state(FSMRegistration.fill_registrator)
    except Exception as e:
        logger.error(f"Ошибка при обработке подтверждения адреса: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать на отказ подтвердить адрес
@router.callback_query(StateFilter(FSMRegistration.fill_confirm2), F.data == 'no_address')
@log_handler_call
async def process_no_address(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Кнопка 'Не верно' нажата пользователем {callback.from_user.id}")

        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()

        # Завершаем машину состояний
        await state.clear()

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Спасибо! Ваши данные не добавлены\nПопробуйте еще раз.\nВы вышли из машины состояний'
        data['reply_markup'] = None  # Клавиатура не нужна

        # Отправляем сообщение о выходе из машины состояний
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при отказе от подтверждения адреса: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = None  # Клавиатура не нужна

        # Отправляем сообщение об ошибке
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать, если вместо подтверждения адреса
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_confirm2))
@log_handler_call
async def warning_not_address(message: Message):
    logger.warning(f"Некорректный ввод при подтверждении адреса от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на выбор регистратора
@router.callback_query(StateFilter(FSMRegistration.fill_registrator),
                      lambda x: x.data.isdigit() or x.data == 'stranger')
@log_handler_call
async def process_registrator_press(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Выбран регистратор {callback.data} пользователем {callback.from_user.id}")

        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()

        # Сохраняем знакомого модератора (callback.data нажатой кнопки) в контексте состояния по ключу "familiar"
        await state.update_data(familiar=callback.data)
        tg_id = callback.from_user.id

        # Заносим данные регистрации в строку соответствующего пользователя в базе данных
        user_dict = await state.get_data()
        success, result = await update_address(tg_id, user_dict['city'], user_dict['street'], user_dict['house'])

        if not success:
            await callback.message.answer(text=result)
            return

        # Меняем статус пользователя на 'candidate'
        success, result = await new_status_tg(None, tg_id, 'candidate')  # меняем статус пользователя на 'candidate'
        if not success:
            await callback.message.answer(text=result)
            return

        # Завершаем машину состояний
        await state.clear()

        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.answer(
            text='Спасибо! Ваши данные сохранены.\nАдминистрация их проверит и даст вам соответствующие права\nВы вышли из машины состояний'
        )

        # Если выбран регистратор, отправляем ему сообщение с просьбой подтвердить регистрацию
        if callback.data.isdigit():
            success, result = await notify_registrator(int(callback.data), tg_id, user_dict)
            if not success:
                await callback.message.answer(text=f'Ошибка при уведомлении регистратора: {result}')
        else:
            logger.info(f"Пользователь {tg_id} выбрал 'Никого не знаю'.")
    except Exception as e:
        logger.error(f"Ошибка при выборе регистратора: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')
        # Завершаем машину состояний
        await state.clear()

# Этот хэндлер будет срабатывать, если во время выбора регистратора
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMRegistration.fill_registrator))
@log_handler_call
async def warning_not_registrator(message: Message):
    logger.warning(f"Некорректный ввод при выборе модератора от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками при выборе модератора.\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )
