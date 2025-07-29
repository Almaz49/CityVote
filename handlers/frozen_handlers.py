# Модуль frozen_handlers
# В нем хэндлеры, которые срабатывают для пользователей с истекшим токеном
import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from data_base.db_token_service import add_token_attempt, auto_approve_by_token, clear_old_attempts, get_token_attempts_count, is_valid_token
from data_base.db_func import get_profile
from filters.filters import StatusFilter
from aiogram.fsm.context import FSMContext
from FSMs.FSMs import FSMEnterToken
from keyboards.keyboards import create_inline_kb, return_to_main_menu_markup
from services.services import notify_super_registrator_short
from utils import log_handler_call

# Настройка логирования
logger = logging.getLogger(__name__)



# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status=["frozen"]))
router.callback_query.filter(StatusFilter(required_status=["frozen"]))

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#       Важен порядок роутеров!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

"""
Хэндлеры ввода нового токмена
"""
@router.callback_query(F.data == "enter_token")
@log_handler_call
async def enter_token(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик кнопки enter_token.
    """

    logger.info(f"Пользователь {callback.from_user.id} хочет ввести новый токен.")
    await callback.answer()
    if not callback.message:
        raise ValueError("Нет сообщения для ответа")
    member_id = data["member_id"]
    club_id = data["club_id"]


    # Очистка старых попыток ввода токена
    await clear_old_attempts(member_id)
    attempts = await get_token_attempts_count(member_id)
    if attempts >= 3:
        await callback.message.answer("Превышено количество попыток ввода токена.")
        return

    # Формируем сообщение: ввести токен
    text = (
        "Введите уникальный токен (если он у вас есть).\n"
    )

    markup = return_to_main_menu_markup

    # Сохраняем данные в middleware или контекст
    data["response_text"] = text
    data["reply_markup"] = markup

    if isinstance(callback.message, Message):
        current_text = callback.message.text
        current_markup = callback.message.reply_markup
        if current_text != text or current_markup != markup:
            await callback.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
    else:
        await callback.message.answer(text=text, reply_markup=markup)
    await state.set_state(FSMEnterToken.fill_token)


@router.message(StateFilter(FSMEnterToken.fill_token))
@log_handler_call
async def process_token(message: Message, state: FSMContext, data: dict):
    """
    Обработчик текстовых сообщений, введенных пользователем в машину состояний FSMEnterToken.
    В случае, если введен токен, то он проверяется на действительность.
    """
    if not message.text:
        await message.answer("Токен не может быть пустым. Попробуйте ещё раз:")
        return
    if not message.from_user:
        raise ValueError("Отправтель сообщения отсутствует (from_user == None)")
    token_input = message.text.strip()
    member_id = data["member_id"]
    club_id = data["club_id"]

    # Проверяем, похож ли ввод на токен
    clean_token = token_input.replace(" ", "").replace("-", "")
    if clean_token.isdigit():
        # Это токен — проверяем его валидность
        result = await is_valid_token(clean_token, club_id)
        if not result or result.get("status") not in ["valid"]:
            await message.answer(
                text = "Токен не действителен. Попробуйте снова или продолжите анкету.",
                reply_markup=return_to_main_menu_markup)
            await add_token_attempt(member_id)
            return
        token_id = result.get("token_id")
        if token_id:
            success, msg = await auto_approve_by_token(member_id, club_id, token_id)
            if success:
                await message.answer(text="Авторизация успешна! Вы участник группы.",
                    reply_markup=return_to_main_menu_markup)
                await state.clear()
                return
            else:
                await message.answer(text=msg,
                    reply_markup=return_to_main_menu_markup)
                await add_token_attempt(member_id)
                return
        else:
            await message.answer(text="Токен недействителен. Попробуйте снова или продолжите анкету.",
                reply_markup=return_to_main_menu_markup)
            await add_token_attempt(member_id)
            return
    else:
        # Это не токен
        logger.info(f"Вместо токена постпило сообщение: {token_input} от пользователя {member_id}")
        await message.answer(text="То, что вы ввели не похоже на токен. Попробуйте снова или наберите /cancel.",
                reply_markup=return_to_main_menu_markup)
        await state.set_state(FSMEnterToken.fill_token)

"""
Хэндлеры запроса нового токена
"""
@router.callback_query(F.data == "request_token")
@log_handler_call
async def request_token(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик кнопки request_token.
    """
    logger.info(f"Пользователь {callback.from_user.id} хочет получить новый токен.")
    if not callback.bot:
        raise ValueError("Бот не найден")
    bot = callback.bot

    await callback.answer()

    if not callback.message:
        raise ValueError("Нет сообщения для ответа")
    member_id = data["member_id"]
    club_id = data["club_id"]
    tg_id = callback.from_user.id
    status = data["status"]
    if 'member' not in status:  # type: ignore
        await callback.message.answer(text='Вы не зарегистрированы в группе. Пройдите регистрацию')  # type: ignore
        return
    profile = await get_profile(member_id)
    if not profile:  # type: ignore
        await callback.message.answer(text='Не найден профиль пользователя')  # type: ignore
        return
    profile['status'] = status
    success, result = await notify_super_registrator_short(bot=bot, club_id=club_id, candidate_tg_id= tg_id, user_dict= profile)
    if not success:
        await callback.message.answer(text=f"Ошибка при уведомлении супер-регистратора: {result}")
    else:
        await callback.message.answer(text=result)






"""
Хэндлеры, ловящие все сообщения от пользователя с просроченным или отсутствующим токеном
"""
# Хэндлер для текстовых сообщений, не являющихся командами
@router.message()
@log_handler_call
async def frozen_message_await(message: Message, data: dict):
    """
    Обработчик сообщений от пользователя, с просроченным или отсутствующим токеном.
    """
    logger.info(f"Замороженный пользователь {message.from_user.id} отправил сообщение: {message.text}.")  # type: ignore
    buttons = {
        "request_token":"Запросить токен",
        "enter_token":"Ввести токен"
    }
    markup = create_inline_kb(1, **buttons)
    await message.answer(
        text=f'У вас нет подтверждающего токена или истек срок его действия".\n'
        "Попросите у администрации новый токен.",
        reply_markup=markup,  # type: ignore
    )


# Хэндлер для нажатия на кнопку не пойманную другими хэндлерами
@router.callback_query()
@log_handler_call
async def frozen_cb_await(callback: CallbackQuery, data: dict):
    """
    Обработчик нажатия кнопок пользователем, находящимся  бане.
    """
    logger.info(f"Замороженный пользователь {callback.from_user.id} нажал кнопку: {callback.data}.")
    buttons = {
        "request_token":"Запросить токен",
        "enter_token":"Ввести токен"
    }
    markup = create_inline_kb(1, **buttons)
    await callback.message.answer(  # type: ignore
        text=f'У вас нет подтверждающего токена или истек срок его действия".\n'
        "Попросите у администрации новый токен.",
        reply_markup=markup,
    )