import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, PhotoSize
from filters.filters import StatusFilter
from keyboards.keyboards import reg_markup, contact_markup, remove_markup
from config_data.config import Config, load_config
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from data_base.telegram_bot_logic import *
from utils import log_handler_call

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)
path_db = config.db.path_db  # путь к базе данных
club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status = 'candidate'))

"""
# Определяем состояния FSM для регистрации кандидата
class FSMRegistration(StatesGroup):
    fill_name = State()  # Состояние ожидания ввода имени
    fill_contact = State()  # Состояние ожидания отправки контакта

# Этот хэндлер будет срабатывать на команду "/start"
@router.message(Command(commands=["start"]))
async def process_start_command(message: Message, state: FSMContext):
    logging.info(f"Команда /start сработала для пользователя {message.from_user.id}")
    await message.answer(
        text='Привет, Кандидат!\nМеня зовут Эхо-бот!\nЧтобы зарегистрироваться, нажмите кнопку "Регистрация"',
        reply_markup=reg_markup
    )

# Этот хэндлер будет срабатывать на нажатие кнопки "Регистрация"
@router.callback_query(F.data == 'register')
async def process_register_press(callback: CallbackQuery, state: FSMContext):
    logging.info(f"Нажата кнопка 'Регистрация' пользователем {callback.from_user.id}")
    await callback.message.edit_text(
        text='Пожалуйста, введите ваше имя'
    )
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(FSMRegistration.fill_name)

# Этот хэндлер будет срабатывать на ввод имени кандидата
@router.message(StateFilter(FSMRegistration.fill_name))
async def process_name_sent(message: Message, state: FSMContext):
    logging.info(f"Введено имя кандидата: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем введенное имя в контексте состояния
    await state.update_data(name=message.text)
    await message.answer(
        text='Пожалуйста, отправьте свой контакт',
        reply_markup=contact_markup
    )
    # Устанавливаем состояние ожидания отправки контакта
    await state.set_state(FSMRegistration.fill_contact)

# Этот хэндлер будет срабатывать на отправку контакта кандидата
@router.message(StateFilter(FSMRegistration.fill_contact), F.content_type == 'contact')
async def process_contact_sent(message: Message, state: FSMContext):
    logging.info(f"Отправлен контакт кандидата от пользователя {message.from_user.id}")
    # Получаем сохраненные данные из контекста состояния
    user_data = await state.get_data()
    name = user_data['name']
    contact = message.contact.phone_number

    try:
        # Выполняем регистрацию кандидата в базе данных
        await new_user_tg(message.from_user.id)
        user_id = await extract_user_id(message.from_user.id)
        if user_id:
            await new_member(club_id, user_id)
            await message.answer(
                text=f'Спасибо за регистрацию, {name}! Ваш контактный телефон: {contact}. \nОжидайте подтверждения.',
                reply_markup=remove_markup
            )
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
        else:
            await message.answer(
                text='Произошла ошибка при регистрации. Попробуйте снова.',
                reply_markup=remove_markup
            )
            await state.clear()
    except Exception as e:
        logging.error(f"Ошибка при регистрации кандидата: {e}")
        await message.answer(
            text='Произошла ошибка при регистрации. Попробуйте снова.',
            reply_markup=remove_markup
        )
        await state.clear()

# Этот хэндлер будет срабатывать на некорректный ввод в состоянии ожидания имени или контакта
@router.message(StateFilter(FSMRegistration.fill_name, FSMRegistration.fill_contact))
async def warning_registration(message: Message):
    logging.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {await state.get_state()}")
    await message.answer(
        text='Пожалуйста, следуйте инструкциям.\nЕсли вы хотите прервать регистрацию - отправьте команду /cancel'
    )
"""