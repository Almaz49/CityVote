# Модуль oll_users_handlers
# В нем хэндлеры, которые работают для всех пользователей
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from keyboards.keyboards import user_menu, remove_markup, create_inline_kb
from config_data.config import Config, load_config
import logging

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
async def process_start_command(message: Message):
    """
    Обработчик команды /start.
    Отправляет приветственное сообщение и главное меню.
    """
    try:
        markup = await user_menu(message.from_user.id)
        await message.answer(
            text='Привет!\nЭто бот для проведения голосований',
            reply_markup=markup
        )
        logging.info(f"Пользователь {message.from_user.id} начал работу с ботом.")
    except Exception as e:
        logging.error(f"Ошибка при обработке команды /start: {e}")
        await message.answer(text="Произошла ошибка при загрузке главного меню.")

# Хэндлер для команды /help
@router.message(Command(commands=['help']))
async def process_help_command(message: Message):
    """
    Обработчик команды /help.
    Отправляет справочную информацию о боте.
    """
    logging.info(f"Пользователь {message.from_user.id} запросил справку.")
    await message.answer(
        text='Здесь будет описание функционала бота и инструкции по использованию.'
    )

# Хэндлер для нажатия на кнопку "помощь"
@router.callback_query(F.data == 'help')
async def process_help_callback(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку "помощь".
    Отправляет справочную информацию о боте.
    """
    logging.info(f"Пользователь {callback.from_user.id} запросил справку через кнопку.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Здесь будет описание функционала бота и инструкции по использованию.',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

# Хэндлер для команды /cancel в состоянии по умолчанию
@router.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    """
    Обработчик команды /cancel.
    Уведомляет пользователя, что команда работает только внутри машин состояний.
    """
    logging.info(f"Пользователь {message.from_user.id} попытался использовать /cancel вне машины состояний.")
    markup = await user_menu(message.from_user.id)
    await message.answer(
        text='Вы вышли в главное меню.',
        reply_markup=markup
    )

# Хэндлер для команды /cancel в любом состоянии, кроме состояния по умолчанию
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    """
    Обработчик команды /cancel.
    Завершает текущую машину состояний.
    """
    logging.info(f"Пользователь {message.from_user.id} вышел из машины состояний.")
    markup = await user_menu(message.from_user.id)
    await message.answer(
        text='Вы вышли из машины состояний и вернулись в главное меню.',
        reply_markup=markup
    )
    # Сбрасываем состояние и очищаем данные
    await state.clear()

# Хэндлер для текстовых сообщений, не являющихся командами
@router.message()
async def send_echo(message: Message):
    """
    Обработчик эхо-сообщений.
    Отправляет обратно текстовые сообщения пользователя.
    """
    logging.info(f"Пользователь {message.from_user.id} отправил сообщение: {message.text}.")
    await message.answer(
        text=f'Вы написали: "{message.text}".\n'
             'Если вам нужна помощь, используйте команду /help.',
        reply_markup = await user_menu(message.from_user.id)
    )

# Хэндлеры для кнопок основного меню
@router.callback_query(F.data.in_(['list_of_votes', 'archive_of_votes']))
async def process_vote_button(callback: CallbackQuery):
    """
    Обработчик кнопок голосований.
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Список голосований',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

@router.callback_query(F.data == 'select_proxy')
async def process_select_proxy_button(callback: CallbackQuery):
    """
    Обработчик кнопки выбора представителя.
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Выбор представителя',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

@router.callback_query(F.data == 'become_proxy')
async def process_become_proxy_button(callback: CallbackQuery):
    """
    Обработчик кнопки стать представителем.
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Стать представителем',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

@router.callback_query(F.data == 'resign_from_proxy')
async def process_resign_from_proxy_button(callback: CallbackQuery):
    """
    Обработчик кнопки отказаться от роли представителя.
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Отказаться от роли представителя',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

@router.callback_query(F.data == 'new_vote')
async def process_new_vote_button(callback: CallbackQuery):
    """
    Обработчик кнопки создания нового голосования.
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Создание нового голосования',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

@router.callback_query(F.data == 'new_variant')
async def process_new_variant_button(callback: CallbackQuery):
    """
    Обработчик кнопки создания нового варианта голосования.
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Создание нового варианта голосования',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

@router.callback_query(F.data == 'new_status')
async def process_new_status_button(callback: CallbackQuery):
    """
    Обработчик кнопки назначения нового статуса.
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.message.edit_text(
        text='Назначение нового статуса',
        reply_markup=create_inline_kb(1, 'back', 'main_menu')
    )

# Хэндлер для кнопки "назад"
@router.callback_query(F.data == 'back')
async def process_back_button(callback: CallbackQuery):
    """
    Обработчик кнопки "назад".
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    markup = await user_menu(callback.from_user.id)
    await callback.message.edit_text(
        text='Главное меню',
        reply_markup=markup
    )

# Хэндлер для кнопки "Главное меню"
@router.callback_query(F.data == 'main_menu')
async def process_main_menu_button(callback: CallbackQuery):
    """
    Обработчик кнопки "Главное меню".
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    markup = await user_menu(callback.from_user.id)
    await callback.message.edit_text(
        text='Главное меню',
        reply_markup=markup
    )

# Хэндлер для кнопки 'Главное меню' в основном состоянии
@router.callback_query(F.data == 'main_menu',StateFilter(default_state))
async def process_main_menu_button(callback: CallbackQuery):
    """
    Обработчик кнопки "Главное меню".
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    markup = await user_menu(callback.from_user.id)
    await callback.message.edit_text(
        text='Главное меню для администраторов:',
        reply_markup=markup
    )

# Хэндлер для кнопки 'Главное меню' внутри машины состояний.
@router.callback_query(F.data == 'main_menu',~StateFilter(default_state))
async def process_main_menu_button_state(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Главное меню".
    """
    logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    markup = await user_menu(callback.from_user.id)
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()
    await callback.message.edit_text(
        text='Главное меню для администраторов:',
        reply_markup=markup
    )