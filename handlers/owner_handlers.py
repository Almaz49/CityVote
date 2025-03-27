import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from filters.filters import StatusFilter
from FSMs.FSMs import FSMNewRegistrator, FSMNewVoting, FSMNewStatus
from data_base.telegram_bot_logic import *
from utils import log_handler_call
from keyboards.keyboards import *
from config_data.config import Config, load_config

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)
path_db = config.db.path_db  # путь к базе данных
club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)

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
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMNewStatus.fill_ID_User)
    logging.info(f"Установлено состояние: {await state.get_state()}")


# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewStatus.fill_ID_User), ~F.contact, (lambda x: x.text.isdigit()))
@log_handler_call
async def process_user_id_sent(message: Message, state: FSMContext):
    logging.info(f"Введенный ID пользователя: {message.text} от пользователя {message.from_user.id}")
    user_tg_id = int(message.text)
    await state.update_data(ID=user_tg_id)
    try:
        user_data = await extract_user_data_tg(user_tg_id, 'id', 'tg_first_name', 'tg_last_name', 'tg_phone_number')  # извлекаем данные о пользователе
        if user_data:
            await message.answer(
                text=f'''Данные участника которому вы меняете статус:\nИмя: {user_data[1]},
Фамилия: {user_data[2]}, \n Телефон: {user_data[3]}\nВсё верно?''',
                reply_markup=confirm_markup  # клавиатура подтверждения из модуля клавиатур
            )
            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMNewStatus.fill_OK)
        else:
            await message.answer(text='Такой участник не найден')
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при извлечении данных пользователя: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')
        await state.clear()


# Этот хэндлер будет срабатывать, если  отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewStatus.fill_ID_User), F.contact)
@log_handler_call
async def process_user_contact_sent(message: Message, state: FSMContext, contact: Contact = None):
    contact = message.contact
    logging.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")
    user_tg_id = contact.user_id
    await state.update_data(ID=user_tg_id)
    try:
        user_data = await extract_user_data_tg(user_tg_id, 'id', 'tg_first_name', 'tg_last_name', 'tg_phone_number')  # извлекаем данные о пользователе
        if user_data:
            await message.answer(
                text=f'''Данные нового модератора\nИмя: {user_data[1]},
Фамилия: {user_data[2]}, \n Телефон: {user_data[3]}\nВсё верно?''',
                reply_markup=confirm_markup  # клавиатура подтверждения из модуля клавиатур
            )
            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMNewStatus.fill_OK)
        else:
            await message.answer(text='Такой участник не найден')
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при извлечении данных пользователя: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')
        await state.clear()

# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
async def process_status_choice(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    logging.info(f'FSM data: \n{fsm_data}\n')
    member_tg_id = fsm_data['ID']

    try:
        status = await extract_status_tg(member_tg_id)
        status = status if status else []
        all_st = await all_status()

        vacansy = list(set(all_st) - set(status) - {'owner', 'user', 'candidate','votist','proxy'})
        status = list(set(status) - {'owner', 'member', 'user', 'candidate'})

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
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        # Устанавливаем состояние ожидания выбора статуса
        await state.set_state(FSMNewStatus.fill_choice)

    except Exception as e:
        logging.error(f"Ошибка при формировании клавиатуры статусов: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_status_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний'
    data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# данных пользователя будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_OK))
@log_handler_call
async def warning_registrator(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать назначение регистратора - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на выбор одного из статусов (или его отмены)
@router.callback_query(StateFilter(FSMNewStatus.fill_choice))
@log_handler_call
async def process_new_status_confirm(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Выбран статус: {callback.data} пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    await state.update_data(status=callback.data)
    status = callback.data
    fsm_data = await state.get_data()
    member_tg_id = fsm_data['ID']

    try:
        user_data = await extract_user_data_tg(member_tg_id, 'id', 'tg_first_name', 'tg_last_name', 'tg_phone_number')  # Извлекаем данные о пользователе
        status_text = LEXICON[status] if status in LEXICON else status

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'''Данные пользователя\nИмя: {user_data[1]},
Фамилия: {user_data[2]}, \n Телефон: {user_data[3]}
\nВы хотите изменить его статус:
\n{status_text}
\nВсё верно?'''
        data['reply_markup'] = confirm_markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.set_state(FSMNewStatus.fill_new_status_confirm)

    except Exception as e:
        logging.error(f"Ошибка при извлечении данных пользователя или формировании сообщения: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
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
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    status = fsm_data['status']
    st = status.split('_')[1] if '_' in status else status

    try:
        if st not in await all_status():
            await state.clear()

            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Извините, такого статуса нет.\n\n Попробуйте снова.' \
                                    'Вы вышли из машины состояний'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'], data['user_status'])

            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
        else:
            member_tg_id = fsm_data['ID']
            registrator_tg_id = callback.from_user.id
            ans_str = await new_status_tg(registrator_tg_id, member_tg_id, st)  # Вызов функции присвоения нового статуса

            if isinstance(ans_str, str) and 'Ошибка' in ans_str:
                # Добавляем данные для SafeEditMiddleware
                data['response_text'] = f'Произошла ошибка: {ans_str}'
                data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

                # Пытаемся отредактировать сообщение
                await callback.message.edit_text(
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
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

    except Exception as e:
        logging.error(f"Ошибка при присвоении нового статуса: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Произошла ошибка: {str(e)}'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_new_status_confirm), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_sttus_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний'
    data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# статуса будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_new_status_confirm))
@log_handler_call
async def warning_new_status(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_new_status_confirm}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать изменение статуса - '
             'отправьте команду /cancel'
    )
