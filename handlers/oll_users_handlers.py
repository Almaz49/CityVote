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
from utils import log_handler_call
from LEXICON.LEXICON import LEXICON

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

# Хэндлер для текстовых сообщений, не являющихся командами
@router.message()
@log_handler_call
async def send_echo(message: Message,data:dict):
    """
    Обработчик эхо-сообщений.
    Отправляет обратно текстовые сообщения пользователя.
    """
    logging.info(f"Пользователь {message.from_user.id} отправил сообщение: {message.text}.")
    await message.answer(
        text=f'Вы написали: "{message.text}".\n'
             'Если вам нужна помощь, используйте команду /help.',
        reply_markup = await user_menu(message.from_user.id,data['user_status'])
    )




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