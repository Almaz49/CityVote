# Модуль admin_handlers , сожержит хэндлеры для админов и владельца группы

import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import traceback
from filters.filters import StatusFilter
from FSMs.FSMs import FSMNewRegistrator, FSMNewVoting, FSMNewStatus
from data_base.telegram_bot_logic import *
from utils import log_handler_call
from services.services import send_notification_to_user
from keyboards.keyboards import *
from config_data.config import Config, load_config
from manager.manager import *

# Настройка логирования
logger = logging.getLogger(__name__)

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
#     logger.info(f"Команда /cancel сработала для пользователя {message.from_user.id} в состоянии по умолчанию")
#     await message.answer(
#         text='Отменять нечего. Вы вне машины состояний',
#         reply_markup=remove_markup
#     )

# # Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# # кроме состояния по умолчанию, и отключать машину состояний
# @router.message(Command(commands='cancel'), ~StateFilter(default_state))
# @log_handler_call
# async def process_cancel_command_state(message: Message, state: FSMContext):
#     logger.info(f"Команда /cancel сработала для пользователя {message.from_user.id} в состоянии {await state.get_state()}")
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
    logger.info(f"Команда /new_registrator сработала для пользователя {message.from_user.id}")
    await message.answer(text='''Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус или отправьте контакт с ID''')
    # Устанавливаем состояние ожидания ввода ID
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
    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMNewRegistrator.fill_ID_NewRegistrator)


# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# или отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewRegistrator.fill_ID_NewRegistrator), (lambda x: x.text.isdigit()))
@log_handler_call
async def process_registrator_id_sent(message: Message, state: FSMContext, data: dict = None):
    logger.info(f"Введенный ID нового регистратора: {message.text} от пользователя {message.from_user.id}")

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
        await state.set_state(FSMNewRegistrator.fill_OK)

    else:
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = ans_str
        data['reply_markup'] = main_menu_markup

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
    logger.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")
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
        await state.set_state(FSMNewRegistrator.fill_OK)

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
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
async def process_yes_registrator_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Меняем в базе данных статус пользователя по ключу tg_id пользователя и tg_id регистратора
    fsm_data = await state.get_data()
    member_tg_id = fsm_data['ID']
    admin_tg_id = callback.from_user.id
    admin_id = data['member_id']

    try:
        ans_str = await new_status_tg(admin_tg_id, member_tg_id, 'pre-registrator')  # Вызов функции присвоения нового статуса
        if isinstance(ans_str, str) and 'Ошибка' in ans_str:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = f'Произошла ошибка: {ans_str}'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])
            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(text=data['response_text'], reply_markup=data['reply_markup'])
            return

        # Завершаем машину состояний
        await state.clear()

        # Формируем и отправляем запрос кандидату в регистраторы - согласен ли он

        notification = 'Здравствуйте! Администрация группы назначила вас регистратором.\n' \
        'Это означает, что вам будут приходить заявки на вступления в группу, ' \
        'которые вы можете подтверждать или игнорировать.\n' \
        'Если вы согласны на роль Регистратора, нажмите кнопку "Согласен".\n' \
        'Если не согласны - кнопку "Не согласен"'

        keyboard = {f'pre_registrator_yes:{admin_id}:{member_tg_id}':'Согласен',
                    f'pre_registrator_no:{admin_id}:{member_tg_id}':'Не согласен'}

        pre_reg_markup = create_inline_kb(2, **keyboard)

        response = await send_notification_to_user(member_tg_id, notification, pre_reg_markup   )

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Спасибо! Кандидат в Регистраторы добавлен!\n' \
        'Результат отправки сообщения кандидату:\n' \
        f'{response}' \
        '\nВы вышли из машины состояний'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при назначении регистратора: {e}")
        # Необходимость явной обработки ошибок здесь минимальна,
        # так как LoggingAndErrorHandlingMiddleware уже позаботится об этом.
        raise  # Передаем исключение middleware для обработки

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕВЕРНО"
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_registrator_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
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
# регистратора будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewRegistrator.fill_OK))
@log_handler_call
async def warning_registrator(message: Message):
    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewRegistrator.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать назначение регистратора - '
             'отправьте команду /cancel'
    )


"""
Хэндлеры создани списка регистраторов (суперрегистраторов) и редактирования и статусов
"""

# Добавляем обработку нажатия кнопки "список регистраторов" в меню администратора
@router.callback_query(F.data == 'registrators_list')
@log_handler_call
async def process_registrators_list(callback: CallbackQuery, data: dict):
    logger.info(f"Пользователь {callback.from_user.id} запросил список регистраторов")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Здесь будет логика получения и отображения списка регистраторов и суперрегистраторов
    registrators = await list_of_members(data['club_id'],status='registrator')  # Функция для получения списка регистраторов
    super_registrators = await list_of_members(data['club_id'], status='superregistrator')  # Функция для получения списка суперhегистраторов

    if not registrators and not super_registrators:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'В данный момент нет регистраторов.'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

    for registrator in registrators:
        # Отправляем сообщение про каждого регистратора
        await callback.message.answer(
            text=(f"Регистратор: {registrator['username']} {registrator['first_name'] if registrator['first_name'] else ''} "
                  f"{registrator['last_name'] if registrator['last_name'] else ''}"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Удалить из регистраторов", callback_data=f"remove_registrator:{registrator['member_id']}")],
                [InlineKeyboardButton(text="Сделать суперрегистратором", callback_data=f"promote_to_super:{registrator['member_id']}")]
            ])
        )

    for super_registrator in super_registrators:
        # Отправляем сообщение про каждого суперрегистратора
        await callback.message.answer(
            text=(f"Суперегистратор: {super_registrator['username']} \n{super_registrator['first_name'] if super_registrator['first_name'] else ''} "
                  f"{super_registrator['last_name'] if super_registrator['last_name'] else ''}"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Удалить из суперрегистраторов", callback_data=f"remove_superregistrator:{super_registrator['member_id']}")],
                [InlineKeyboardButton(text="Разжаловать в простые регистраторы", callback_data=f"demote_to_registrator:{super_registrator['member_id']}")]
            ])
        )
    await callback.message.answer(
        text="Вернуться в основное меню",
        reply_markup=return_to_main_menu_markup
        )


@router.callback_query(F.data.regexp(r'^remove_registrator:\d+$'))
@log_handler_call
async def process_remove_registrator(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления регистратора
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} удалаяет регистратора: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = int(callback.data.split(':')[1])
        registrator = callback.from_user.id

        result1 = await new_status(registrator=registrator,member_id=member_id,status='not_registrator')

        if result1:
            success1,text = result1


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
        logger.error(f"Ошибка при удалении регистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при удалении регистратора.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r'^promote_to_super:\d+$'))
@log_handler_call
async def process_promote_to_super(callback: CallbackQuery, data: dict):
    """
    Обработчик назначения суперрегистратора
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} делает регистратора суперрегистратором: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = int(callback.data.split(':')[1])
        registrator = callback.from_user.id

        result1 = await new_status(registrator=registrator,member_id=member_id,status='superregistrator')

        if result1:
            success1,text = result1

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
        logger.error(f"Ошибка при  назначениии суперрегистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при назначении суперрегистратора.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

@router.callback_query(F.data.regexp(r'^remove_superregistrator:\d+$'))
@log_handler_call
async def process_remove_superregistrator(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления суперрегистратора
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} удалаяет суперрегистратора: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = int(callback.data.split(':')[1])
        registrator = callback.from_user.id

        result1 = await new_status(registrator=registrator,member_id=member_id,status='not_superregistrator')
        print(result1)

        if result1:
            success1,text = result1


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
        logger.error(f"Ошибка при удалении суперрегистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при удалении суперрегистратора.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r'^demote_to_registrator:\d+$'))
@log_handler_call
async def process_demote_to_registrator(callback: CallbackQuery, data: dict):
    """
    Обработчик разжалования суперрегистратора в регистраторы
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} разжалует суперрегистратора в регистраторы: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = int(callback.data.split(':')[1])
        registrator = callback.from_user.id

        result1 = await new_status(registrator=registrator,member_id=member_id,status='not_superregistrator')
        result2 = await new_status(registrator=registrator,member_id=member_id,status='registrator')

        if result1:
            success1,text1 = result1
        if result2:
            success2,text2 = result2

        text = f"{text1}\n{text2}"


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
        logger.error(f"Ошибка при удалении регистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при удалении регистратора.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


"""
Администрирование голосования
"""

# Хэндлер для обработки кнопки "администрирование голосования"
# callback.data 'admin_voting':{voting_id}
@router.callback_query(F.data.regexp(r'^admin_voting:\d+$'))
@log_handler_call
async def process_admin_voting_cb(callback: CallbackQuery, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} запустил администрирование голосвания: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        voting_status = await extract_voting_status(voting_id)
        variants = await list_of_variants(voting_id, 'valid')
        if variants:
            amount = len(variants)
        else:
            amount = 0
        if amount == 2:
            voting_status = 'final'

        dict_menu = {}
        if voting_status == 'add_variants':
            dict_menu[f'voting_start:{voting_id}'] = LEXICON.get('voting_start', 'voting_start')
            dict_menu[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
        # Пока не пишу восстановление голосования - слоишком сложно "проворачивать фарш назад"
        # elif voting_status == 'completed':
        #     dict_menu[f'voting_reopen:{voting_id}'] = LEXICON.get('reopen', 'reopen')
        elif voting_status == 'ongoing':
            dict_menu[f'voting_stage:{voting_id}'] = LEXICON.get('voting_stage', 'voting_stage')
            dict_menu[f'voting_final:{voting_id}'] = LEXICON.get('voting_final', 'voting_final')
            dict_menu[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
        elif voting_status == 'final':
            dict_menu[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')
        elif voting_status =='confirmation':
            dict_menu[f'voting_complete:{voting_id}'] = LEXICON.get('voting_complete', 'voting_complete')


        dict_menu['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')

        logger.info(f'словарь меню при показе вариантов: {dict_menu}')
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
        logger.error(f"Ошибка при просмотре вариантов голосования: {e}")

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
        logger.info(f"Пользователь {callback.from_user.id} запускает голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await voting_manager(voting_id, club_id=club_id, admin=member_id, stage_type='start')



        if result:
            text = result.get('message')
            logger.info(text)
        else:
            text = 'Что-то пошло не так при запуске голосования'
            logger.info(text+f':{voting_id}')

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
        logger.error(f"Ошибка при запуске голосования: {e}")

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
    Обработчик нажатия кнопки старта промежуточного этапа голосования.
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} запускает промежуточный этап голосования: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await voting_manager(voting_id, club_id=club_id, admin=member_id, stage_type='stage')



        if result:
            text = result.get("message")
            logger.info(text)
        else:
            text = 'Что-то пошло не так при подведении промежуточного итога голосования'
            logger.info(text+f':{voting_id}')

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
        logger.error(f"Ошибка при запуске голосования: {e}")

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
        logger.info(f"Пользователь {callback.from_user.id} запускает финальный этап голосования: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await voting_manager(voting_id, club_id=club_id, admin=member_id, stage_type='final')



        if result:
            text = result.get('message')
            logger.info(f'Сообщение о результате перехода в финал: {text}')
        else:
            text = 'Что-то пошло не так при подведении промежуточного итога голосования'
            logger.info(text+f':{voting_id}')

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
        logger.error(f"Ошибка при запуске голосования: {e}")

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
        logger.info(f"Пользователь {callback.from_user.id} завершает голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await voting_manager(voting_id, club_id=club_id, admin=member_id, stage_type='complete')
        if result:
            text = result.get('message')
            logger.info(f'Сообщение о завершении голосования: {text}')
        else:
            text = 'Что-то пошло не так при завершении голосования'
            logger.info(text+f':{voting_id}')

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
        logger.error(f"Ошибка при запуске голосования: {e}")

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
@router.callback_query(F.data.regexp(r'^delete_variant:\d+$'))
@log_handler_call
async def process_delete_variant_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления варианта
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} удалаяет вариант: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        variant_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await delete_variant(variant_id, admin=member_id)
        if result:
            text = result[0]
            logger.info(text)
        else:
            text = 'Что-то пошло не так при удалении варианта'
            logger.info(text+f':{variant_id}')

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
        logger.error(f"Ошибка при удалении варианта: {e}")

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
async def process_stop_confirmation_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик завершения утверждения голосования (то есть, последне стадии).
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} завершает голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        club_id = data['club_id']

        result = await confirmation_of_voting_results_stop (voting_id, finisher=member_id)
        if result:
            text = result[0]
            logger.info(text)
        else:
            text = 'Что-то пошло не так при завершении утверждения голосования'
            logger.info(text+f':{voting_id}')

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
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при запуске голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки
