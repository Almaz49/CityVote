from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from filters.filters import filter_isMember
from keyboards.keyboards import reg_markup, contact_markup, remove_markup
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import *
# Инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)
# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(filter_isMember)

# Хэндлер для кнопки 'list_of_votes'
@log_function_call
@router.callback_query(F.data == 'list_of_votes')
async def process_list_of_votes(callback: CallbackQuery):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил список голосований.")
        status = 'add_variants','ongoing'
        votes = await list_of_votes_tg(*status)
        if not votes:
            await callback.message.answer(text='В данный момент нет активных голосований.')
            return

        # Создаем кнопки для каждого голосования
        vote_buttons = []
        for vote in votes:
            vote_buttons.append(
                InlineKeyboardButton(
                    text=vote[1],  # Название голосования
                    callback_data=f'vote_{vote[0]}'  # ID голосования
                )
            )

        # Создаем инлайн-клавиатуру с кнопками
        markup = InlineKeyboardMarkup(row_width=1, inline_keyboard=[vote_buttons])

        await callback.message.answer(
            text='Выберите голосование:',
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'list_of_votes': {e}")
        await callback.message.answer(text='Произошла ошибка при загрузке списка голосований.')

# Хэндлер для кнопки 'select_proxy'
@router.callback_query(F.data == 'select_proxy')
async def process_select_proxy(callback: CallbackQuery):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил список представителей.")
        members = await list_of_members_tg('proxy')
        if not members:
            await callback.message.answer(text='В данный момент нет доступных представителей.')
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

        await callback.message.answer(
            text='Выберите представителя, которому вы доверите свой голос:',
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")
        await callback.message.answer(text='Произошла ошибка при загрузке списка представителей.')

# Хэндлер для кнопки 'become_proxy'
@router.callback_query(F.data == 'become_proxy')
async def process_become_proxy(callback: CallbackQuery):
    try:
        logging.info(f"Пользователь {callback.from_user.id} запросил статус 'proxy'.")
        member_id = await extract_member_id(club_id, await extract_user_id(callback.from_user.id))
        if not member_id:
            await callback.message.answer(text='Вы не являетесь участником группы.')
            return

        # Присваиваем статус 'proxy'
        await new_status_tg(callback.from_user.id, callback.from_user.id, 'proxy')
        await callback.message.answer(text='Вы стали представителем!')
    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'become_proxy': {e}")
        await callback.message.answer(text='Произошла ошибка при присвоении статуса.')

# Хэндлер для обработки выбора голосования
@router.callback_query(F.data.startswith('vote_'))
async def process_vote_selection(callback: CallbackQuery):
    try:
        vote_id = int(callback.data.split('_')[1])
        logging.info(f"Пользователь {callback.from_user.id} выбрал голосование с ID {vote_id}.")
        await callback.message.answer(text='Выбранное голосование:')
        # Добавьте здесь логику для обработки выбранного голосования
    except Exception as e:
        logging.error(f"Ошибка при обработке выбора голосования: {e}")
        await callback.message.answer(text='Произошла ошибка при выборе голосования.')

# Хэндлер для доверия голоса
@router.callback_query(F.data.startswith('trust_'))
async def process_trust(callback: CallbackQuery):
    try:
        proxy_tg_id = int(callback.data.split('_')[1])
        logging.info(f"Пользователь {callback.from_user.id} доверил свой голос пользователю с tg_id {proxy_tg_id}.")
        flag, ans_str = await trust_tg(callback.from_user.id, proxy_tg_id)
        if flag:
            await callback.message.answer(text=ans_str)
        else:
            await callback.message.answer(text=ans_str)
    except Exception as e:
        logging.error(f"Ошибка при доверии голоса: {e}")
        await callback.message.answer(text='Произошла ошибка при доверии голоса.')