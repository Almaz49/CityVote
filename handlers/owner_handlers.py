import logging
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from filters.filters import StatusFilter
from FSMs.FSMs import FSMNewStatus, AdminStates
from data_base.telegram_bot_logic import *
from services.services import process_channel_info
from utils import log_handler_call
from keyboards.keyboards import *
from LEXICON.LEXICON import LEXICON

# Настройка логирования
logger = logging.getLogger(__name__)

# # Загружаем конфиг в переменную config
# config: Config = load_config('.env')
# bot = Bot(token=config.tg_bot.token)
# path_db = config.db.path_db  # путь к базе данных
# club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status = ['owner']))
router.callback_query.filter(StatusFilter(required_status = ['owner']))

"""
Хэндлеры FSM присвоения нового статуса выбранному участнику группы
"""
# Этот хэндлер будет срабатывать на команду /new_status
# и переводить бота в состояние ожидания ввода телеграм-ID участника,
# которому меняется статус
@router.message(Command(commands='new_status'), StateFilter(default_state))
@log_handler_call
async def process_new_status(message: Message, state: FSMContext):
    await message.answer(text='''Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус или отправьте контакт с ID''')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(FSMNewStatus.fill_ID_User)

# Этот хэндлер будет срабатывать на нажатие кнопки "новый статус" в меню админа
@router.callback_query(StateFilter(default_state), F.data == 'new_status')
@log_handler_call
async def process_new_status_cb(callback: CallbackQuery, state: FSMContext, data: dict):
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = '''Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус или отправьте контакт с ID'''
    data['reply_markup'] = None  # Если клавиатура не нужна, устанавливаем None

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text( # type: ignore
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMNewStatus.fill_ID_User)
    logger.info(f"Установлено состояние: {await state.get_state()}")


# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewStatus.fill_ID_User), ~F.contact, (lambda x: x.text.isdigit()))
@log_handler_call
async def process_user_id_sent(message: Message, state: FSMContext):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.info(f"Введенный ID пользователя: {message.text} от пользователя {message.from_user.id}")
    if message.text is not None:
        try:
            user_tg_id = int(message.text.strip())
        except ValueError:
            await message.answer("Пожалуйста, введите корректное числовое значение.")
            raise ValueError("Сообщние не содержит числовое значение.")
    else:
        await message.answer("Сообщение не содержит текст. Пожалуйста, попробуйте снова.")
        raise ValueError("Сообщние не содержит текст")
    await state.update_data(ID=user_tg_id)
    try:
        user_id, user_member_id = await extract_user_member_id(user_tg_id)
        if user_member_id:
            user_profile = await extract_profile(user_member_id)
            if user_profile:
                await message.answer(
                    text=f'''Данные участника которому вы меняете статус:\nИмя: {user_profile.get('first_name')},
    Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
    Псевдоним: {user_profile.get('username')} Всё верно?''',
                    reply_markup=confirm_markup  # клавиатура подтверждения из модуля клавиатур
                )
                # Устанавливаем состояние ожидания подтверждения
                await state.set_state(FSMNewStatus.fill_OK)
            else:
                await message.answer(text='Данные участника не найдены')
                # Сбрасываем состояние и очищаем данные, полученные внутри состояний
                await state.clear()
        else:
            await message.answer(text='Такой участник не найден')
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')
        await state.clear()


# Этот хэндлер будет срабатывать, если  отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewStatus.fill_ID_User), F.contact)
@log_handler_call
async def process_user_contact_sent(message: Message, state: FSMContext, contact: Contact):
    if message.contact is None:
        await message.answer("Пожалуйста, отправьте контакт.")
        raise ValueError("Сообщние не содержит контакта.")
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    contact = message.contact
    logger.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")

    if not contact.user_id:
        await message.answer("К сожалению, ID контакта отсутствует. Попробуйте отправить просто ID")
        raise ValueError("Сообщние не содержит ID контакта.")

    user_tg_id = contact.user_id

    await state.update_data(ID=user_tg_id)
    try:
        user_id, user_member_id = await extract_user_member_id(user_tg_id)
        if user_member_id:
            user_profile = await extract_profile(user_member_id)
            if user_profile:
                await message.answer(
                    text=f'''Данные участника которому вы меняете статус:\nИмя: {user_profile.get('first_name')},
    Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
    Псевдоним: {user_profile.get('username')} Всё верно?''',
                    reply_markup=confirm_markup  # клавиатура подтверждения из модуля клавиатур
                )
            else:
                await message.answer(text='Данные участника не найдены')
                # Сбрасываем состояние и очищаем данные, полученные внутри состояний
                await state.clear()

            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMNewStatus.fill_OK)
        else:
            await message.answer(text='Такой участник не найден')
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')
        await state.clear()

# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
async def process_status_choice(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    logger.info(f'FSM data: \n{fsm_data}\n')
    member_tg_id = fsm_data['ID']

    try:
        status = await extract_status_tg(member_tg_id)
        status = status if status else []
        all_st = await all_status()

        vacansy = list(set(all_st) - set(status) - {'owner', 'user', 'candidate','votist','proxy','pre-registrator'})
        status = list(set(status) - {'owner', 'member', 'user', 'candidate'})

        logger.debug(f'Вакансии для пользователя: {vacansy}')

        keyboards = []
        for item in vacansy:
            keyboards.append('AppointAs_' + item)
        for item in status:
            keyboards.append('not_' + item)

        keyboards.append('main_menu')
        markup = create_inline_kb(1, *keyboards)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = '''Выберите, какой статус вы хотите добавить пользователю, или удалить.
\nЕсли хотите прервать процедуру - наберите /cancel'''
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text( # type: ignore
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        # Устанавливаем состояние ожидания выбора статуса
        await state.set_state(FSMNewStatus.fill_choice)

    except Exception as e:
        logger.error(f"Ошибка при формировании клавиатуры статусов: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text( # type: ignore
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_status_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний'
    data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text( # type: ignore
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# данных пользователя будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_OK))
@log_handler_call
async def warning_registrator(message: Message):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать назначение регистратора - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на выбор одного из статусов (или его отмены)
@router.callback_query(StateFilter(FSMNewStatus.fill_choice), F.data != 'main_menu')
@log_handler_call
async def process_new_status_confirm(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Выбран статус: {callback.data} пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    if not callback.data:
        raise ValueError("Нет callback.data")
    await state.update_data(status=callback.data)
    status = callback.data
    fsm_data = await state.get_data()
    member_tg_id = fsm_data['ID']

    try:
        user_id, member_id = await extract_user_member_id(member_tg_id)
        if not member_id:
            raise ValueError("Нет member_ID пользователя")
        user_profile = await extract_profile(member_id)
        if user_profile:
           status_text = LEXICON.get(status, status)
           text=f'''Данные участника которому вы меняете статус:\nИмя: {user_profile.get('first_name')},
Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
Псевдоним: {user_profile.get('username')}\nВы хотите изменить его статус:
\n{status_text}\nВсё верно?'''
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = confirm_markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text( # type: ignore
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.set_state(FSMNewStatus.fill_new_status_confirm)

    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя или формировании сообщения: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text( # type: ignore
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки

# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении
# нового статуса, присваиваемого пользователю
@router.callback_query(StateFilter(FSMNewStatus.fill_new_status_confirm), F.data == 'ConfirmOK')
@log_handler_call
async def process_new_status_entry(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Присваиваем переменной st значение статуса без приставки, чтобы проверить существует ли вообще такой статус
    fsm_data = await state.get_data()
    status = fsm_data['status']
    st = status
    if status.split('_')[0] == 'not':
        st = status[4:]
    if status.split('_')[0] == 'AppointAs':
        st = status[10:]

    try:
        if st not in await all_status():
            await state.clear()

            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Извините, такого статуса нет.\n\n Попробуйте снова.' \
                                    'Вы вышли из машины состояний'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Пытаемся отредактировать сообщение
            await callback.message.edit_text( # type: ignore
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
        else:
            member_tg_id = fsm_data['ID']
            registrator_tg_id = callback.from_user.id
            ans_str = await new_status_tg(registrator_tg_id, member_tg_id, status)  # Вызов функции присвоения нового статуса

            if isinstance(ans_str, str) and 'Ошибка' in ans_str:
                # Добавляем данные для SafeEditMiddleware
                data['response_text'] = f'Произошла ошибка: {ans_str}'
                data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

                # Пытаемся отредактировать сообщение
                await callback.message.edit_text( # type: ignore
                    text=data['response_text'],
                    reply_markup=data['reply_markup']
                )
                return

            # Завершаем машину состояний
            await state.clear()

            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Спасибо! Статус участника обновлен!\n\n' \
                                    'Вы вышли из машины состояний'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Пытаемся отредактировать сообщение
            await callback.message.edit_text( # type: ignore
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

    except Exception as e:
        logger.error(f"Ошибка при присвоении нового статуса: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text( # type: ignore
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_new_status_confirm), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_status(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний'
    data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text( # type: ignore
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# статуса будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_new_status_confirm))
@log_handler_call
async def warning_new_status(message: Message):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_new_status_confirm}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать изменение статуса - '
             'отправьте команду /cancel'
    )

"""
АДМИНИСТРИРОВАНИЕ БОТА
"""
# Обрабатывает нажатие кнопик "admin_bot", присылает клавиатуру администрирования
@router.callback_query(F.data == "admin_bot")
@log_handler_call
async def admin_menu(callback: CallbackQuery):
    markup = get_admin_menu_keyboard()
    await callback.message.edit_text("Выберите действие:", reply_markup=markup) # type: ignore


# Изменение имени группы

@router.callback_query(F.data == "edit_club_name")
@log_handler_call
async def edit_club_name_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое имя группы:") # type: ignore
    await state.set_state(AdminStates.entering_club_name)

@router.message(AdminStates.entering_club_name)
@log_handler_call
async def process_club_name(message: Message, state: FSMContext, club_id: int):
    if not message.text:
        await message.answer("Имя не может быть пустым. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Имя не может быть пустым. Попробуйте снова.")
        return

    success = await update_club_name(club_id=club_id, new_name=new_name)
    if success:
        await message.answer(f"Имя группы успешно изменено на: {new_name}")
    else:
        await message.answer("Произошла ошибка при изменении имени группы.")

    await state.clear()


# Изменение описания группы

@router.callback_query(F.data == "edit_club_description")
@log_handler_call
async def edit_club_description_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое описание группы:") # type: ignore
    await state.set_state(AdminStates.entering_club_description)

@router.message(AdminStates.entering_club_description)
@log_handler_call
async def process_club_description(message: Message, state: FSMContext, club_id: int):
    if not message.text:
        await message.answer("Описание не может быть пустым. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")
    new_description = message.text.strip()
    if not new_description:
        await message.answer("Описание не может быть пустым. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")

    success = await update_club_description(club_id=club_id, new_description=new_description)
    if success:
        await message.answer(f"Описание группы успешно изменено.")
    else:
        await message.answer("Произошла ошибка при изменении описания группы.")

    await state.clear()


# Изменение условий участия

@router.callback_query(F.data == "edit_club_conditions")
@log_handler_call
async def edit_club_conditions_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новые условия участия в группе:") # type: ignore
    await state.set_state(AdminStates.entering_club_conditions)

@router.message(AdminStates.entering_club_conditions)
@log_handler_call
async def process_club_conditions(message: Message, state: FSMContext, club_id: int):
    if not message.text:
        await message.answer("Условия не могут быть пустыми. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")
    new_conditions = message.text.strip()
    if not new_conditions:
        await message.answer("Условия не могут быть пустыми. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")

    success = await update_club_conditions(club_id=club_id, new_conditions=new_conditions)
    if success:
        await message.answer(f"Условия участия успешно изменены.")
    else:
        await message.answer("Произошла ошибка при изменении условий участия.")

    await state.clear()


# Добавление телеграм-канала

@router.callback_query(F.data == "add_channel")
@log_handler_call
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID или ссылку на канал/чат для рассылок:") # type: ignore
    await state.set_state(AdminStates.adding_telegram_channel)

@router.message(AdminStates.adding_telegram_channel)
@log_handler_call
async def process_add_channel(message: Message, state: FSMContext, club_id: int):
    if  not message.text:
        await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")
    channel_info = message.text.strip()
    if not channel_info:
        await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        raise

    result = await process_channel_info(channel_info, club_id, "add")
    await message.answer(result["message"])
    await state.clear()


# Удаление телеграм-канала

@router.callback_query(F.data == "remove_channel")
@log_handler_call
async def remove_channel_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID или ссылку на канал/чат для удаления из рассылок:") # type: ignore
    await state.set_state(AdminStates.removing_telegram_channel)

@router.message(AdminStates.removing_telegram_channel)
@log_handler_call
async def process_remove_channel(message: Message, state: FSMContext, club_id: int):
    if  not message.text:
        await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")
    channel_info = message.text.strip()
    if not channel_info:
        await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        return

    result = await process_channel_info(channel_info, club_id, "remove")
    await message.answer(result["message"])
    await state.clear()


# Установка основного канала

@router.callback_query(F.data == "set_main_channel")
@log_handler_call
async def set_main_channel_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID или ссылку на основной канал/чат:") # type: ignore
    await state.set_state(AdminStates.setting_main_channel)

@router.message(AdminStates.setting_main_channel)
@log_handler_call
async def process_set_main_channel(message: Message, state: FSMContext, club_id: int):
    if  not message.text:
        await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        raise ValueError("Текст сообщения пуст")
    channel_info = message.text.strip()
    if not channel_info:
        await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        return

    result = await process_channel_info(channel_info, club_id, "set_main")
    # Логирование результата
    logger.debug(f"Результат операции: {result}")

    if isinstance(result, dict) and "message" in result:
        await message.answer(result["message"])
    else:
        await message.answer("Произошла ошибка при обработке запроса.")

    await state.clear()

# Установка продолжительности этапов голосования

# 1. Команда для запуска процесса
@router.message(Command(commands='set_stage_durations'), StateFilter(default_state))
@log_handler_call
async def start_setting_stage_durations(message: Message, state: FSMContext):
    if  not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")
    logger.info(f"Команда /set_stage_durations сработала для пользователя {message.from_user.id}")
    await message.answer(
        text="Введите продолжительность этапов голосования (в сутках) в следующем формате:\n"
             "1. Продолжительность этапа добавления вариантов\n"
             "2. Продолжительность основного этапа\n"
             "3. Продолжительность финального этапа\n"
             "4. Продолжительность этапа утверждения итогов\n"
             "Пример: `2 3 1 1` (через пробел)."
    )
    await state.set_state(AdminStates.setting_stage_durations)

# Тоже самое при обработке кнопки 'set_stage_durations'
@router.callback_query(StateFilter(default_state), F.data == 'set_stage_durations')
@log_handler_call
async def process_set_stage_durations_cb(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик нажатия кнопки "Установить продолжительность этапов голосования" в меню администрирования.
    """
    logger.info(f"Кнопка 'set_stage_durations' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Формируем текст и клавиатуру для ответа
    response_text = (
        "Введите продолжительность этапов голосования (в сутках) в следующем формате:\n"
        "1. Продолжительность этапа добавления вариантов\n"
        "2. Продолжительность основного этапа\n"
        "3. Продолжительность финального этапа\n"
        "4. Продолжительность этапа утверждения итогов\n"
        "Пример: `2 3 1 1` (через пробел)."
    )
    reply_markup = None  # Клавиатура не нужна

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = response_text
    data['reply_markup'] = reply_markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text( # type: ignore
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Устанавливаем состояние ожидания ввода продолжительности этапов
    await state.set_state(AdminStates.setting_stage_durations)

# 2. Хэндлер для обработки ввода значений

@router.message(StateFilter(AdminStates.setting_stage_durations), F.text)
@log_handler_call
async def process_stage_durations_input(message: Message, state: FSMContext):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.info(f"Пользователь {message.from_user.id} ввел продолжительность этапов: {message.text}")
    try:
        if not message.text:
            await message.answer("Произошла ошибка: данные не найдены.")
            logger.warning("Данные введены пустыми")
            raise ValueError("Данные введены пустыми")
        # Разбиваем введенные данные на список чисел
        durations = list(map(int, message.text.split()))
        if len(durations) != 4:
            raise ValueError("Неверное количество значений")

        # Проверяем, что все значения положительные
        if any(d <= 0 for d in durations):
            raise ValueError("Значения должны быть положительными числами")

        # Сохраняем данные в FSM
        await state.update_data(
            duration_add_variants=durations[0],
            duration_first_stage=durations[1],
            duration_final=durations[2],
            duration_confirmation=durations[3]
        )

        # Формируем текст для подтверждения
        confirmation_text = (
            f"Подтвердите продолжительность этапов голосования (в сутках):\n"
            f"1. Этап добавления вариантов: {durations[0]} суток\n"
            f"2. Основной этап: {durations[1]} суток\n"
            f"3. Финальный этап: {durations[2]} суток\n"
            f"4. Этап утверждения итогов: {durations[3]} суток\n"
            "Всё верно?"
        )

        # Отправляем сообщение с подтверждением
        markup = confirm_markup
        await message.answer(text=confirmation_text, reply_markup=markup)
        await state.set_state(AdminStates.setting_stage_durations)

    except ValueError as e:
        logger.warning(f"Ошибка ввода длительности этапов от пользователя {message.from_user.id}: {e}")
        await message.answer(
            text=f"Некорректный ввод: {e}\nПожалуйста, введите четыре положительных числа через пробел."
        )

# 3. Хэндлер для подтверждения ввода
@router.callback_query(StateFilter(AdminStates.setting_stage_durations), F.data == 'ConfirmOK')
@log_handler_call
async def confirm_stage_durations(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    club_id = data['club_id']
    result = await update_stage_duration(
        club_id=club_id,
        duration_add_variants=fsm_data['duration_add_variants'],
        duration_first_stage=fsm_data['duration_first_stage'],
        duration_final=fsm_data['duration_final'],
        duration_confirmation=fsm_data['duration_confirmation']
    )

    # Формируем ответ
    response_text = result if isinstance(result, str) else "Произошла ошибка при сохранении данных."
    markup = await user_menu(callback.from_user.id, data['user_status'])

    # Отправляем ответ и завершаем машину состояний
    await callback.message.edit_text(text=response_text, reply_markup=markup) # type: ignore
    await state.clear()

# 4. Хэндлер для отмены подтверждения
@router.callback_query(StateFilter(AdminStates.setting_stage_durations), F.data == 'ConfirmNotOK')
@log_handler_call
async def cancel_stage_durations(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Завершаем машину состояний
    await state.clear()

    # Отправляем сообщение об отмене
    response_text = "Установка продолжительности этапов отменена."
    markup = await user_menu(callback.from_user.id, data['user_status'])
    await callback.message.edit_text(text=response_text, reply_markup=markup) # type: ignore

# Установка электоральных порогов для делегатов.
# Один порог - в голосах, другой - в процентах. Работать будет тот, который больше.

# 1. Хэндлер для обработки нажатия кнопки с callback_data='set_threshold'
@router.callback_query(StateFilter(default_state), F.data == 'set_threshold')
@log_handler_call
async def process_set_threshold_cb(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик нажатия кнопки "Установить пороги доверенных голосов" в меню администрирования.
    """
    logger.info(f"Кнопка 'set_threshold' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Формируем текст для инструкции
    response_text = (
        "Введите пороги доверенных голосов в следующем формате:\n"
        "1. Минимальное количество голосов (число с плавающей точкой)\n"
        "2. Минимальный процент от общего числа голосов (число с плавающей точкой)\n"
        "Пример: `10.5 5.0` (через пробел)."
    )
    response_text = (
        "Введите пороги доверенных голосов в следующем формате:\n"
        "1. Минимальное количество голосов (число с плавающей точкой или запятой)\n"
        "2. Минимальный процент от общего числа голосов (число с плавающей точкой или запятой)\n"
        "Примеры:\n"
        "- `10.5 5`\n"
        "- `10,5 1,5`\n"
        "- `10 15`\n"
        "Через пробел."
    )

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = response_text
    data['reply_markup'] = None  # Клавиатура не нужна

    # Редактируем сообщение
    await callback.message.edit_text( # type: ignore
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Устанавливаем состояние ожидания ввода порогов
    await state.set_state(AdminStates.setting_thresholds)


# 2. Хэндлер для обработки ввода значений порогов
@router.message(StateFilter(AdminStates.setting_thresholds), F.text)
@log_handler_call
async def process_thresholds_input(message: Message, state: FSMContext, data:dict):
    if not message.text:
        await message.answer("Введите значения порогов через пробел.")
        raise ValueError("Введено пустое значение")
    if not message.from_user:
        raise ValueError("Отправтель сообщения отсутствует (from_user == None)")

    logger.info(f"Пользователь {message.from_user.id} ввел пороги: {message.text}")
    try:
        # Заменяем запятую на точку для единообразия
        input_text = message.text.replace(',', '.')

        # Разбиваем введенные данные на список чисел
        thresholds = list(map(float, input_text.split()))

        # Проверяем, что введено ровно два значения
        if len(thresholds) != 2:
            raise ValueError("Неверное количество значений. Введите ровно два числа.")

        # Сохраняем данные в FSM
        await state.update_data(
            threshold_in_voices=thresholds[0],
            threshold_in_percent=thresholds[1]
        )

        # Формируем текст для подтверждения
        confirmation_text = (
            f"Подтвердите пороги доверенных голосов:\n"
            f"1. Минимальное количество голосов: {thresholds[0]}\n"
            f"2. Минимальный процент от общего числа голосов: {thresholds[1]}\n"
            "Всё верно?"
        )

        # Отправляем сообщение с подтверждением
        markup = confirm_markup
        await message.answer(text=confirmation_text, reply_markup=markup)
        await state.set_state(AdminStates.setting_thresholds)

    except ValueError as e:
        logger.warning(f"Ошибка ввода порогов от пользователя {message.from_user.id}: {e}")
        await message.answer(
            text=f"Некорректный ввод: {e}\n"
                 "Пожалуйста, введите два числа через пробел.\n"
                 "Разделителем между целой и дробной частью может быть точка или запятая."
        )


# 3. Хэндлер для подтверждения ввода
@router.callback_query(StateFilter(AdminStates.setting_thresholds), F.data == 'ConfirmOK')
@log_handler_call
async def confirm_thresholds(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    club_id = data['club_id']
    result = await update_thresholds(
        club_id=club_id,
        threshold_in_voices=fsm_data['threshold_in_voices'],
        threshold_in_percent=fsm_data['threshold_in_percent']
    )

    # Формируем ответ
    response_text = result if isinstance(result, str) else "Произошла ошибка при сохранении данных."
    markup = await user_menu(callback.from_user.id, data['user_status'])

    # Отправляем ответ и завершаем машину состояний
    await callback.message.edit_text(text=response_text, reply_markup=markup) # type: ignore
    await state.clear()


# 4. Хэндлер для отмены подтверждения
@router.callback_query(StateFilter(AdminStates.setting_thresholds), F.data == 'ConfirmNotOK')
@log_handler_call
async def cancel_thresholds(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Завершаем машину состояний
    await state.clear()

    # Отправляем сообщение об отмене
    response_text = "Установка порогов доверенных голосов отменена."
    markup = await user_menu(callback.from_user.id, data['user_status'])
    await callback.message.edit_text(text=response_text, reply_markup=markup) # type: ignore