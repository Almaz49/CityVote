from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3

from filters.filters import filter_isDelegate
from FSMs.FSMs import FSMNewVoting, FSMNewVariant
from keyboards.keyboards import *
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import *

#инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)


# Инициализируем роутер уровня модуля
router = Router()
#Навешиваем на роутер фильтр, проверяющий, является ли пользователь Делегатом
router.message.filter(filter_isDelegate)



# Этот хэндлеры будет срабатывать на команду "/start"

@router.message(Command(commands=["start"]))
async def process_start_command1(message: Message):
    await bot.send_message(message.from_user.id,
        text='Привет, Делегат!\nМеня зовут Эхо-бот!\nНапиши мне что-нибудь')
    


"""
СОЗДАНИЕ ГОЛОСОВАНИЯ
"""

# Этот хэндлер будет срабатывать на команду /new_vote
# и переводить бота в состояние ожидания ввода названия голосования
@router.message(Command(commands='new_vote'), StateFilter(default_state))
async def process_new_voting_start(message: Message, state: FSMContext):
    await message.answer(text='Пожалуйста, введите название голосования')
    # Устанавливаем состояние ожидания ввода названия
    await state.set_state(FSMNewVoting.fill_vote_title)


# Этот хэндлер будет срабатывать на ввод названия
# и переводить бота в состояние ожидания ввода описания голосования
@router.message(StateFilter(FSMNewVoting.fill_vote_title))
async def process_new_voting_title_sent(message: Message, state: FSMContext):
    # Cохраняем название в хранилище по ключу "title"
    await state.update_data(title = message.text)
    await message.answer(text='Пожалуйста, введите описание голосования')
    # Устанавливаем состояние ожидания ввода названия
    await state.set_state(FSMNewVoting.fill_vote_description)



# Этот хэндлер будет срабатывать, после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVoting.fill_vote_description))
async def process_new_voting_description_sent(message: Message, state: FSMContext):
    # Cохраняем название в хранилище по ключу "description"
    await state.update_data(description = message.text)
    data = await state.get_data()
    title = data['title']
    description = message.text
#здесь создание кнопок, если надо    
    await message.answer(text=f'''Пожалуйста, подтвердите, правильно ли введены
                         название и описание голосования?
                         Название:
                         {title}
                         Текст:
                         {description}
                         
                         ''',
                         reply_markup=confirm_markup
                         )

    # Устанавливаем состояние ожидания ввода подтверждения
    await state.set_state(FSMNewVoting.fill_OK)



# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK),
                   F.data == 'ConfirmOK')
async def process_new_voting_yes_confirm_press(callback: CallbackQuery, state: FSMContext):
    # Заносим в базу данных голосование
    # по ключу tg_id пользователя b tg_id регистратора (админа в данном случае)
    data = await state.get_data()
    title = data['title']
    description = data['description']
    tg_id = callback.from_user.id
#     Записываем новое голосование в базу данных
    flag,answ_str = new_vote_tg(creator_tg_id=tg_id, title=title, text=description, vote_status='add_variants')
    if flag:
        await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.edit_text(
        text='Спасибо! Голосование создано!'
             'Вы вышли из машины состояний'
        )
    else:
        await callback.message.edit_text(text = answ_str)

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK),
                   F.data == 'ConfirmNotOK')    
async def process_new_voting_no_confirm_press(callback: CallbackQuery, state: FSMContext):
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Голосование не создано!'
        'Попробуйте еще раз.'
        'Вы вышли из машины состояний'
        )


"""
Добавление варианта
"""

# Этот хэндлер будет срабатывать на команду /new_variant
# и переводить бота в состояние ожидания выбора голосования
# к которому добавляется вариант
@router.message(Command(commands='new_variant'), StateFilter(default_state))
async def process_new_variant_start(message: Message, state: FSMContext):
    list_of_votes = list_of_votes_tg('add_variants')
    if list_of_votes:
        keyboards = {}
        for item in list_of_votes:
            keyboards[str(item[0])] = item[1]
        markup = create_inline_kb(1,**keyboards)
    else:
        await message.answer(text = 'Сейчас нет активных голосований,'
        'вы не можете добавить вариант')
        return()
    

    # Устанавливаем состояние ожидания ввода названия
    await message.answer(text='''Пожалуйста, выберите, к какому голосованию
    вы хотите добавить вариант''',
    reply_markup = markup
    )
    await state.set_state(FSMNewVariant.fill_vote_choise)

#Этот хэндлер будет срабатывать на нажатие кнопки с названием голосования
@router.callback_query(StateFilter(FSMNewVariant.fill_vote_choise), F.data)
async def process_variant_title_sent(callback: CallbackQuery, state: FSMContext):
    # Cохраняем ID голосования по ключу vote_id
    await state.update_data(vote_id=int(callback.data))
    # Удаляем сообщение с кнопками
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.edit_text(text='Пожалуйста, введите название варианта',
        reply_markup=None)
    await state.set_state(FSMNewVariant.fill_variant_title)
    


# Этот хэндлер будет срабатывать на ввод названия варианта
# и переводить бота в состояние ожидания ввода описания голосования
@router.message(StateFilter(FSMNewVariant.fill_variant_title))
async def process_variant_description_sent(message: Message, state: FSMContext):
    # Cохраняем название в хранилище по ключу "title"
    await state.update_data(title = message.text)
    await message.answer(text='Пожалуйста, введите описание варианта')
    # Устанавливаем состояние ожидания ввода названия
    await state.set_state(FSMNewVariant.fill_variant_description)



# Этот хэндлер будет срабатывать, после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVariant.fill_variant_description))
async def process_new_variant_description_sent(message: Message, state: FSMContext):
    # Cохраняем название в хранилище по ключу "description"
    await state.update_data(description = message.text)
    data = await state.get_data()
    title = data['title']
    description = message.text
#здесь создание кнопок, если надо    
    await message.answer(text=f'''Пожалуйста, подтвердите, правильно ли введены
                         название и описание варианта?
                         Название:
                         {title}
                         Текст:
                         {description}
                         
                         ''',
                         reply_markup=confirm_markup
                         )

    # Устанавливаем состояние ожидания ввода подтверждения
    await state.set_state(FSMNewVariant.fill_OK)



# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVariant.fill_OK),
                   F.data == 'ConfirmOK')
async def process_new_variant_yes_confirm_press(callback: CallbackQuery, state: FSMContext):
    # Заносим в базу данных голосование
    # по ключу tg_id пользователя b tg_id регистратора (админа в данном случае)
    data = await state.get_data()
    vote_id = data['vote_id']
    title = data['title']
    description = data['description']
    tg_id = callback.from_user.id
#     Записываем новое голосование в базу данных
    new_variant_tg(vote_id=vote_id, tg_id=tg_id, title=title, text=description)


    await callback.message.edit_text(
        text='Спасибо! Вариант создано!\n'
             'Хотите ли добавить ещё вариант?',
        reply_markup = variant_markup
        )
    await state.set_state(FSMNewVariant.fill_more_variant)

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK),
                   F.data == 'ConfirmNotOK')    
async def process_new_variant_no_confirm_press(callback: CallbackQuery, state: FSMContext):
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Вариант не создан!'
             'Хотите ли добавить другой вариант?',
        reply_markup = variant_markup
        )
    await state.set_state(FSMNewVariant.fill_more_variant)
    
# Этот хэндлер будет срабатывать на нажатие кнопки "Добавить ещё вараинт"
# Откатываем машину состояния в точку ввода названия варианта
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant),
                   F.data == 'NewVariant')
async def process_more_variant(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text='Пожалуйста, введите название варианта')
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на нажатие кнопки "Завершить добавление вариантов"
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant),
                   F.data == 'Finish_Variant')
async def process_finish_variant(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Спасибо! Голосование создано!\n'
             'Вы вышли из машины состояний'
        )