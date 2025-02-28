from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from aiogram.exceptions import TelegramBadRequest
from filters.filters import StatusFilter
from LEXICON.LEXICON import LEXICON
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, create_inline_kb
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
router.message.filter(StatusFilter(required_status = 'member'))

# Хэндлер для кнопки 'ongoing_voting'
@router.callback_query(F.data == 'ongoing_votings')
@log_handler_call
async def process_ongoing_votings(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        votings = await list_of_votings_tg('ongoing')

        if votings:
            text = 'Список голосований:\n'
            for voting in votings:
                text += f'- {voting[1]}\n'
            text += '\nВыберите голосование для участия:'

            dict_votings = {}
            for voting in votings:
                dict_votings[f'voting_{voting[0]}'] = voting[1]
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


# Хэндлер для кнопки 'completed_voting'
@router.callback_query(F.data == 'completed_votings')
@log_handler_call
async def process_list_of_completed_votings(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        votings = await list_of_votings_tg('completed')

        if votings:
            text = 'Список завершенных голосований:\n'
            for voting in votings:
                text += f'- {voting[1]}\n'
            text += '\nВыберите голосование для просмотра:'

            dict_votings = {}
            for voting in votings:
                dict_votings[f'completed_voting_{voting[0]}'] = voting[1]
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
async def process_list_of_future_votes(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        votings = await list_of_votings_tg('add_variants')

        if votings:
            text = 'Список голосований:\n'
            for voting in votings:
                text += f'- {voting[1]}\n'
            text += '\nВыберите голосование для просмотра:'

            dict_votings = {}
            for voting in votings:
                dict_votings[f'future_voting_{voting[0]}'] = voting[1]
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





# Хэндлер для выбора конкретного идущего голосования
@router.callback_query(F.data.regexp(r'^voting_\d+$'))
@log_handler_call
async def process_voting_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split('_')[1])
        variants = await list_of_variants(voting_id, 'valid')

        if variants:
            text = ('Выберите вариант за который хотите проголосовать.\n'
                    'Или нажмите кнопку "Посмотреть варианты", если хотите посмотреть варианты\n')

            dict_variants = {}
            for variant in variants:
                dict_variants[f'variant_{variant[0]}'] = variant[1]
            dict_variants[f'show_variants:{voting_id}'] = LEXICON.get('show_variants', 'show variants')
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

# Хэндлер для просмотра вариантов (обрабатывает кнопку "посмотреть варианты")
# Присылает по сообщению на каждый вариант, к последнему прикладывает клавиаттуру из вариантов
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
                title, text_var = await extract_variant_data(variant[0])
                await callback.message.answer(
                    text=(title + '\n\n' + text_var),
                )

            text = 'Выберите вариант за который хотите проголосовать:\n'

            dict_variants = {}
            for variant in variants:
                dict_variants[f'variant_{variant[0]}'] = variant[1]
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




# Хэндлер для просмотра будущего голосования
@router.callback_query(F.data.regexp(r'^future_voting_\d+$'))
@log_handler_call
async def process_future_vote_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик просмотра будущего голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал будущее голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split('_')[2])
        variants = await list_of_variants(voting_id, 'valid')

        if variants:
            text = 'Выберите вариант, который хотите посмотреть'
            dict_variants = {}
            for variant in variants:
                dict_variants[f'show_variant_{variant[0]}'] = variant[1]
            # Если пользователь - делегат, добавляем кнопку "добавить вариант"
            if 'delegate' in data['user_status']:
                dict_variants[f'create_variant_vote:{voting_id}'] = LEXICON.get('create_variant', 'create variant')

            dict_variants['main_menu'] = LEXICON.get('return_to_main_menu', 'main menu')

            markup = create_inline_kb(1, **dict_variants)

            for variant in variants:
                text += f'- {variant[1]}\n'
            text += '\nВыберите вариант для просмотра:'

        else:
            text = 'В настоящее время у будущего голосования нет вариантов.'
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
        logging.error(f"Ошибка при просмотре будущего голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при просмотре будущего голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки




# Хэндлер для выбора конкретного варианта при голосовании
@router.callback_query(F.data.regexp(r'^variant_\d+$'))
@log_handler_call
async def process_variant_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного варианта голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал вариант: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        variant_id = int(callback.data.split('_')[1])
        success, message = await election_tg(callback.from_user.id, variant_id)

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




# Хэндлер для кнопки 'select_proxy'
@router.callback_query(F.data == 'select_proxy')
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

        #    !!!!!!!!!!!!!!!!!!!!!!!!!!!
        #       Разобраться с тёзками!
        #    !!!!!!!!!!!!!!!!!!!!!!!!!!!

        # Создаем кнопки для каждого представителя, текст - Имя Фамилия, data - телеграм ID
        proxy_buttons = {}
        for member in members:
            proxy_buttons[f'trust_{member[2]}'] = f"{member[0]} {member[1]}"


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

# Хэндлер для доверия голоса
@router.callback_query(F.data.startswith('trust_'))
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

# Хэндлер для кнопки 'become_proxy'
@router.callback_query(F.data == 'become_proxy')
@log_handler_call
async def process_become_proxy(callback: CallbackQuery, data: dict):
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

        # Присваиваем статус 'proxy'
        await new_status_tg(callback.from_user.id, callback.from_user.id, 'proxy')

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Вы стали представителем!'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'become_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при присвоении статуса.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

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
        await new_status_tg(callback.from_user.id, callback.from_user.id, 'not_proxy')

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Вы перестали быть представителем!'
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
