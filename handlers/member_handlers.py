from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from aiogram.exceptions import TelegramBadRequest
from filters.filters import filter_isMember
from LEXICON.LEXICON import LEXICON
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, create_inline_kb
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import *
import logging

# Инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(filter_isMember)

# Хэндлер для кнопки 'list_of_votes'
@router.callback_query(F.data == 'list_of_votes')
async def process_list_of_votes(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        votes = await list_of_votes_tg('ongoing')

        if votes:
            text = 'Список голосований:\n'
            for vote in votes:
                text += f'- {vote[1]}\n'
            text += '\nВыберите голосование для участия:'

            dict_votes = {}
            for vote in votes:
                dict_votes[f'vote_{vote[0]}'] = vote[1]
            dict_votes['main_menu'] = LEXICON['main_menu']
            markup = create_inline_kb(1, **dict_votes)

        else:
            text = 'В настоящее время нет активных голосований.'
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
        logging.error(f"Ошибка при обработке кнопки 'list_of_votes': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка голосований.'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для кнопки 'future_votes'
@router.callback_query(F.data == 'future_votes')
async def process_list_of_future_votes(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        votes = await list_of_votes_tg('add_variants')

        if votes:
            text = 'Список голосований:\n'
            for vote in votes:
                text += f'- {vote[1]}\n'
            text += '\nВыберите голосование для просмотра:'

            dict_votes = {}
            for vote in votes:
                dict_votes[f'future_vote_{vote[0]}'] = vote[1]
            dict_votes['main_menu'] = LEXICON['main_menu']
            markup = create_inline_kb(1, **dict_votes)

        else:
            text = 'В настоящее время нет голосований в стадии добавления вариантов.'
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
        logging.error(f"Ошибка при обработке кнопки 'future_votes': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при загрузке списка будущих голосований.'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки





# Хэндлер для выбора конкретного голосования
@router.callback_query(F.data.regexp(r'^vote_\d+$'))
async def process_vote_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        vote_id = int(callback.data.split('_')[1])
        variants = await list_of_variants(vote_id, 'valid')

        if variants:
            text = ('Выберите вариант за который хотите проголосовать:\n'
                    'Или нажмите кнопку "Посмотреть варианты", если хотите посмотреть варианты')

            dict_variants = {}
            for variant in variants:
                dict_variants[f'variant_{variant[0]}'] = variant[1]
            dict_variants[f'show_variants:{vote_id}'] = LEXICON.get('show_variants', 'show variants')
            dict_variants['main_menu'] = LEXICON.get('main_menu', 'main menu')

            logging.info(f'словарь для клавиатуры вариантов: {dict_variants}')
            markup = create_inline_kb(1, **dict_variants)

            for variant in variants:
                text += f'- {variant[1]}\n'
            text += '\nВыберите вариант для голосования:'

        else:
            text = 'В настоящее время нет доступных вариантов для голосования.'
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
        logging.error(f"Ошибка при выборе конкретного голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при выборе голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для просмотра вариантов (обрабатывает кнопку "посмотреть варианты")
# Присылает по сообщению на каждый вариант, к последнему прикладывает клавиаттуру из вариантов
@router.callback_query(F.data.regexp(r'^show_variants:\d+$'))
async def process_show_variants(callback: CallbackQuery, data: dict):
    """
    Обработчик просмотра вариантов.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил просмотр вариантов: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        vote_id = int(callback.data.split(':')[1])
        variants = await list_of_variants(vote_id, 'valid')

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
            dict_variants['show_variants'] = LEXICON.get('show_variants', 'show variants')
            dict_variants['main_menu'] = LEXICON.get('main_menu', 'main menu')

            logging.info(f'словарь для клавиатуры вариантов: {dict_variants}')
            markup = create_inline_kb(1, **dict_variants)

            for variant in variants:
                text += f'- {variant[1]}\n'
            text += '\nВыберите вариант для голосования:'

        else:
            text = 'В настоящее время нет доступных вариантов для голосования.'
            markup = create_inline_kb(1, 'main_menu')

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
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки




# Хэндлер для просмотра будущего голосования
@router.callback_query(F.data.regexp(r'^future_vote_\d+$'))
async def process_future_vote_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик просмотра будущего голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал будущее голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        vote_id = int(callback.data.split('_')[1])
        variants = await list_of_variants(vote_id, 'valid')

        if variants:
            text = 'Выберите вариант, который хотите посмотреть'
            dict_variants = {}
            for variant in variants:
                dict_variants[f'show_variant_{variant[0]}'] = variant[1]

            if 'delegate' in await extract_status_tg(callback.from_user.id):
                dict_variants[f'create_variant_vote:{vote_id}'] = LEXICON.get('create_variant', 'create variant')

            dict_variants['main_menu'] = LEXICON.get('main_menu', 'main menu')

            markup = create_inline_kb(1, **dict_variants)

            for variant in variants:
                text += f'- {variant[1]}\n'
            text += '\nВыберите вариант для просмотра:'

        else:
            text = 'В настоящее время у будущего голосования нет вариантов.'
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
        logging.error(f"Ошибка при просмотре будущего голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при просмотре будущего голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки




# Хэндлер для выбора конкретного варианта голосования
@router.callback_query(F.data.regexp(r'^variant_\d+$'))
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
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Отправляем новое сообщение в случае ошибки
        await callback.message.answer(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для просмотра будущего голосования
@router.callback_query(F.data.regexp(r'^future_vote_\d+$'))
async def process_future_vote_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал будущее голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        vote_id = int(callback.data.split('_')[1])  # Исправлено индексирование для получения vote_id
        variants = await list_of_variants(vote_id, 'valid')

        if variants:
            text = 'Выберите вариант, который хотите посмотреть'
            dict_variants = {}
            for variant in variants:
                dict_variants[f'variant_{variant[0]}'] = variant[1]

            if 'delegate' in await extract_status_tg(callback.from_user.id):  # Добавлен асинхронный вызов
                dict_variants['new_variant'] = LEXICON.get('new_variant', 'create variant')

            dict_variants['main_menu'] = LEXICON.get('main_menu', 'main menu')

            markup = create_inline_kb(1, **dict_variants)

            for variant in variants:
                text += f'- {variant[1]}\n'
            text += '\nВыберите вариант для просмотра:'

        else:
            text = 'В настоящее время у будущего голосования нет вариантов.'
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
        logging.error(f"Ошибка при просмотре будущего голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при просмотре будущего голосования.'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки





# Хэндлер для кнопки 'select_proxy'
@router.callback_query(F.data == 'select_proxy')
async def process_select_proxy(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил список представителей.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        members = await list_of_members_tg('proxy')

        if not members:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'В данный момент нет доступных представителей.'
            data['reply_markup'] = await user_menu(callback.from_user.id)

            # Редактируем сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
            return

        # Создаем кнопки для каждого представителя
        proxy_buttons = []
        for member in members:
            proxy_buttons.append(
                InlineKeyboardButton(
                    text=f"{member[0]} {member[1]}",  # Имя и Фамилия представителя
                    callback_data=f'trust_{member[2]}'  # tg_id представителя
                )
            )

        # Создаем инлайн-клавиатуру с кнопками
        markup = InlineKeyboardMarkup(row_width=1, inline_keyboard=[proxy_buttons])

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
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для доверия голоса
@router.callback_query(F.data.startswith('trust_'))
async def process_trust(callback: CallbackQuery, data: dict):
    try:
        proxy_tg_id = int(callback.data.split('_')[1])
        logging.info(f"Пользователь {callback.from_user.id} доверил свой голос пользователю с tg_id {proxy_tg_id}.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        flag, ans_str = await trust_tg(callback.from_user.id, proxy_tg_id)

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = ans_str
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

    except Exception as e:
        logging.error(f"Ошибка при доверии голоса: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при доверии голоса.'
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для кнопки 'become_proxy'
@router.callback_query(F.data == 'become_proxy')
async def process_become_proxy(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил статус 'proxy'.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = await extract_member_id(club_id, await extract_user_id(callback.from_user.id))
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь участником группы.'
            data['reply_markup'] = await user_menu(callback.from_user.id)

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
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки

# Хэндлер для кнопки ''resign_from_proxy''
@router.callback_query(F.data == 'resign_from_proxy')
async def process_resign_from_proxy(callback: CallbackQuery, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} отказывается от статуса 'proxy'.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = await extract_member_id(club_id, await extract_user_id(callback.from_user.id))
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Вы не являетесь участником группы.'
            data['reply_markup'] = await user_menu(callback.from_user.id)

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
        data['reply_markup'] = await user_menu(callback.from_user.id)

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки
