# Модуль oll_users_handlers
# В нем хэндлеры, которые работают для всех пользователей
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext
from keyboards.keyboards import user_menu, remove_markup
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


# Хэндлер для неизвестных пользователей (не должен срабатывать)
@router.message(Command(commands=["start"]))
async def process_start_command6(message: Message):
    """
    Обработчик для неизвестных пользователей.
    Предупреждает пользователя, что он не зарегистрирован.
    """
    logging.warning(f"Неизвестный пользователь {message.from_user.id} пытается начать работу с ботом.")
    await message.answer(
        text='Привет, Незнакомец!\nМеня зовут Эхо-бот!\nНапишите администратору для регистрации.'
    )


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


# Хэндлер для команды /cancel в состоянии по умолчанию
@router.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    """
    Обработчик команды /cancel.
    Уведомляет пользователя, что команда работает только внутри машин состояний.
    """
    logging.info(f"Пользователь {message.from_user.id} попытался использовать /cancel вне машины состояний.")
    await message.answer(
        text='Отменять нечего. Вы находитесь вне машины состояний.',
        reply_markup=remove_markup
    )


# Хэндлер для команды /cancel в любом состоянии, кроме состояния по умолчанию
@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    """
    Обработчик команды /cancel.
    Завершает текущую машину состояний.
    """
    logging.info(f"Пользователь {message.from_user.id} вышел из машины состояний.")
    await message.answer(
        text='Вы вышли из машины состояний.',
        reply_markup=remove_markup
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
             'Если вам нужна помощь, используйте команду /help.'
    )
