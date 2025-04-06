# Модуль oll_users_handlers
# В нем хэндлеры, которые работают для всех пользователей
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from data_base.data_base import *
from keyboards.keyboards import user_menu, remove_markup, create_inline_kb, confirm_markup
from services.services import not_votist_because_proxy_quit, votist_because_proxy_returned, leave_club
from config_data.config import Config, load_config
import logging
from utils import log_handler_call
from LEXICON.LEXICON import LEXICON
from FSMs.FSMs import FSM_become_proxy, FSM_leave_club

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')

# Инициализируем роутер уровня модуля
router = Router()

"""
ХЭНДЛЕРЫ
"""

# Хэндлер для команды /start
@router.message(Command(commands=["start"]))
@log_handler_call
async def process_start_command(message: Message, data: dict):
    """
    Обработчик команды /start.
    Отправляет приветственное сообщение и главное меню.
    """
    try:
        markup = await user_menu(message.from_user.id, status=data['user_status'])
        text = ('Привет!\nЭто бот для проведения голосований.\n'
                  'Ваш статус в группе:')
        for status in data['user_status']:
            text += f'\n   -{LEXICON.get(status, status)}'
        await message.answer(
            text=text,
            reply_markup=markup
        )
        logging.info(f"Пользователь {message.from_user.id} начал работу с ботом.")
    except Exception as e:
        logging.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer(text="Произошла ошибка при загрузке главного меню.",
                             reply_markup=await user_menu(status=data['user_status']))

# Хэндлер для команды /help
@router.message(Command(commands=['help']))
@log_handler_call
async def process_help_command(message: Message, data: dict):
    """
    Обработчик команды /help.
    Отправляет справочную информацию о боте.
    """
    logging.info(f"Пользователь {message.from_user.id} запросил справку.")
    await message.answer(
        text='Здесь будет описание функционала бота и инструкции по использованию.',
        reply_markup=await user_menu(message.from_user.id, status = data['user_status'])
    )

# Хэндлер для нажатия на кнопку "помощь"
@router.callback_query(F.data == 'help')
@log_handler_call
async def process_help_callback(callback: CallbackQuery, data: dict):
    """
    Обработчик нажатия на кнопку "помощь".
    Отправляет справочную информацию о боте.
    """
    logging.info(f"Пользователь {callback.from_user.id} запросил справку через кнопку.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Здесь будет описание функционала бота и инструкции по использованию.'
    data['reply_markup'] = await user_menu(callback.from_user.id, status = data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Хэндлер для команды /cancel в состоянии по умолчанию
@router.message(Command(commands='cancel'), StateFilter(default_state))
@log_handler_call
async def process_cancel_command(message: Message, data:dict):
    """
    Обработчик команды /cancel.
    Уведомляет пользователя, что команда работает только внутри машин состояний.
    """
    logging.info(f"Пользователь {message.from_user.id} попытался использовать /cancel вне машины состояний.")
    markup = await user_menu(message.from_user.id, data['user_status'])
    await message.answer(
        text='Вы вышли в главное меню.',
        reply_markup=markup
    )

# Хэндлер для команды /cancel в любом состоянии, кроме состояния по умолчанию
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
@log_handler_call
async def process_cancel_command_state(message: Message, state: FSMContext, data: dict):
    """
    Обработчик команды /cancel.
    Завершает текущую машину состояний.
    """
    logging.info(f"Пользователь {message.from_user.id} вышел из машины состояний.")
    markup = await user_menu(message.from_user.id, data['user_status'])
    await message.answer(
        text='Вы вышли из машины состояний и вернулись в главное меню.',
        reply_markup=markup
    )
    # Сбрасываем состояние и очищаем данные
    await state.clear()


# Хэндлер для кнопки 'Главное меню' в основном состоянии
@router.callback_query(F.data == 'main_menu', StateFilter(default_state))
@log_handler_call
async def process_main_menu_button(callback: CallbackQuery, data: dict):
    """
    Обработчик кнопки "Главное меню".
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    markup = await user_menu(callback.from_user.id,data['user_status'])

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Главное меню:'
    data['reply_markup'] = markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Хэндлер для кнопки 'Главное меню' внутри машины состояний.
@router.callback_query(F.data == 'main_menu', ~StateFilter(default_state))
@log_handler_call
async def process_main_menu_button_state(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик кнопки "Главное меню".
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    markup = await user_menu(callback.from_user.id,data['user_status'])

    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Вы вышли из процесса.\nГлавное меню:'
    data['reply_markup'] = markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

# Хэндлер будет обрабатывать ввод username представителя
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSM_become_proxy.fill_username))
@log_handler_call
async def process_username_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода имени/псевдонима.
    Запрашивает подтверждение.
    """
    logging.info(f"Пользователь {message.from_user.id} ввел свой псевдоним: {message.text}.")



# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Хэндлер для списка идущих голосваний для тех, у кого нет права голоса
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Хэндлер для кнопки 'ongoing_voting'
@router.callback_query(F.data == 'ongoing_votings')
@log_handler_call
async def process_list_of_ongoing_votings(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        club_id = data['club_id']
        voting_status = 'ongoing','confirmation'

        votings = await list_of_votings(club_id,*voting_status)

        if votings:
            text = 'Список голосований:\n'
            for voting in votings:
                text += f'- {voting[1]}\n'
            text += '\nВыберите голосование для просмотра вариантов:'

            dict_votings = {}
            for voting in votings:
                dict_votings[f'show_oll_variants:{voting[0]}'] = voting[1]
            dict_votings['main_menu'] = LEXICON.get('return_to_main_menu','main menu')
            markup = create_inline_kb(1, **dict_votings)

        else:
            text = 'В настоящее время нет активных голосований.'
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
        logging.error(f"Ошибка при обработке кнопки 'list_of_votings': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка голосований.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для кнопки 'completed_voting'
@router.callback_query(F.data == 'completed_votings')
@log_handler_call
async def process_list_of_completed_votings(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        club_id = data['club_id']

        votings = await list_of_votings(club_id,'completed')

        if votings:
            text = 'Список завершенных голосований:\n'
            for voting in votings:
                text += f'- {voting[1]}\n'
            text += '\nВыберите голосование для просмотра:'

            dict_votings = {}
            for voting in votings:
                dict_votings[f'show_oll_variants:{voting[0]}'] = voting[1]
            dict_votings['main_menu'] = LEXICON.get('return_to_main_menu','main menu')
            markup = create_inline_kb(1, **dict_votings)

        else:
            text = 'В настоящее время нет завершенных голосований.'
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
        logging.error(f"Ошибка при обработке кнопки 'completed_votings': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка завершенных голосований.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для кнопки 'future_votes'
@router.callback_query(F.data == 'future_votings')
@log_handler_call
async def process_list_of_future_votings(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        club_id = data['club_id']

        votings = await list_of_votings(club_id,'add_variants')

        if votings:
            text = 'Список голосований:\n'
            for voting in votings:
                text += f'- {voting[1]}\n'
            text += '\nВыберите голосование для просмотра:'

            dict_votings = {}
            for voting in votings:
                dict_votings[f'show_oll_variants:{voting[0]}'] = voting[1]
            dict_votings['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')
            markup = create_inline_kb(1, **dict_votings)

        else:
            text = 'В настоящее время нет голосований в стадии добавления вариантов.'
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
        logging.error(f"Ошибка при обработке кнопки 'future_votings': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка будущих голосований.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для просмотра всех вариантов (обрабатывает кнопку "посмотреть все варианты")
# Присылает по сообщению на каждый вариант, к последнему прикладывает клавиатуру из меню.
#Для членов группы - кнопка "выбрать вариант для голосвания" 'ongoing_voting:{voting_id}'
@router.callback_query(F.data.regexp(r'^show_oll_variants:\d+$'))
@log_handler_call
async def process_show_oll_variants(callback: CallbackQuery, data: dict):
    """
    Обработчик просмотра вариантов.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил просмотр вариантов: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        variants = await list_of_variants(voting_id)
        voting_status = await extract_voting_status(voting_id)


        if variants:
            for variant in variants:
                variant_id, title, variant_status, text_var = variant
                await callback.message.answer(
                    text=(title + '\n' + 'Статус варианта: ' + LEXICON.get(variant_status, variant_status) + '\n\n' + text_var),
                )
            text = 'Выберите дальнейшее действие'

        else:
            text = 'В настоящее время нет доступных вариантов.'

        dict_menu = {}
        if voting_status == 'add_variants':
            dict_menu['future_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
            # Если пользователь - делегат, добавляем кнопку "Добавить вариант"
            if 'delegate' in data["user_status"]:
                dict_menu[f'create_variant:{voting_id}'] = LEXICON.get('create_variant', 'create variant')
            if 'admin' in data["user_status"]:
                dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')
        elif voting_status == 'completed':
            dict_menu['completed_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
            # Если пользователь - админ, добавляем кнопку "Возобновить голосование"
            if 'admin' in data["user_status"]:
                dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')
        elif voting_status == 'ongoing':
            # Если пользователь - участник группы, добавляем кнопки для голосования
            if 'member' in data['user_status']:
                for variant in variants:
                    if variant[2] == 'valid':
                        dict_menu[f'variant:{variant[0]}'] = variant[1]
            # Если пользователь - админ, добавляем кнопки "Завершить этап","Перейти в финал","Завершить голосование"
            if 'admin' in data["user_status"]:
                dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')

            dict_menu['ongoing_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')

        elif voting_status =='confirmation':
            if 'admin' in data["user_status"]:
                dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')


        dict_menu['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')

        logging.info(f'словарь меню при показе вариантов: {dict_menu}')
        markup = create_inline_kb(1, **dict_menu)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
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





# Хэндлер для кнопки 'leave_the_group'
@router.callback_query(F.data == 'leave_the_group', StateFilter(default_state))
@log_handler_call
async def process_leave_the_group(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        text = 'Вы действительно хотите выйти из группы?\nВсё верно?'
        markup = confirm_markup

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.set_state(FSM_leave_club.fill_OK)

    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'list_of_votes': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка голосований.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для кнопки подтверждения выхода из группы
# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении выхода

@router.callback_query(StateFilter(FSM_leave_club.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
async def process_leave_club_entry(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' при подтверждении выхода из нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"


    try:
        # Запускаем процедуру выхода из группы
        member_id = data['member_id']
        status = data['user_status']
        await leave_club(member_id,status)
        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Вы вышли из группы!'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )


        # Завершаем машину состояний
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка при записи username: {e}")

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
@router.callback_query(StateFilter(FSM_leave_club.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_leave_club(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"


    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Вы остались в группе'
    data['reply_markup'] = await user_menu(status=data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Завершаем машину состояний
    await state.clear()


# Этот хэндлер будет срабатывать, если во время подтверждения
# выхода из группы будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSM_leave_club.fill_OK))
@log_handler_call
async def warning_leave_club(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSM_become_proxy.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать изменение статуса - '
             'отправьте команду /cancel'
    )



# Хэндлер для события изменения статуса члена чата
@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION)
)
async def handle_user_unblock(event: ChatMemberUpdated):
    """
    Срабатывает, когда пользователь разблокирует бота.
    """
    tg_id = event.from_user.id  # ID пользователя
    logging.info(f"Пользователь {tg_id} разблокировал бота.")

    # Обновляем статус пользователя в базе данных
    await mark_user_as_available(tg_id)

# Хэндлер для события блокировки бота
@router.my_chat_member(
    ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION)
)
async def handle_user_block(event: ChatMemberUpdated):
    """
    Срабатывает, когда пользователь блокирует бота.
    """
    tg_id = event.from_user.id  # ID пользователя
    logging.warning(f"Пользователь {tg_id} заблокировал бота.")

    # Обновляем статус пользователя в базе данных
    await mark_user_as_unavailable(tg_id, reason="Бот заблокирован")