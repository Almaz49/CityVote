import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, PhotoSize
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from filters.filters import filter_isAdmin, filter_isOwner
from FSMs.FSMs import FSMNewRegistrator, FSMNewVoting, FSMNewStatus
from data_base.telegram_bot_logic import *
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
router.message.filter(filter_isAdmin or filter_isOwner)

# Этот хэндлер будет срабатывать на команду "/start"
# @router.message(Command(commands=["start"]))
# async def process_start_command1(message: Message):
#     await bot.send_message(message.from_user.id,
#         text='Привет, Админ!\nМеня зовут Эхо-бот!\nНапиши мне что-нибудь')

# Этот хэндлер будет срабатывать на команду "/cancel" в состоянии по умолчанию
# и сообщать, что эта команда работает внутри машины состояний
@router.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    logging.info(f"Команда /cancel сработала для пользователя {message.from_user.id} в состоянии по умолчанию")
    await message.answer(
        text='Отменять нечего. Вы вне машины состояний',
        reply_markup=remove_markup
    )

# Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# кроме состояния по умолчанию, и отключать машину состояний
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    logging.info(f"Команда /cancel сработала для пользователя {message.from_user.id} в состоянии {await state.get_state()}")
    await message.answer(
        text='Вы вышли из машины состояний',
        reply_markup=remove_markup
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()

"""
Хэндлеры FSM создания нового регистратора
"""

# Этот хэндлер будет срабатывать на команду /new_registrator
# и переводить бота в состояние ожидания ввода ID нового регистратора
@router.message(Command(commands='new_registrator'), StateFilter(default_state))
async def process_new_registrator(message: Message, state: FSMContext):
    logging.info(f"Команда /new_registrator сработала для пользователя {message.from_user.id}")
    await message.answer(text='Пожалуйста, введите ID нового регистратора')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(FSMNewRegistrator.fill_ID_NewRegistrator)

# Этот хэндлер будет срабатывать на команду /new_registrator
# если она не от админа или не из дефаулт стэйт
@router.message(Command(commands='new_registrator'))
async def process_new_registrator2(message: Message, state: FSMContext):
    logging.warning(f"Команда /new_registrator сработала для пользователя {message.from_user.id}, но пользователь не имеет прав администратора или находится в неподходящем состоянии.")
    await message.answer(text='У вас недостаточно прав. Или эта команда не к месту.')

# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewRegistrator.fill_ID_NewRegistrator),
               lambda x: x.text.isdigit())
async def process_registrator_id_sent(message: Message, state: FSMContext):
    logging.info(f"Введенный ID нового регистратора: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем ID в хранилище по ключу "ID"
    await state.update_data(ID=int(message.text))
    flag, ans_str = await extract_new_registrator_data(int(message.text))  # извлекаем данные о новом регистраторе

    # Создаем объекты инлайн-кнопок
    ok_mod_button = InlineKeyboardButton(
        text='ВСЁ ВЕРНО',
        callback_data='NewRegistratorOK'
    )
    no_mod_button = InlineKeyboardButton(
        text='НЕВЕРНО',
        callback_data='NewRegistratorNotOK'
    )
    # Добавляем кнопки в клавиатуру
    keyboard: list[list[InlineKeyboardButton]] = [
        [ok_mod_button, no_mod_button],
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(one_time_keyboard=True, inline_keyboard=keyboard)
    # Отправляем пользователю сообщение с клавиатурой
    if flag:
        await message.answer(
            text=f'Данные участника, которому вы меняете статус\n{ans_str}\nВсё верно?',
            reply_markup=markup
        )
        # Устанавливаем состояние ожидания подтверждения
        await state.set_state(FSMNewStatus.fill_OK)
    else:
        await message.answer(
            text=ans_str,
        )
        # Сбрасываем состояние и очищаем данные, полученные внутри состояний
        await state.clear()

# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK),
                      F.data == 'NewRegistratorOK')
async def process_yes_registrator_press(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    # Меняем в базе данных статус пользователя по ключу tg_id пользователя и tg_id регистратора (админа в данном случае)
    data = await state.get_data()
    member_tg_id = data['ID']
    registrator_tg_id = callback.from_user.id

    try:
        ans_str = await new_status_tg(registrator_tg_id, member_tg_id, 'registrator')  # вызов функции присвоения нового статуса
        if isinstance(ans_str, str) and 'Ошибка' in ans_str:
            await callback.message.edit_text(text=f'Произошла ошибка: {ans_str}')
            return

        # Завершаем машину состояний
        await state.clear()
        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.edit_text(
            text='Спасибо! Регистратор добавлен!\n\n'
                 'Вы вышли из машины состояний'
        )
    except Exception as e:
        logging.error(f"Ошибка при назначении регистратора: {e}")
        await callback.message.edit_text(text=f'Произошла ошибка: {str(e)}')

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕВЕРНО"
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK),
                      F.data == 'NewRegistratorNotOK')
async def process_no_registrator_press(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Спасибо! Регистратор не добавлен!\nПопробуйте еще раз.\n'
             'Вы вышли из машины состояний'
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# модератора будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewRegistrator.fill_OK))
async def warning_registrator(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewRegistrator.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать назначение регистратора - '
             'отправьте команду /cancel'
    )

"""
Хэндлеры FSM присвоения нового статуса выбранному участнику группы
"""

# Этот хэндлер будет срабатывать на команду /new_status
# и переводить бота в состояние ожидания ввода телеграм-ID участника,
# которому меняется статус
@router.message(Command(commands='new_status'), StateFilter(default_state))
async def process_new_status(message: Message, state: FSMContext):
    await message.answer(text='''Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус''')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(FSMNewStatus.fill_ID_User)

# Этот хэндлер будет срабатывать на нажатие кнопки "новый статус" в меню админа
@router.callback_query(StateFilter(default_state),
                      F.data == 'new_status')
async def process_new_status_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(text='''Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус''')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(FSMNewStatus.fill_ID_User)

# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewStatus.fill_ID_User),
                lambda x: x.text.isdigit())
async def process_user_id_sent(message: Message, state: FSMContext):
    logging.info(f"Введенный ID пользователя: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем телеграм ID пользователя в хранилище по ключу "ID"
    await state.update_data(ID=int(message.text))
    user_tg_id = int(message.text)

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
@router.callback_query(StateFilter(FSMNewStatus.fill_OK),
                      F.data == 'ConfirmOK')
async def process_status_choice(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    data = await state.get_data()
    member_tg_id = data['ID']

    try:
        status = await extract_status_tg(member_tg_id)
        all_st = await all_status()
        vacansy = list(set(all_st) - set(status) - {'owner', 'user', 'candidate'})
        status = list(set(status) - {'owner', 'member', 'user', 'candidate'})

        keyboards = []
        for item in vacansy:
            keyboards.append('AppointAs_' + item)
        for item in status:
            keyboards.append('not_' + item)
        markup = create_inline_kb(1, *keyboards)

        await callback.message.answer(
            text='''Выберите, какой статус вы хотите добавить пользователю, или удалить.
            \nЕсли хотите прервать процедуру - наберите /cancel''',
            reply_markup=markup  # клавиатура из статусов
        )
        # Устанавливаем состояние ожидания подтверждения
        await state.set_state(FSMNewStatus.fill_choice)
    except Exception as e:
        logging.error(f"Ошибка при формировании клавиатуры статусов: {e}")
        await callback.message.edit_text(text=f'Произошла ошибка: {str(e)}')
        await state.clear()

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_OK),
                      F.data == 'ConfirmNotOK')
async def process_no_confirm_status_press(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\n'
             'Вы вышли из машины состояний'
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# данных пользователя будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_OK))
async def warning_registrator(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать назначение регистратора - '
             'отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на выбор одного из статусов (или его отмены)
@router.callback_query(StateFilter(FSMNewStatus.fill_choice))
async def process_new_status_confirm(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Выбран статус: {callback.data} пользователем {callback.from_user.id}")
    await state.update_data(status=callback.data)
    status = callback.data
    data = await state.get_data()
    member_tg_id = data['ID']

    try:
        user_data = await extract_user_data_tg(member_tg_id, 'id', 'tg_first_name', 'tg_last_name', 'tg_phone_number')  # извлекаем данные о пользователе
        status_text = LEXICON[status] if status in LEXICON else status

        await callback.message.answer(
            text=f'''Данные пользователя\nИмя: {user_data[1]},
Фамилия: {user_data[2]}, \n Телефон: {user_data[3]}
           \nВы хотите изменить его статус:
           \n{status_text}
           \nВсё верно?''',
            reply_markup=confirm_markup
        )
        await state.set_state(FSMNewStatus.fill_new_status_confirm)
    except Exception as e:
        logging.error(f"Ошибка при извлечении данных пользователя или формировании сообщения: {e}")
        await callback.message.edit_text(text=f'Произошла ошибка: {str(e)}')
        await state.clear()

# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении
# нового статуса, присваиваемого пользователю
@router.callback_query(StateFilter(FSMNewStatus.fill_new_status_confirm),
                      F.data == 'ConfirmOK')
async def process_new_status_entry(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    data = await state.get_data()
    status = data['status']
    st = status.split('_')[1] if '_' in status else status

    try:
        if st not in await all_status():
            await state.clear()
            # Отправляем в чат сообщение о выходе из машины состояний
            await callback.message.edit_text(
                text='Извините, такого статуса нет.\n\n Попробуйте снова.'
                     'Вы вышли из машины состояний')
        else:
            member_tg_id = data['ID']
            registrator_tg_id = callback.from_user.id
            ans_str = await new_status_tg(registrator_tg_id, member_tg_id, st)  # вызов функции присвоения нового статуса

            if isinstance(ans_str, str) and 'Ошибка' in ans_str:
                await callback.message.edit_text(text=f'Произошла ошибка: {ans_str}')
                return

            # Завершаем машину состояний
            await state.clear()
            # Отправляем в чат сообщение о выходе из машины состояний
            await callback.message.edit_text(
                text='Спасибо! Статус участника обновлен!\n\n'
                     'Вы вышли из машины состояний'
            )
    except Exception as e:
        logging.error(f"Ошибка при присвоении нового статуса: {e}")
        await callback.message.edit_text(text=f'Произошла ошибка: {str(e)}')
        await state.clear()

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_new_status_confirm),
                      F.data == 'ConfirmNotOK')
async def process_no_confirm_sttus_press(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\n'
             'Вы вышли из машины состояний'
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# статуса будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_new_status_confirm))
async def warning_new_status(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_new_status_confirm}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать изменение статуса - '
             'отправьте команду /cancel'
    )