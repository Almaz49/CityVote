from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize, Contact)
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from filters.filters import StatusFilter
from LEXICON.LEXICON import LEXICON
from FSMs.FSMs import FSM_become_proxy, FSM_appoint_deputy, FSM_leave_club, FSM_become_registrator
from services.services import not_votist_because_proxy_quit, votist_because_proxy_returned
from keyboards.keyboards import (reg_markup, contact_markup, remove_markup, user_menu,
            create_inline_kb, confirm_markup, return_to_main_menu_markup)
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import *
import logging
from utils import log_handler_call

# Настройка логирования
logger = logging.getLogger(__name__)

# # Инициализируем бота
# # Загружаем конфиг в переменную config
# config: Config = load_config('.env')
# bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status = ['member']))
router.callback_query.filter(StatusFilter(required_status = ['member']))


# Хэндлер для выбора конкретного варианта при голосовании
@router.callback_query(F.data.regexp(r'^variant:\d+$'))
@log_handler_call
async def process_variant_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного варианта голосования.
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} выбрал вариант: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        variant_id = int(callback.data.split(':')[1])
        member_id = data['member_id']
        success, message = await election(member_id, variant_id)

        if success:
            text = f'{message}\n\nВоспользуйтесь кнопками под последним сообщением для дальнейших действий'
        else:
            text = f'Ошибка при голосовании: {message}'

        # markup = create_inline_kb(1, 'main_menu')

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = None # markup

        # Отправляем ответ
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при выборе конкретного варианта голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при голосовании.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Отправляем новое сообщение в случае ошибки
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки




# Хэндлер для кнопки 'select_proxy' обычным участником
@router.callback_query(F.data == 'select_proxy', ~StatusFilter(required_status = ['proxy']))
@log_handler_call
async def process_select_proxy(callback: CallbackQuery, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} запросил список представителей.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        members = await list_of_members_tg('proxy')

        if not members:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'В данный момент нет доступных представителей.'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return


        # Создаем кнопки для каждого представителя, текст - его username в группе (не телеграм) или Имя Фамилия, callback-data - телеграм ID
        proxy_buttons = {}
        for member in members:
            proxy_buttons[f'trust:{member[2]}'] = f'{member[5]}' if member[5] else  f"{member[0]} {member[1]}"

        # # Смотрим, нет ли дубликатов (полных тезок среди представителей)
        # # Создаем словарь для подсчёта частоты встречаемости значений
        # value_counts = {}

        # # Подсчитываем частоту каждого значения
        # for value in proxy_buttons.values():
        #     if value in value_counts:
        #         value_counts[value] += 1
        #     else:
        #         value_counts[value] = 1

        # # Находим значения, которые встречаются более одного раза
        # duplicates = [key for key, count in value_counts.items() if count > 1]





        # Создаем инлайн-клавиатуру с кнопками
        markup = create_inline_kb(1,**proxy_buttons)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Выберите представителя, которому вы доверите свой голос:'
        data['reply_markup'] = markup

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка представителей.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для кнопки 'select_proxy' представителем (выбор заместителя)
@router.callback_query(F.data == 'select_proxy', StatusFilter(required_status = ['proxy']), StateFilter(default_state))
@log_handler_call
async def process_select_deputy(callback: CallbackQuery, data: dict, state: FSMContext):
    try:
        logger.info(f"Представитеь {callback.from_user.id} хочет выбрать заместителя.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = '''Пожалуйста, введите телеграм-ID участника,
    которого вы хотите псделать своим заместителем или отправьте контакт с ID'''
        data['reply_markup'] = None  # Если клавиатура не нужна, устанавливаем None

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        # Устанавливаем состояние ожидания ввода ID
        await state.set_state(FSM_appoint_deputy.fill_id)
        logger.info(f"Установлено состояние: {await state.get_state()}")

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка представителей.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для доверия голоса
@router.callback_query(F.data.startswith('trust:'), ~StatusFilter(required_status = ['proxy']))
@log_handler_call
async def process_trust(callback: CallbackQuery, data: dict):
    try:
        proxy_tg_id = int(callback.data.split(':')[1])
        logger.info(f"Пользователь {callback.from_user.id} доверил свой голос пользователю с tg_id {proxy_tg_id}.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        flag, ans_str = await trust_tg(callback.from_user.id, proxy_tg_id)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = ans_str
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при доверии голоса: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при доверии голоса.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для выбора заместителя представителем
@router.message(
    StatusFilter(required_status=['proxy']),
    StateFilter(FSM_appoint_deputy.fill_id),
    F.text.isdigit() | F.contact
)
@log_handler_call
async def process_appoint_deputy(message: Message, data: dict, state: FSMContext):
    try:
        if message.contact:
            deputy_tg_id = message.contact.user_id
        else:
            deputy_tg_id = int(message.text)
        logger.info(f"Представитель {message.from_user.id} выбрал своим заместителем пользователя с tg_id {deputy_tg_id}.")

        flag, ans_str = await trust_tg(message.from_user.id, deputy_tg_id)
        if not ans_str:
            ans_str = "Неизвестная ошибка при назначении заместителя."

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = ans_str
        data['reply_markup'] = await user_menu(message.from_user.id, data['user_status'])

        # Отвечаем
        await message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при выборе  заместителя: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при выборе заместителя.'
        data['reply_markup'] = await user_menu(message.from_user.id, data['user_status'])

        # Отправляем сообщение в случае ошибки
        await message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )
        await state.clear()

        raise


# Хэндлер для кнопки 'become_proxy'
@router.callback_query(F.data == 'become_proxy', StateFilter(default_state))
@log_handler_call
async def process_become_proxy(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} запросил статус 'proxy'.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = data['member_id']
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь участником группы.'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        if 'proxy' in data['user_status']:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы уже являетесь представителем'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        columns = ('username',)
        username, = await extract_user_data(data['user_id'], *columns)
        if username:
            # Присваиваем статус 'proxy'
            await new_status(member_id, member_id, 'proxy')
            # Присваиваем статус 'votist' (если его не было)
            await new_status(member_id,member_id,'votist')
            # Присваем статус 'votist' тем, кто каким-то образом уже доверил ему голос
            await votist_because_proxy_returned(member_id)

            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы стали представителем!'
            data['reply_markup'] = await user_menu(callback.from_user.id)

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            await state.clear()
        else:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = (
                'Введите уникальное имя или псевдоним.'
                'Это может быть ваше собственное имя (фамилия).'
                'Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей.'
                'И желательно не длиннее 40 символов'
            )
            data['reply_markup'] = None

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

            await state.set_state(FSM_become_proxy.fill_username)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'become_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при присвоении статуса представителя.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )
        await state.clear()

        raise  # Передаем исключение middleware для обработки


# Хэндлер будет обрабатывать ввод username представителя
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSM_become_proxy.fill_username))
@log_handler_call
async def process_username_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода имени/псевдонима.
    Запрашивает подтверждение.
    """
    logger.info(f"Пользователь {message.from_user.id} ввел свой псевдоним: {message.text}.")
    flag = await is_username_uniq(message.text)
    if flag:
        await state.update_data(username = message.text)
        # Отправляем сообщение с подтверждением
        await message.answer(
            text=f'''Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?
    {message.text}''',
            reply_markup=confirm_markup
        )
        await state.set_state(FSM_become_proxy.fill_OK)
    else:
        await message.answer(
            text='Такое имя/псевдоним уже есть. Попрбуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас'
        )


# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении username

@router.callback_query(StateFilter(FSM_become_proxy.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
async def process_username_entry(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' при подтверждении username нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    username = fsm_data['username']
    user_id = data['user_id']
    member_id = data['member_id']

    try:
        # Записываем username в базу данных
        await db_update('Users', 'id', user_id, username=username)
        # Присваиваем статус 'proxy'
        await new_status(member_id, member_id, 'proxy')
        # Присваиваем статус 'votist' (если его не было)
        await new_status(member_id,member_id,'votist')
        # Присваем статус 'votist' тем, кто каким-то образом уже доверил ему голос
        await votist_because_proxy_returned(member_id)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Вы стали представителем!'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )


        # Завершаем машину состояний
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при записи username: {e}")

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
@router.callback_query(StateFilter(FSM_become_proxy.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_proxy_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"


    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Псевдоним не доавлен\nПопробуйте еще раз, или нажмите кнопку для прерывания процедуры'
    data['reply_markup'] = return_to_main_menu_markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    await state.set_state(FSM_become_proxy.fill_username)


# Этот хэндлер будет срабатывать, если во время подтверждения
# статуса будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSM_become_proxy.fill_OK))
@log_handler_call
async def warning_new_status(message: Message):
    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSM_become_proxy.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать изменение статуса - '
             'отправьте команду /cancel'
    )



# Хэндлер для кнопки ''resign_from_proxy''
@router.callback_query(F.data == 'resign_from_proxy')
@log_handler_call
async def process_resign_from_proxy(callback: CallbackQuery, data: dict):

    logger.info(f"Пользователь {callback.from_user.id} отказывается от статуса 'proxy'.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    member_id = data['member_id']
    if not member_id:
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Вы не являетесь участником группы.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )
        return

    # Убираем статус 'proxy'
    await new_status(member_id, member_id, 'not_proxy')
    await not_votist_because_proxy_quit(member_id)
    flag = await is_votist(member_id)
    text = 'Вы перестали быть представителем!'
    if not flag:
        text = '\nВам требуется выбрать себе представителя, чтобы иметь право голосовать'



    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = text
    data['reply_markup'] = await user_menu(callback.from_user.id)

    # Редактируем сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )




# Хэндлер для кнопки 'resign_from_registrator'
# Удаляет статус регистратора  или кандидата в регистраторы при отказе быть регистратором
@router.callback_query(F.data == 'resign_from_registrator')
@log_handler_call
async def process_resign_from_registrator(callback: CallbackQuery, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} отказывается от статуса 'registrator'.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = data['member_id']
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь участником группы.'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        # Убираем статус 'registrator'
        await new_status(member_id, member_id, 'not_registrator') # Для регистратора
        await new_status(member_id, member_id, 'not_pre-registrator') # Для кандидата в регистраторы
        text = 'Вы отказались от роли регистратора!'




        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'resign_from_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при удалении статуса представителя.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для кнопки 'resign_from_admin'
# Удаляет статус администратора при отказе быть администратором
@router.callback_query(F.data == 'resign_from_admin')
@log_handler_call
async def process_resign_from_registrator(callback: CallbackQuery, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} отказывается от статуса 'admin'.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = data['member_id']
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь участником группы.'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        # Убираем статус 'registrator'
        await new_status(member_id, member_id, 'not_admin')
        text = 'Вы отказались от роли администратора!'




        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'resign_from_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при удалении статуса администратора.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для согласия стать регистратором (кнопки pre_registrator_yes: )
@router.callback_query(F.data.regexp(r'^pre_registrator_yes:\d+:\d+$'), StateFilter(default_state))
@log_handler_call
async def process_become_registrator(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} дал согласие стать регистратором.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        # Разбираем callback_data на части
        action, admin_id, member_tg_id = callback.data.split(':')

        # Преобразуем ID в целые числа
        admin_id = int(admin_id)
        member_tg_id = int(member_tg_id)

        member_id = data['member_id']

        # Проверяем, что отправитель коллбэка и кандидат в регистраторы - один и тот же аккаунт
        if callback.from_user.id != member_tg_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Предложение стать регистратором предназначалось не вам'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь участником группы.'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        if 'registrator' in data['user_status']:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы уже являетесь регистратором'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        if 'pre-registrator' not in data['user_status']:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь кандидатом в регистраторы'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        # Переходим к обработке запроса. Проверяем, есть ли у кандидата псевдоним
        columns = ('username',)
        username, = await extract_user_data(data['user_id'], *columns)
        # Если есть псевдоним - записываем новый статус
        if username:
            # Присваиваем статус 'registrator'
            await new_status(member_id, member_id, 'registrator')
            # Удаляем статус 'pre-registrator'
            await new_status(member_id,member_id,'not_pre-registrator')

            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы стали регистратором!'
            data['reply_markup'] = await user_menu(callback.from_user.id)

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            await state.clear()
        # Если нет псевдонима, просим его создать
        else:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = (
                'Введите уникальное имя или псевдоним.'
                'Это может быть ваше собственное имя (фамилия).'
                'Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей.'
                'И желательно не длиннее 40 символов'
            )
            data['reply_markup'] = None

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

            await state.set_state(FSM_become_registrator.fill_username)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'pre_registrator_yes': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при присвоении статуса регистратора.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )
        await state.clear()

        raise  # Передаем исключение middleware для обработки

# Хэндлер для позднего согласия стать регистратором (кнопка основного меню become_registrator: )
@router.callback_query(F.data == 'become_registrator', StateFilter(default_state))
@log_handler_call
async def process_become_registrator_own(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} дал согласие стать регистратором.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = data['member_id']
        status = data['user_status']


        if 'registrator' in status:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы уже являетесь регистратором'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        if 'pre-registrator' not in status:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь кандидатом в регистраторы'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        # Переходим к обработке запроса. Проверяем, есть ли у кандидата псевдоним
        columns = ('username',)
        username, = await extract_user_data(data['user_id'], *columns)
        # Если есть псевдоним - записываем новый статус
        if username:
            # Присваиваем статус 'registrator'
            await new_status(member_id, member_id, 'registrator')
            # Удаляем статус 'pre-registrator'
            await new_status(member_id,member_id,'not_pre-registrator')

            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы стали регистратором!'
            data['reply_markup'] = await user_menu(callback.from_user.id)

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            await state.clear()
        # Если нет псевдонима, просим его создать
        else:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = (
                'Введите уникальное имя или псевдоним.'
                'Это может быть ваше собственное имя (фамилия).'
                'Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей.'
                'И желательно не длиннее 40 символов'
            )
            data['reply_markup'] = None

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

            await state.set_state(FSM_become_registrator.fill_username)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'pre_registrator_yes': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при присвоении статуса представителя.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )
        await state.clear()

        raise  # Передаем исключение middleware для обработки

# Хэндлер для отказа стать регистратором (кнопки pre_registrator_no: )
@router.callback_query(F.data.regexp(r'^pre_registrator_no:\d+:\d+$'), StateFilter(default_state))
@log_handler_call
async def process_not_become_registrator(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} не дал согласие стать регистратором.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        # Разбираем callback_data на части
        action, admin_id, member_tg_id = callback.data.split(':')

        # Преобразуем ID в целые числа
        member_tg_id = int(member_tg_id)

        member_id = data['member_id']

        # Проверяем, что отправитель коллбэка и кандидат в регистраторы - один и тот же аккаунт
        if callback.from_user.id != member_tg_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Предложение стать регистратором предназначалось не вам'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь участником группы.'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        if 'pre-registrator' not in data['user_status']:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь кандидатом в регистраторы'
            data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        # Удаляем статус 'pre-registrator'
        await new_status(member_id,member_id,'not_pre-registrator')

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Вы не стали регистратором!'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )


    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'pre_registrator_no': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при присвоении статуса представителя.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )
        await state.clear()

        raise  # Передаем исключение middleware для обработки

# Хэндлер будет обрабатывать ввод username регистратора
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSM_become_registrator.fill_username))
@log_handler_call
async def process_reg_username_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода имени/псевдонима.
    Запрашивает подтверждение.
    """
    logger.info(f"Пользователь {message.from_user.id} ввел свой псевдоним: {message.text}.")
    flag = await is_username_uniq(message.text)
    if flag:
        await state.update_data(username = message.text)
        # Отправляем сообщение с подтверждением
        await message.answer(
            text=f'''Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?
    {message.text}''',
            reply_markup=confirm_markup
        )
        await state.set_state(FSM_become_registrator.fill_OK)
    else:
        await message.answer(
            text='Такое имя/псевдоним уже есть. Попрбуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас'
        )


# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении username

@router.callback_query(StateFilter(FSM_become_registrator.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
async def process_reg_username_entry(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' при подтверждении username нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    username = fsm_data['username']
    user_id = data['user_id']
    member_id = data['member_id']


    try:
        # Записываем username в базу данных
        await db_update('Users', 'id', user_id, username=username)
        # Присваиваем статус 'registrator'
        await new_status(member_id, member_id, 'registrator')
        # Удаляем статус 'pre-registrator'
        await new_status(member_id,member_id,'not_pre-registrator')

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Вы стали регистратором!'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )


        # Завершаем машину состояний
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при записи username: {e}")

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
@router.callback_query(StateFilter(FSM_become_registrator.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_registrator_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"


    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Псевдоним не доавлен\nПопробуйте ввести псевдоним еще раз, или нажмите кнопку для прерывания процедуры'
    data['reply_markup'] = return_to_main_menu_markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    await state.set_state(FSM_become_registrator.fill_username)


# Этот хэндлер будет срабатывать, если во время подтверждения
# статуса будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSM_become_proxy.fill_OK))
@log_handler_call
async def warning_new_status(message: Message):
    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSM_become_proxy.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать процедуру - '
             'отправьте команду /cancel'
    )