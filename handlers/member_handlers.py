from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from filters.filters import filter_isMember
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
async def process_list_of_votes(callback: CallbackQuery):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        votes = await list_of_votes_tg('ongoing', 'add_variants')
        if votes:
            text = 'Список голосований:\n'
            for vote in votes:
                text += f'- {vote[1]}\n'
            text += '\nВыберите голосование для участия:'
            markup = create_inline_kb(1, *[f'vote_{vote[0]}' for vote in votes], 'main_menu')
        else:
            text = 'В настоящее время нет активных голосований.'
            markup = create_inline_kb(1, 'main_menu')
        await callback.message.edit_text(
            text=text,
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'list_of_votes': {e}")
        await callback.message.edit_text(
            text='Произошла ошибка при загрузке списка голосований.',
            reply_markup=await user_menu(callback.from_user.id)
        )

# Хэндлер для выбора конкретного голосования
@router.callback_query(F.data.regexp(r'^vote_\d+$'))
async def process_vote_selection(callback: CallbackQuery):
    """
    Обработчик выбора конкретного голосования.
    """
    try:
        logging.info(f"Пользователь {callback.from_user.id} выбрал голосование: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        vote_id = int(callback.data.split('_')[1])
        variants = await list_of_variants(vote_id, 'valid')
        if variants:
            text = 'Выберите вариант голосования:\n'
            for variant in variants:
                text += f'- {variant[1]}\n'
            text += '\nВыберите вариант для голосования:'
            markup = create_inline_kb(1, *[f'variant_{variant[0]}' for variant in variants], 'main_menu')
        else:
            text = 'В настоящее время нет доступных вариантов для голосования.'
            markup = create_inline_kb(1, 'main_menu')
        await callback.message.edit_text(
            text=text,
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Ошибка при выборе конкретного голосования: {e}")
        await callback.message.edit_text(
            text='Произошла ошибка при выборе голосования.',
            reply_markup=await user_menu(callback.from_user.id)
        )

# Хэндлер для выбора конкретного варианта голосования
@router.callback_query(F.data.regexp(r'^variant_\d+$'))
async def process_variant_selection(callback: CallbackQuery):
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
        await callback.message.edit_text(
            text=text,
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Ошибка при выборе конкретного варианта голосования: {e}")
        await callback.message.edit_text(
            text='Произошла ошибка при голосовании.',
            reply_markup=await user_menu(callback.from_user.id)
        )

# Хэндлер для кнопки 'select_proxy'
@router.callback_query(F.data == 'select_proxy')
async def process_select_proxy(callback: CallbackQuery):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил список представителей.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        members = await list_of_members_tg('proxy')
        if not members:
            await callback.message.edit_text(text='В данный момент нет доступных представителей.',
                                          reply_markup=await user_menu(callback.from_user.id))
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
        await callback.message.edit_text(
            text='Выберите представителя, которому вы доверите свой голос:',
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")
        await callback.message.edit_text(
            text='Произошла ошибка при загрузке списка представителей.',
            reply_markup=await user_menu(callback.from_user.id)
        )

# Хэндлер для доверия голоса
@router.callback_query(F.data.startswith('trust_'))
async def process_trust(callback: CallbackQuery):
    try:
        proxy_tg_id = int(callback.data.split('_')[1])
        logging.info(f"Пользователь {callback.from_user.id} доверил свой голос пользователю с tg_id {proxy_tg_id}.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        flag, ans_str = await trust_tg(callback.from_user.id, proxy_tg_id)
        await callback.message.edit_text(
            text=ans_str,
            reply_markup=await user_menu(callback.from_user.id)
        )
    except Exception as e:
        logging.error(f"Ошибка при доверии голоса: {e}")
        await callback.message.edit_text(
            text='Произошла ошибка при доверии голоса.',
            reply_markup=await user_menu(callback.from_user.id)
        )

# Хэндлер для кнопки 'become_proxy'
@router.callback_query(F.data == 'become_proxy')
async def process_become_proxy(callback: CallbackQuery):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил статус 'proxy'.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        member_id = await extract_member_id(club_id, await extract_user_id(callback.from_user.id))
        if not member_id:
            await callback.message.edit_text(
                text='Вы не являетесь участником группы.',
                reply_markup=await user_menu(callback.from_user.id)
            )
            return
        # Присваиваем статус 'proxy'
        await new_status_tg(callback.from_user.id, callback.from_user.id, 'proxy')
        await callback.message.edit_text(
            text='Вы стали представителем!',
            reply_markup=await user_menu(callback.from_user.id)
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'become_proxy': {e}")
        await callback.message.edit_text(
            text='Произошла ошибка при присвоении статуса.',
            reply_markup=await user_menu(callback.from_user.id)
        )