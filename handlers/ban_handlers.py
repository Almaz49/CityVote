# Модуль ban_handlers
# В нем хэндлеры, которые срабатывают для забаненных пользователей
import logging

from aiogram import Router
from aiogram.types import CallbackQuery, Message
from data_base.db_member import check_ban_status
from filters.filters import StatusFilter

from keyboards.keyboards import user_menu
from utils import log_handler_call

# Настройка логирования
logger = logging.getLogger(__name__)



# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status=["banned"]))
router.callback_query.filter(StatusFilter(required_status=["banned"]))

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#       Важен порядок роутеров!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


# Хэндлер для текстовых сообщений, не являющихся командами
@router.message()
@log_handler_call
async def ban_message_await(message: Message, data: dict):
    """
    Обработчик сообщений от пользователя, находящегося в бане.
    """
    member_id = data.get("member_id")
    if not member_id:
        raise ValueError("Нет member_id")
    ban_expiration = await check_ban_status(member_id)
    logger.info(f"Забаненный пользователь {message.from_user.id} отправил сообщение: {message.text}.")  # type: ignore
    await message.answer(
        text=f'Вы забанены в группе до: "{ban_expiration}".\n'
        "Вы по прежнему можете голосовать и доверять свой голос.\n"
        "В случае несогласия с баном, пожалуйста, свяжитесь с администратором.",
        reply_markup=await user_menu(status = data.get("user_status", ["user"]))
    )


# Хэндлер для нажатия на кнопку не пойманную другими хэндлерами
@router.callback_query()
@log_handler_call
async def ban_cb_await(callback: CallbackQuery, data: dict):
    """
    Обработчик нажатия кнопок пользователем, находящимся  бане.
    """
    member_id = data.get("member_id")
    if not member_id:
        raise ValueError("Нет member_id")
    ban_expiration = await check_ban_status(member_id)
    logger.info(f"Забаненный пользователь {callback.from_user.id} нажал кнопку: {callback.data}.")
    await callback.message.answer(  # type: ignore
        text=f'Вы забанены в группе до: "{ban_expiration}".\n'
        "Вы по прежнему можете голосовать и доверять свой голос.\n"
        "В случае несогласия с баном, пожалуйста, свяжитесь с администратором.",
        reply_markup=await user_menu(status = data.get("user_status", ["user"]))
    )
