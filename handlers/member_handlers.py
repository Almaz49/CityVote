from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize, Contact)
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from filters.filters import StatusFilter
from LEXICON.LEXICON import LEXICON
from FSMs.FSMs import FSM_become_proxy, FSM_appoint_deputy, FSM_leave_club
from services.services import not_votist_because_proxy_quit, votist_because_proxy_returned, leave_club
from keyboards.keyboards import (reg_markup, contact_markup, remove_markup, user_menu,
            create_inline_kb, confirm_markup, return_to_main_menu_markup)
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import *
import logging
from utils import log_handler_call

# Инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status = ['member']))
router.callback_query.filter(StatusFilter(required_status = ['member']))

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
                dict_votings[f'ongoing_voting:{voting[0]}'] = voting[1]
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


# # Хэндлер для кнопки 'completed_voting'
# @router.callback_query(F.data == 'completed_votings')
# @log_handler_call
# async def process_list_of_completed_votings(callback: CallbackQuery, data: dict):
#     try:
#         logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
#         await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

#         club_id = data['club_id']

#         votings = await list_of_votings(club_id,'completed')

#         if votings:
#             text = 'Список завершенных голосований:\n'
#             for voting in votings:
#                 text += f'- {voting[1]}\n'
#             text += '\nВыберите голосование для просмотра:'

#             dict_votings = {}
#             for voting in votings:
#                 dict_votings[f'show_oll_variants:{voting[0]}'] = voting[1]
#             dict_votings['main_menu'] = LEXICON.get('return_to_main_menu','main menu')
#             markup = create_inline_kb(1, **dict_votings)

#         else:
#             text = 'В настоящее время нет завершенных голосований.'
#             markup = await user_menu(status=data['user_status'])

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = text
#         data['reply_markup'] = markup

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#     except Exception as e:
#         logging.error(f"Ошибка при обработке кнопки 'completed_votings': {e}")

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = 'Произошла ошибка при загрузке списка завершенных голосований.'
#         data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#         raise  # Передаем исключение middleware для обработки


# # Хэндлер для кнопки 'future_votes'
# @router.callback_query(F.data == 'future_votings')
# @log_handler_call
# async def process_list_of_future_votings(callback: CallbackQuery, data: dict):
#     try:
#         logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
#         await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

#         club_id = data['club_id']

#         votings = await list_of_votings(club_id,'add_variants')

#         if votings:
#             text = 'Список голосований:\n'
#             for voting in votings:
#                 text += f'- {voting[1]}\n'
#             text += '\nВыберите голосование для просмотра:'

#             dict_votings = {}
#             for voting in votings:
#                 dict_votings[f'show_oll_variants:{voting[0]}'] = voting[1]
#             dict_votings['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')
#             markup = create_inline_kb(1, **dict_votings)

#         else:
#             text = 'В настоящее время нет голосований в стадии добавления вариантов.'
#             markup = await user_menu(status=data['user_status'])

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = text
#         data['reply_markup'] = markup

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#     except Exception as e:
#         logging.error(f"Ошибка при обработке кнопки 'future_votings': {e}")

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = 'Произошла ошибка при загрузке списка будущих голосований.'
#         data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#         raise  # Передаем исключение middleware для обработки





# Хэндлер для выбора конкретного идущего голосования
@router.callback_query(F.data.regexp(r'^ongoing_voting:\d+$'))
@log_handler_call
async def process_ongoing_voting_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        variants = await list_of_variants(voting_id, 'valid')

        if variants:
            text = ('Выберите вариант за который хотите проголосовать.\n'
                    'Или нажмите кнопку "Посмотреть варианты", если хотите посмотреть варианты\n')

            dict_variants = {}
            for variant in variants:
                dict_variants[f'variant:{variant[0]}'] = variant[1]
            dict_variants[f'show_variants:{voting_id}'] = LEXICON.get('show_variants', 'show variants')
            if 'admin' in data['user_status']:
                # Добавляем кнопку для админа - администрировать голосование
                dict_variants[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'Администрировать голосование')


            dict_variants['main_menu'] = LEXICON.get('return_to_main_menu','main menu')

            logging.info(f'словарь для клавиатуры вариантов: {dict_variants}')
            markup = create_inline_kb(1, **dict_variants)

            for variant in variants:
                text += f'- {variant[1]}\n'
            text = '\nВыберите вариант для голосования:\n' + text

        else:
            text = 'В настоящее время нет доступных вариантов для голосования.'
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
        logging.error(f"Ошибка при выборе конкретного голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при выборе голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для просмотра вариантов идущего голосвания (обрабатывает кнопку "посмотреть варианты")
# Присылает по сообщению на каждый вариант, к последнему прикладывает клавиаттуру из вариантов
# Показываются варианты, имеющией статус "действительный"
@router.callback_query(F.data.regexp(r'^show_variants:\d+$'))
@log_handler_call
async def process_show_variants(callback: CallbackQuery, data: dict):
    """
    Обработчик просмотра вариантов.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил просмотр вариантов: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        variants = await list_of_variants(voting_id, 'valid')

        if variants:
            for variant in variants:
                title, text_var, variant_status = await extract_variant_data(variant[0])
                await callback.message.answer(
                    text=(title + '\n\n' + text_var),
                )

            text = 'Выберите вариант за который хотите проголосовать:\n'

            dict_variants = {}
            for variant in variants:
                dict_variants[f'variant:{variant[0]}'] = variant[1]
            dict_variants['ongoing_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
            dict_variants['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')

            logging.info(f'словарь для клавиатуры вариантов: {dict_variants}')
            markup = create_inline_kb(1, **dict_variants)

            for variant in variants:
                text += f'- {variant[1]}\n'
            text += '\nВыберите вариант для голосования:'

        else:
            text = 'В настоящее время нет доступных вариантов для голосования.'
            markup = await user_menu(status=data['user_status'])

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
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для просмотра всех вариантов (обрабатывает кнопку "посмотреть все варианты")
# Присылает по сообщению на каждый вариант, к последнему прикладывает клавиатуру из меню.
# Применяется для будущих и завершенных голосований
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
            # Если пользователь - делегат, добавляем кнопку "Добавить голосование"
            if 'delegete' in data["user_status"]:
                dict_menu[f'create_variant:{voting_id}'] = LEXICON.get('create_variant', 'create variant')
        elif voting_status == 'comleted':
            dict_menu['completed_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
            # Если пользователь - админ, добавляем кнопку "Возобновить голосование"
            if 'admin' in data["user_status"]:
                dict_menu[f'reopen:{voting_id}'] = LEXICON.get('reopen', 'reopen')


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




# Хэндлер для выбора конкретного варианта при голосовании
@router.callback_query(F.data.regexp(r'^variant:\d+$'))
@log_handler_call
async def process_variant_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного варианта голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал вариант: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        variant_id = int(callback.data.split('_')[1])
        member_id = data['member_id']
        success, message = await election(member_id, variant_id)

        if success:
            text = f'Ваш голос принят: {message}'
        else:
            text = f'Ошибка при голосовании: {message}'

        keyboard = {
            f'show_result_variant:{variant_id}':LEXICON.get('show_result','Текущий результат'),
            'ongoing_voting':LEXICON.get('ongoing_voting','ongoing voting'),
            'main_menu':LEXICON.get('main_menu', 'main menu')
            }
        markup = create_inline_kb(1, 'main_menu')

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при выборе конкретного варианта голосования: {e}")

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
        logging.info(f"Пользователь {callback.from_user.id} запросил список представителей.")
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
            proxy_buttons[f'trust_{member[2]}'] = f'{member[5]}' if member[5] else  f"{member[0]} {member[1]}"

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
        logging.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")

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
        logging.info(f"Представитеь {callback.from_user.id} хочет выбрать заместителя.")
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
        logging.info(f"Установлено состояние: {await state.get_state()}")

    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")

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
@router.callback_query(F.data.startswith('trust_'), ~StatusFilter(required_status = ['proxy']))
@log_handler_call
async def process_trust(callback: CallbackQuery, data: dict):
    try:
        proxy_tg_id = int(callback.data.split('_')[1])
        logging.info(f"Пользователь {callback.from_user.id} доверил свой голос пользователю с tg_id {proxy_tg_id}.")
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
        logging.error(f"Ошибка при доверии голоса: {e}")

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
async def process_appoint_deputy(message: Message, data: dict, state: FSMContext, contact: Contact = None):
    try:
        deputy_tg_id = contact.user_id if contact else int(message.text)
        logging.info(f"Представитель {message.from_user.id} выбрал своим заместителем пользователя с tg_id {deputy_tg_id}.")

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
        logging.error(f"Ошибка при выборе  заместителя: {e}")

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
        logging.info(f"Пользователь {callback.from_user.id} запросил статус 'proxy'.")
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
        logging.error(f"Ошибка при обработке кнопки 'become_proxy': {e}")

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
    logging.info(f"Пользователь {message.from_user.id} ввел свой псевдоним: {message.text}.")
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
    logging.info(f"Кнопка 'ВСЁ ВЕРНО' при подтверждении username нажата пользователем {callback.from_user.id}")
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
@router.callback_query(StateFilter(FSM_become_proxy.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_proxy_press(callback: CallbackQuery, state: FSMContext, data: dict):
    logging.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
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
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSM_become_proxy.fill_OK}")
    await message.answer(
        text='Пожалуйста, воспользуйтесь кнопками!\n\n'
             'Если вы хотите прервать изменение статуса - '
             'отправьте команду /cancel'
    )



# Хэндлер для кнопки ''resign_from_proxy''
@router.callback_query(F.data == 'resign_from_proxy')
@log_handler_call
async def process_resign_from_proxy(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} отказывается от статуса 'proxy'.")
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

    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'resign_from_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при удалении статуса представителя.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки
