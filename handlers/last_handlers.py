# Модуль last_handlers
# В нем хэндлеры, которые работают для всех пользователей
import logging

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from LEXICON import get_text
from keyboards.keyboards import user_menu
from utils import log_handler_call

# Настройка логирования
logger = logging.getLogger(__name__)

# # Загружаем конфиг в переменную config
# config: Config = load_config(".env")

# Инициализируем роутер уровня модуля
router = Router()

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#       В самом конце !
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


# Хэндлер для текстовых сообщений, не являющихся командами
@router.message()
@log_handler_call
async def send_echo(message: Message, data: dict):
    """
    Обработчик эхо-сообщений.
    Отправляет обратно текстовые сообщения пользователя.
    """
    logger.info(f"Пользователь {message.from_user.id} отправил сообщение: {message.text}.")  # type: ignore
    text = message.text
    await message.answer(
#         text=f'Вы написали: "{message.text}".\n'
        text=get_text("last.you_written_value_n", lang=data.get("lang","ru")).format(text=text),
        reply_markup=await user_menu(status = data.get("user_status", ["user"]))
    )


# Хэндлер для нажатия на кнопку не пойманную другими хэндлерами
@router.callback_query()
@log_handler_call
async def send_echo_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик эхо-сообщений.
    Отправляет обратно текстовые сообщения пользователя.
    """
    logger.info(f"Пользователь {callback.from_user.id} нажал кнопку: {callback.data}.")
    butt_data = callback.data
    await callback.message.answer(  # type: ignore
#         text=f'Вы нажали кнопку: "{callback.data}".\n'
        text=get_text("last.you_pressed_button_value_n", lang=data.get("lang","ru")).format(butt_data=butt_data),
        reply_markup=await user_menu(status = data.get("user_status", ["user"])),
    )
