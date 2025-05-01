# Модуль oll_users_handlers
# В нем хэндлеры, которые работают для всех пользователей
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.utils.text_decorations import html_decoration as html
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION
from data_base.data_base import *
from keyboards.keyboards import user_menu, remove_markup, create_inline_kb, confirm_markup, return_to_main_menu_markup
from services.services import not_votist_because_proxy_quit, votist_because_proxy_returned, leave_club, greetings_message, help_message
from config_data.config import Config, load_config
import logging
from utils import log_handler_call
from LEXICON.LEXICON import LEXICON
from FSMs.FSMs import FSM_become_proxy, FSM_leave_club

# Настройка логирования
logger = logging.getLogger(__name__)

# # Загружаем конфиг в переменную config
# config: Config = load_config('.env')

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
        text = await greetings_message(club_id=data['club_id'])
        text = text + '\nВаш статус в группе:'
        for status in data['user_status']:
            text += f'\n   -{LEXICON.get(status, status)}'
        await message.answer(
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
        logger.info(f"Пользователь {message.from_user.id} начал работу с ботом.")
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer(text="Произошла ошибка при загрузке главного меню.",
                             reply_markup=await user_menu(status=data['user_status']))


@router.message(Command(commands=["start"]))
@log_handler_call
async def process_start_command(message: Message, command: CommandObject, data: dict):
    """
    Обработчик команды /start.
    Отправляет приветственное сообщение и главное меню.
    Если команда /start вызвана с параметром (например, через URL), обрабатывает его.
    """
    try:
        # Извлекаем параметр из команды /start
        args = command.args  # Это то, что идет после ?start= в URL

        # Логика обработки параметра
        if args == "start":
            # Пользователь перешел по ссылке с параметром "start"
            text = (
                "🎉 Добро пожаловать! Вы перешли по специальной ссылке.\n"
                "Это бот для проведения голосований."
            )
        else:
            # Обычный старт без параметра
            text = (
                await ()
                + '\nВаш статус в группе:'
            )
            for status in data['user_status']:
                text += f'\n   - {LEXICON.get(status, status)}'

        # Создаем клавиатуру
        markup = await user_menu(message.from_user.id, status=data['user_status'])

        # Отправляем сообщение
        await message.answer(
            text=text,
            reply_markup=markup
        )

        logger.info(f"Пользователь {message.from_user.id} начал работу с ботом. Параметр: {args}")

    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer(
            text="Произошла ошибка при загрузке главного меню.",
            reply_markup=await user_menu(status=data['user_status'])
        )

# Хэндлер для команды /help
@router.message(Command(commands=['help']))
@log_handler_call
async def process_help_command(message: Message, data: dict):
    """
    Обработчик команды /help.
    Отправляет справочную информацию о боте.
    """
    logger.info(f"Пользователь {message.from_user.id} запросил справку.")
    await message.answer(
        text=help_message(data['user_status']),
        reply_markup=await user_menu(message.from_user.id, status = data['user_status']),
        parse_mode="HTML"  # Указываем режим разметки
    )

# Хэндлер для нажатия на кнопку "помощь"
@router.callback_query(F.data == 'help')
@log_handler_call
async def process_help_callback(callback: CallbackQuery, data: dict):
    """
    Обработчик нажатия на кнопку "помощь".
    Отправляет справочную информацию о боте.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил справку через кнопку.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = help_message(data['user_status'])
    data['reply_markup'] = await user_menu(callback.from_user.id, status = data['user_status'])

    # Отправляем сообщение со справкой в ответ
    await callback.message.answer(
        text=data['response_text'],
        reply_markup=data['reply_markup'],
        parse_mode="HTML"  # Указываем режим разметки
    )

# Хэндлер для команды /cancel в состоянии по умолчанию
@router.message(Command(commands='cancel'), StateFilter(default_state))
@log_handler_call
async def process_cancel_command(message: Message, data:dict):
    """
    Обработчик команды /cancel.
    Уведомляет пользователя, что команда работает только внутри машин состояний.
    """
    logger.info(f"Пользователь {message.from_user.id} попытался использовать /cancel вне машины состояний.")
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
    logger.info(f"Пользователь {message.from_user.id} вышел из машины состояний.")
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
    logger.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
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
    logger.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
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
    logger.info(f"Пользователь {message.from_user.id} ввел свой псевдоним: {message.text}.")


# # Универсальный хэндлер вызова списка голосований (в зависимости от их типа). Работает !!!
# @router.callback_query(F.data.regexp(r'^(ongoing_votings|completed_votings|future_votings)$'))
# @log_handler_call
# async def process_list_of_votings(callback: CallbackQuery, data: dict):
#     try:
#         logger.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
#         await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

#         # Определяем тип голосования на основе callback.data
#         voting_type = callback.data.split('_')[0]  # 'ongoing', 'completed', или 'future'
#         club_id = data['club_id']

#         # Определяем статусы голосований в зависимости от типа
#         if voting_type == 'ongoing':
#             voting_status = ('ongoing', 'confirmation')
#             empty_message = 'В настоящее время нет активных голосований.'
#         elif voting_type == 'completed':
#             voting_status = ('completed',)
#             empty_message = 'В настоящее время нет завершенных голосований.'
#         elif voting_type == 'future':
#             voting_status = ('add_variants',)
#             empty_message = 'В настоящее время нет голосований в стадии добавления вариантов.'

#         # Получаем список голосований
#         votings = await list_of_votings(club_id, *voting_status)

#         if votings:
#             text = f'Список {"активных" if voting_type == "ongoing" else "завершенных" if voting_type == "completed" else "будущих"} голосований:\n'
#             for voting in votings:
#                 text += f'- {voting[1]}\n'
#             text += '\nВыберите голосование для просмотра:'

#             # Формируем меню с голосованиями
#             dict_votings = {}
#             for voting in votings:
#                 dict_votings[f'show_oll_variants:{voting[0]}'] = voting[1]
#             dict_votings['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')
#             markup = create_inline_kb(1, **dict_votings)
#         else:
#             text = empty_message
#             markup = await user_menu(status=data['user_status'])

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = text
#         data['reply_markup'] = markup

#         # Редактируем сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#     except Exception as e:
#         logger.error(f"Ошибка при обработке списка голосований ({callback.data}): {e}")

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = 'Произошла ошибка при загрузке списка голосований.'
#         data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

#         # Редактируем сообщение в случае ошибки
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#         raise  # Передаем исключение middleware для обработки

# Обновленный универсальный хэндлер для вызова списка голосований.
# Присылает по сообщению на каждое голосование.
@router.callback_query(F.data.regexp(r'^(ongoing_votings|completed_votings|future_votings)$'))
@log_handler_call
async def process_list_of_votings(callback: CallbackQuery, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        # Определяем тип голосования на основе callback.data
        voting_type = callback.data.split('_')[0]  # 'ongoing', 'completed', или 'future'
        club_id = data['club_id']

        # Определяем статусы голосований в зависимости от типа
        if voting_type == 'ongoing':
            voting_status = ('ongoing', 'confirmation')
            header_message = 'Список активных голосований:'
            empty_message = 'В настоящее время нет активных голосований.'
        elif voting_type == 'completed':
            voting_status = ('completed',)
            header_message = 'Список завершенных голосований:'
            empty_message = 'В настоящее время нет завершенных голосований.'
        elif voting_type == 'future':
            voting_status = ('add_variants',)
            header_message = 'Список будущих голосований:'
            empty_message = 'В настоящее время нет голосований в стадии добавления вариантов.'

        # Получаем список голосований
        votings = await list_of_votings(club_id, *voting_status)

        # Формируем клавиатуру для возврата в главное меню
        main_menu_markup = return_to_main_menu_markup

        if votings:
            # Отправляем заголовок
            await callback.message.answer(header_message)

            # Отправляем по одному сообщению на каждое голосование
            for i, voting in enumerate(votings):
                voting_id, title, description = voting
                await callback.message.answer(
                    text=(
                        f"🗳️ <b>{title}</b>\n"
                        f"📝 Описание:\n{description}\n\n"
                        f"<i>Выберите это голосование для просмотра вариантов.</i>"
                    ),
                    parse_mode="HTML",
                    reply_markup=create_inline_kb(1, **{f'show_oll_variants:{voting_id}': 'Посмотреть варианты'})
                )

            # В последнем сообщении добавляем кнопку "Вернуться в главное меню"
            await callback.message.answer(
                text=LEXICON.get('return_to_main_menu', 'Вернуться в главное меню'),
                reply_markup=main_menu_markup
            )
        else:
            # Если голосований нет, отправляем сообщение об этом и кнопку "Вернуться в главное меню"
            await callback.message.answer(empty_message)
            await callback.message.answer(
                text=LEXICON.get('return_to_main_menu', 'Вернуться в главное меню'),
                reply_markup=main_menu_markup
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке списка голосований ({callback.data}): {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка голосований.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для просмотра всех вариантов (обрабатывает кнопку "посмотреть все варианты")
# Присылает по сообщению на каждый вариант, к последнему прикладывает клавиатуру из меню.
# Варианты отсортиованы по числу голосов
# Для членов группы - под каждым вариантом кнопка для голосования
@router.callback_query(F.data.regexp(r'^show_oll_variants:\d+$'))
@log_handler_call
async def process_show_oll_variants(callback: CallbackQuery, data: dict):
    """
    Обработчик просмотра вариантов.
    """
    try:
        logger.info(f"Пользователь {callback.from_user.id} запросил просмотр вариантов: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(':')[1])
        variants = await list_of_variants(voting_id)
        voting_info = await extract_voting_info(voting_id)
        if voting_info:
            voting_status, voting_title = voting_info
        else:
            voting_status = None
            voting_title = None

        choise = await variant_choise(data['member_id'], voting_id)

        # Экранируем специальные символы в тексте
        escaped_voting_title = html.quote(voting_title)

        await callback.message.answer(
            text=(
                f"Список вариантов к голосованию\n"
                f"<b>{escaped_voting_title}</b>\n"
            ),
            parse_mode="HTML"
        )

        if variants:
            # Функция для подсчета суммарных голосов за вариант
            async def calculate_total_votes(variant_id):
                dir_votes = await count_directly_votes(variant_id)  # решающие голоса, поданные за вариант напрямую
                proxy_votes = await count_proxy_votes(variant_id)   # решающие голоса, поданные через представителя
                return dir_votes + proxy_votes

            # Добавляем поле total_votes к каждому варианту
            variants_with_votes = []
            for variant in variants:
                variant_id, title, variant_status, text_var = variant
                total_votes = await calculate_total_votes(variant_id)
                variants_with_votes.append((variant_id, title, variant_status, text_var, total_votes))

            # Разделяем варианты на действительные и проигравшие
            valid_variants = [v for v in variants_with_votes if v[2] == 'valid']
            loser_variants = [v for v in variants_with_votes if v[2] == 'loser']

            # Сортируем варианты по убыванию total_votes
            valid_variants.sort(key=lambda x: x[4], reverse=True)
            loser_variants.sort(key=lambda x: x[4], reverse=True)

            # Выводим сначала действительные варианты, затем проигравшие
            for variant in valid_variants + loser_variants:
                variant_id, title, variant_status, text_var, total_votes = variant
                dir_votes = await count_directly_votes(variant_id)  # решающие голоса, поданные за вариант напрямую
                proxy_votes = await count_proxy_votes(variant_id)   # решающие голоса, поданные через представителя
                empty_votes = await count_directly_empty_votes(variant_id)  # нерешающие голоса
                if variant_id in choise:
                    choise_mark = '***ВАШ ВЫБОР***\n'
                else:
                    choise_mark = ''

                # Экранируем специальные символы в тексте
                escaped_title = html.quote(title)
                escaped_text_var = html.quote(text_var)

                # Если это идущее голосование, а пользователь - участник группы, добавляем кнопку проголосовать за вариант
                if voting_status == 'ongoing' and 'member' in data['user_status'] and variant_status == 'valid':
                    keyboard = {f'variant:{variant_id}': LEXICON.get('Vote for this variant', 'Vote for this variant')}
                    markup = create_inline_kb(1, **keyboard)
                # Если это голосование в стадии добавления вариантов, а пользователь - админ, добавляем кнопку "удалить вариант"
                elif voting_status == 'add_variants' and 'admin' in data['user_status'] and variant_status == 'valid':
                    keyboard = {f'delete_variant:{variant_id}': LEXICON.get('delete variant', 'delete variant')}
                    markup = create_inline_kb(1, **keyboard)
                else:
                    markup = None

                await callback.message.answer(
                    text=(
                        f"{choise_mark}"
                        f"🗳️ <b>{escaped_title}</b>\n"
                        f"📌 Статус: {LEXICON.get(variant_status, variant_status)}\n\n"
                        f"📝 <b>Описание:</b>\n{escaped_text_var}\n\n"
                        "📊 <b>Статистика голосов:</b>\n"
                        f"• Решающих голосов: <b>{total_votes}</b>\n"
                        f"  - Напрямую: {dir_votes}\n"
                        f"  - Через представителей: {proxy_votes}\n"
                        f"• Нерешающих голосов: {empty_votes}"
                    ),
                    reply_markup=markup,
                    parse_mode="HTML"
                )

            text = 'Выберите дальнейшее действие'

        else:
            text = 'В настоящее время нет доступных вариантов.'

        # Формируем меню в зависимости от статуса голосования
        dict_menu = {}
        if voting_status == 'add_variants':
            dict_menu['future_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
            if 'delegate' in data["user_status"]:
                dict_menu[f'create_variant:{voting_id}'] = LEXICON.get('create_variant', 'Добавить вариант')
            if 'admin' in data["user_status"]:
                dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'Администрирование голосования')
        elif voting_status == 'completed':
            dict_menu['completed_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
            # Пока не администрируем завершенные голосования (не перезапускаем)
            # if 'admin' in data["user_status"]:
            #     dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'Администрирование голосования')
        elif voting_status == 'ongoing':
            if 'admin' in data["user_status"]:
                dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'Администрирование голосования')
            dict_menu['ongoing_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
        elif voting_status == 'confirmation':
            if 'admin' in data["user_status"]:
                dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'Администрирование голосования')
            dict_menu['ongoing_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')

        dict_menu['main_menu'] = LEXICON.get('return_to_main_menu', 'Вернуться в главное меню')

        logger.info(f'Словарь меню при показе вариантов: {dict_menu}')
        markup = create_inline_kb(1, **dict_menu)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Отправляем сообщение
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logger.error(f"Ошибка при просмотре вариантов голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при просмотре вариантов голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Отправляем сообщение в случае ошибки
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# # Хэндлер для просмотра всех вариантов (обрабатывает кнопку "посмотреть все варианты")
# # Присылает по сообщению на каждый вариант, к последнему прикладывает клавиатуру из меню.
# # Для членов группы - кнопка "выбрать вариант для голосвания" 'ongoing_voting:{voting_id}'
# @router.callback_query(F.data.regexp(r'^show_oll_variants:\d+$'))
# @log_handler_call
# async def process_show_oll_variants(callback: CallbackQuery, data: dict):
#     """
#     Обработчик просмотра вариантов.
#     """
#     try:
#         logger.info(f"Пользователь {callback.from_user.id} запросил просмотр вариантов: {callback.data}")
#         await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

#         voting_id = int(callback.data.split(':')[1])
#         variants = await list_of_variants(voting_id)
#         voting_info = await extract_voting_info(voting_id)
#         if voting_info:
#             voting_status, voting_title = voting_info
#         else:
#             variant_status = None
#             voting_title = None

#         choise = await variant_choise(data['member_id'], voting_id)

#         # Экранируем специальные символы в тексте
#         escaped_voting_title = html.quote(voting_title)

#         await callback.message.answer(
#             text=(
#                 f"Список вариантов к голосованию"
#                 f"<b>{escaped_voting_title}</b>\n"
#             ),
#             parse_mode="HTML"
#         )

#         if variants:
#             for variant in variants:
#                 variant_id, title, variant_status, text_var = variant
#                 dir_votes = await count_directly_votes(variant_id) # решающие голоса, поданные за вариант напрямую
#                 proxy_votes = await count_proxy_votes(variant_id)   #решающие голоса, поданные через представителя
#                 empty_votes = await count_directly_empty_votes(variant_id)   # нерешающие голоса
#                 oll_votes = dir_votes + proxy_votes
#                 if variant_id in choise:
#                     choise_mark = '***ВАШ ВЫБОР***\n'
#                 else:
#                     choise_mark = ''

#                 # Экранируем специальные символы в тексте
#                 escaped_title = html.quote(title)
#                 escaped_text_var = html.quote(text_var)

#                 # Если это идущее голосвание, а пользователь - участник группы, добавляем
#                 # кнопку проголосовать за вариант
#                 if voting_status == 'ongoing' and 'member' in data['user_status'] and variant[2] == 'valid':
#                     keyboard = {f'variant:{variant[0]}':LEXICON.get('Vote for this variant','Vote for this variant')}
#                     markup = create_inline_kb(1, **keyboard)
#                 else:
#                     markup = None



#                 await callback.message.answer(
#                     text=(
#                         f"{choise_mark}"
#                         f"🗳️ <b>{escaped_title}</b>\n"
#                         f"📌 Статус: {LEXICON.get(variant_status, variant_status)}\n\n"
#                         f"📝 <b>Описание:</b>\n{escaped_text_var}\n\n"
#                         "📊 <b>Статистика голосов:</b>\n"
#                         f"• Решающих голосов: <b>{oll_votes}</b>\n"
#                         f"  - Напрямую: {dir_votes}\n"
#                         f"  - Через представителей: {proxy_votes}\n"
#                         f"• Нерешающих голосов: {empty_votes}"
#                     ),
#                     reply_markup=markup,
#                     parse_mode="HTML"
#                 )

#             text = 'Выберите дальнейшее действие'

#         else:
#             text = 'В настоящее время нет доступных вариантов.'

#         dict_menu = {}
#         if voting_status == 'add_variants':
#             dict_menu['future_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
#             # Если пользователь - делегат, добавляем кнопку "Добавить вариант"
#             if 'delegate' in data["user_status"]:
#                 dict_menu[f'create_variant:{voting_id}'] = LEXICON.get('create_variant', 'create variant')
#             if 'admin' in data["user_status"]:
#                 dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')
#         elif voting_status == 'completed':
#             dict_menu['completed_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')
#             # Если пользователь - админ, добавляем кнопку "Возобновить голосование"
#             if 'admin' in data["user_status"]:
#                 dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')
#         elif voting_status == 'ongoing':
#             # Если пользователь - админ, добавляем кнопки "Завершить этап","Перейти в финал","Завершить голосование"
#             if 'admin' in data["user_status"]:
#                 dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')

#             dict_menu['ongoing_votings'] = LEXICON.get('back_to_votings', 'Назад к списку голосований')

#         elif voting_status =='confirmation':
#             if 'admin' in data["user_status"]:
#                 dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'admin_voting')


#         dict_menu['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')

#         logger.info(f'словарь меню при показе вариантов: {dict_menu}')
#         markup = create_inline_kb(1, **dict_menu)

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = text
#         data['reply_markup'] = markup

#         # Отправляем сообщение
#         await callback.message.answer(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#     except Exception as e:
#         logger.error(f"Ошибка при просмотре вариантов голосования: {e}")

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = 'Произошла ошибка при просмотре вариантов голосования.'
#         data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

#         # Отправляем сообщение в случае ошибки
#         await callback.message.answer(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#         raise  # Передаем исключение middleware для обработки





# Хэндлер для кнопки 'leave_the_group'
@router.callback_query(F.data == 'leave_the_group', StateFilter(default_state))
@log_handler_call
async def process_leave_the_group(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
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
        logger.error(f"Ошибка при обработке кнопки 'list_of_votes': {e}")

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
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' при подтверждении выхода из нажата пользователем {callback.from_user.id}")
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
@router.callback_query(StateFilter(FSM_leave_club.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_no_confirm_leave_club(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
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
    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSM_become_proxy.fill_OK}")
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
    logger.info(f"Пользователь {tg_id} разблокировал бота.")

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
    logger.warning(f"Пользователь {tg_id} заблокировал бота.")

    # Обновляем статус пользователя в базе данных
    await mark_user_as_unavailable(tg_id, reason="Бот заблокирован")