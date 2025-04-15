# Модуль admin_handlers , сожержит хэндлеры для админов и владельца группы

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
router.message.filter(StatusFilter(required_status = ['admin','owner']))
router.callback_query.filter(StatusFilter(required_status = ['admin','owner']))

# # Этот хэндлер будет срабатывать на команду "/cancel" в состоянии по умолчанию
# # и сообщать, что эта команда работает внутри машины состояний
# @router.message(Command(commands='cancel'), StateFilter(default_state))
# @log_handler_call
# async def process_cancel_command(message: Message):
#     logging.info(f"Команда /cancel сработала для пользователя {message.from_user.id} в состоянии по умолчанию")
#     await message.answer(
#         text='Отменять нечего. Вы вне машины состояний',
#         reply_markup=remove_markup
#     )

# # Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# # кроме состояния по умолчанию, и отключать машину состояний
# @router.message(Command(commands='cancel'), ~StateFilter(default_state))
# @log_handler_call
# async def process_cancel_command_state(message: Message, state: FSMContext):
#     logging.info(f"Команда /cancel сработала для пользователя {message.from_user.id} в состоянии {await state.get_state()}")
#     await message.answer(
#         text='Вы вышли из машины состояний',
#         reply_markup=await user_menu(message.from_user.id)
#     )
#     # Сбрасываем состояние и очищаем данные, полученные внутри состояний
#     await state.clear()

"""
Хэндлеры FSM создания нового регистратора
"""
# Этот хэндлер будет срабатывать на команду /new_registrator
# и переводить бота в состояние ожидания ввода ID нового регистратора
@router.message(Command(commands='new_registrator'), StateFilter(default_state))
@log_handler_call
async def process_new_registrator(message: Message, state: FSMContext):
    logging.info(f"Команда /new_registrator сработала для пользователя {message.from_user.id}")
    await message.answer(text='''Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус или отправьте контакт с ID''')
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(FSMNewRegistrator.fill_ID_NewRegistrator)


# Этот хэндлер будет срабатывать на нажатие кнопки "новый регистратор" в меню админа
@router.callback_query(StateFilter(default_state), F.data == 'new_registrator')
@log_handler_call
async def process_new_registrator_cb(callback: CallbackQuery, state: FSMContext, data: dict):
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


# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# или отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewRegistrator.fill_ID_NewRegistrator), (lambda x: x.text.isdigit()))
@log_handler_call
async def process_registrator_id_sent(message: Message, state: FSMContext, data: dict = None):
    logging.info(f"Введенный ID нового регистратора: {message.text} от пользователя {message.from_user.id}")

    member_tg_id = int(message.text)
    await state.update_data(ID=member_tg_id)

    flag, ans_str = await extract_new_registrator_data(member_tg_id)  # извлекаем данные о новом регистраторе

    # Создаем объект инлайн-клавиатуры
    markup = confirm_markup

    if flag:
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Данные участника, которого вы назначаете регитратором:\n{ans_str}\nВсё верно?'
        data['reply_markup'] = markup

        # Отправляем пользователю сообщение с клавиатурой
        await message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        # Устанавливаем состояние ожидания подтверждения
        await state.set_state(FSMNewStatus.fill_OK)

    else:
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = ans_str
        data['reply_markup'] = None  # Клавиатура не нужна

        # Отправляем сообщение об ошибке
        await message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        # Сбрасываем состояние и очищаем данные
        await state.clear()

# Этот хэндлер будет срабатывать, если  отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewRegistrator.fill_ID_NewRegistrator), F.contact)
@log_handler_call
async def process_registrator_contact_sent(message: Message, state: FSMContext, data, contact: Contact = None):

    contact = message.contact
    logging.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")
    member_tg_id = contact.user_id

    flag, ans_str = await extract_new_registrator_data(member_tg_id)  # извлекаем данные о новом регистраторе

    # Создаем объект инлайн-клавиатуры
    markup = confirm_markup

    if flag:
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f'Данные участника, которого вы назначаете регитратором:\n{ans_str}\nВсё верно?'
        data['reply_markup'] = markup

        # Отправляем пользователю сообщение с клавиатурой
        await message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        # Устанавливаем состояние ожидания подтверждения
        await state.set_state(FSMNewStatus.fill_OK)

    else:
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = ans_str
        data['reply_markup'] = None  # Клавиатура не нужна

        # Отправляем сообщение об ошибке
        await message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        # Сбрасываем состояние и очищаем данные
        await state.clear()


# Хэндлер для обработки нажатии кнопки ВСЁ ВЕРНО
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK), F.data == 'NewRegistratorOK')
@log_handler_call
async def process_yes_registrator_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Меняем в базе данных статус пользователя по ключу tg_id пользователя и tg_id регистратора
    fsm_data = await state.get_data()
    member_tg_id = fsm_data['ID']
    registrator_tg_id = callback.from_user.id

    try:
        ans_str = await new_status_tg(registrator_tg_id, member_tg_id, 'registrator')  # Вызов функции присвоения нового статуса
        if isinstance(ans_str, str) and 'Ошибка' in ans_str:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = f'Произошла ошибка: {ans_str}'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])
            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(text=data['response_text'], reply_markup=data['reply_markup'])
            return

        # Завершаем машину состояний
        await state.clear()

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Спасибо! Регистратор добавлен!\n\nВы вышли из машины состояний'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при назначении регистратора: {e}")
        # Необходимость явной обработки ошибок здесь минимальна,
        # так как LoggingAndErrorHandlingMiddleware уже позаботится об этом.
        raise  # Передаем исключение middleware для обработки

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕВЕРНО"
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK), F.data == 'NewRegistratorNotOK')
@log_handler_call
async def process_no_registrator_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Регистратор не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний'
    data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Этот хэндлер будет срабатывать, если во время подтверждения
# модератора будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewRegistrator.fill_OK))
@log_handler_call
async def warning_registrator(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewRegistrator.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать назначение регистратора - '
             'отправьте команду /cancel'
    )




# # Хэндлер для администрирования конкретного голосования
# @router.callback_query(F.data.regexp(r'^admin_voting:\d+$'))
# @log_handler_call
# async def process_admin_voting(callback: CallbackQuery, data: dict):
#     """
#     Обработчик вызова меню администрирования конкретного голосования.
#     """
#     try:
#         logging.info(f"Пользователь {callback.from_user.id} выбрал голосование для администрирования: {callback.data}")
#         await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

#         voting_id = int(callback.data.split(':')[1])
#         variants = await list_of_variants(voting_id, 'valid')
#         voting_status = await extract_voting_status(voting_id)
#         dict_keyboard = {f'back_to_votings:{voting_status}':LEXICON.get('back_to_votings','back_to_votings')}

# # Добавляю кнопки в зависимости от статуса голосования и числа вариантов
#         if voting_status == 'add_variants':
#             if len(variants) < 2:
#                 text = 'Это голосование в стадии добавления вариантов. У него пока менее двух вариантов. Вы можете добавить еще варианты либо завершить его'
#                 if 'delegate' in data['user_status']:
#                     dict_keyboard[f'create_variant:{voting_id}'] = LEXICON.get('create_variant', 'create variant')
#                     dict_keyboard[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
#             else:
#                 text = 'Это голосование в стадии добавления вариантов. Вы можете добавить вариант или запустить его'
#                 dict_keyboard[f'create_variant:{voting_id}'] = LEXICON.get('create_variant', 'create variant')
#                 dict_keyboard[f'voting_start:{voting_id}'] = LEXICON.get('voting_start','voting_start')
#                 dict_keyboard[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
#         elif voting_status == 'ongoing':
#             if len(variants) > 2:
#                 text = 'Это идущее голосование. Можете перевести его в финал, оставив два варианта'
#                 dict_keyboard[f'voting_final:{voting_id}'] = LEXICON.get('voting_final','voting_final')
#                 if len(variants) > 3:
#                     text = 'Это идущее голосование. Можете подвести промежуточный итог, либо сразу запустить финальный этап, оставив два варианта'
#                     dict_keyboard[f'voting_stage:{voting_id}'] = LEXICON.get('voting_stage','voting_stage')
#                 dict_keyboard[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
#             else:
#                 text = 'это голосование в финальной стадии. Можете завершить его'
#                 dict_keyboard[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')


#         elif voting_status == 'confirmation':
#             text = 'Это голосование в стадии утверждения результата. Вы можете завершить его'
#             dict_keyboard[f'confirmation_of_voting_results_stop:{voting_id}'] = LEXICON.get('confirmation_of_voting_results_stop',
#                                                                                       'confirmation of voting results stop')

#         elif voting_status == 'completed':
#             text = 'Это завершенное голосование. Вы можете возобновить голосование за него. Отданные ранее голоса сохранятся'
#             dict_keyboard[f'continue_voting{voting_id}'] = LEXICON.get('continue_voting','continue_voting')

#         logging.info(f'словарь для клавиатуры вариантов: {dict_keyboard}')
#         markup = create_inline_kb(1, **dict_keyboard)


#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = text
#         data['reply_markup'] = markup

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#     except Exception as e:
#         logging.error(f"Ошибка при создании меню администрирования голосования: {e}")

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = 'Произошла ошибка при администрировании голосования.'
#         data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#         raise  # Передаем исключение middleware для обработки


# Хэндлер для обработки кнопки "администрирование голосования"
# callback.data 'admin_voting':{voting_id}
@router.callback_query(F.data.regexp(r'^admin_voting:\d+$'))
@log_handler_call
async def process_admin_voting_cb(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запустил администрирование голосвания: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        voting_status = await extract_voting_status(voting_id)

        dict_menu = {}
        if voting_status == 'add_variants':
            dict_menu[f'voting_start:{voting_id}'] = LEXICON.get('voting_start', 'voting_start')
            dict_menu[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
        elif voting_status == 'completed':
            dict_menu[f'reopen:{voting_id}'] = LEXICON.get('reopen', 'reopen')
        elif voting_status == 'ongoing':
            dict_menu[f'voting_stage:{voting_id}'] = LEXICON.get('voting_stage', 'voting_stage')
            dict_menu[f'voting_final:{voting_id}'] = LEXICON.get('voting_final', 'voting_final')
            dict_menu[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
        elif voting_status =='confirmation':
            dict_menu[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')


        dict_menu['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')

        logging.info(f'словарь меню при показе вариантов: {dict_menu}')
        markup = create_inline_kb(1, **dict_menu)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Выберите действие'
        data['reply_markup'] = markup

        # Отправляем или редактируем сообщение
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при просмотре вариантов голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при просмотре вариантов голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для запуска голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r'^voting_start:\d+$'))
@log_handler_call
async def process_voting_start_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} запускает голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']

        result = await voting_start(voting_id,starter=member_id)



        if result:
            flag, text = result
            logging.info(text)
        else:
            text = 'Что-то пошло не так при запуске голосования'
            logging.info(text+f':{voting_id}')

        markup = await user_menu(status=data['user_status'])

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при запуске голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для промежуточного итога голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r'^voting_stage:\d+$'))
@log_handler_call
async def process_voting_stage_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} запускает промежуточный этап голосования: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await voting_stage(voting_id, club_id=club_id, stager=member_id)



        if result:
            flag, text = result
            logging.info(text)
        else:
            text = 'Что-то пошло не так при подведении промежуточного итога голосования'
            logging.info(text+f':{voting_id}')

        markup = await user_menu(status=data['user_status'])

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при запуске голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для перехода в финал голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r'^voting_final:\d+$'))
@log_handler_call
async def process_voting_final_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик перехода в финал конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} запускает финальный этап голосования: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await voting_final(voting_id, finaler=member_id)



        if result:
            flag, text,winners,losers = result
            logging.info(text)
        else:
            text = 'Что-то пошло не так при подведении промежуточного итога голосования'
            logging.info(text+f':{voting_id}')

        markup = await user_menu(status=data['user_status'])

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при запуске голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для завершения голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r'^voting_complete:\d+$'))
@log_handler_call
async def process_voting_complete_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} завершает голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await voting_complete(voting_id, finisher=member_id)
        if result:
            text = result[0]
            logging.info(text)
        else:
            text = 'Что-то пошло не так при завершении голосования'
            logging.info(text+f':{voting_id}')

        markup = await user_menu(status=data['user_status'])

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при запуске голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для снятия варианта после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r'^voting_complete:\d+$'))
@log_handler_call
async def process_delete_variant_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} удалаяет вариант: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        variant_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await delete_variant(variant_id, admin=member_id)
        if result:
            text = result[0]
            logging.info(text)
        else:
            text = 'Что-то пошло не так при удалении варианта'
            logging.info(text+f':{variant_id}')

        markup = None

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при удалении варианта: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при удалении варианта.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для завершения утверждения голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r'^confirmation_of_voting_results_stop:\d+$'))
@log_handler_call
async def confirmation_of_voting_results_stop_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} завершает голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await confirmation_of_voting_results_stop (voting_id, finisher=member_id)
        if result:
            text = result[0]
            logging.info(text)
        else:
            text = 'Что-то пошло не так при завершении утверждения голосования'
            logging.info(text+f':{voting_id}')

        markup = await user_menu(status=data['user_status'])

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при запуске голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки