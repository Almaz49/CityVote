# Модуль reg_process_handlers
# Содержит хэндлеры процесса регистрации

import logging
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from data_base.db_member import new_status
from data_base.db_token_service import (clear_old_attempts, get_token_attempts_count,
                                        add_token_attempt, auto_approve_by_token, is_valid_token)
from data_base.telegram_bot_logic import get_club_info, list_of_members, new_status_tg, update_member_data, update_user_data
from services.services import notify_registrator_short, notify_super_registrator_short
from FSMs.FSMs import FSM_short_registration
from keyboards.keyboards import  user_menu
from LEXICON.LEXICON import LEXICON
from utils import log_handler_call


# Настройка логирования
logger = logging.getLogger(__name__)


# Инициализируем роутер уровня модуля
router = Router()
# -------------------------------------------
# Хэндлер для кнопки 'registration'
# -------------------------------------------

@router.callback_query(F.data == "registration")
@log_handler_call
async def process_registration(callback: CallbackQuery, state: FSMContext, data: dict):
    if not callback.message:
        raise ValueError("Нет сообщения для ответа")

    logger.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    if "member" in data["user_status"]:
        await callback.message.answer(text="Вы уже зарегистрированы в группе.")
        return

    member_id = data["member_id"]
    club_id = data["club_id"]

    club_info = await get_club_info(club_id)
    if not club_info:
        logger.error("Нет информации о группе")
        await callback.message.answer(text="Ошибка. Не найдена информация о группе")
        return

    # Очистка старых попыток ввода токена
    await clear_old_attempts(member_id)
    attempts = await get_token_attempts_count(member_id)
    if attempts >= 3:
        await callback.message.answer("Превышено количество попыток ввода токена.")
        return

    # Формируем сообщение: ввести токен ИЛИ ответить на вопросы
    questions = club_info.get("questions_for_the_candidate") or LEXICON.get("registration_message", "Напишите о себе")
    text = (
        "Введите уникальный токен (если он у вас есть).\n"
        "Если нет — ответьте на вопросы администрации.\n\n"
        f"{questions}"
    )

    markup = None  # Клавиатура пока не нужна

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

    await state.set_state(FSM_short_registration.enter_token)


# -------------------------------------------
# Хэндлер ввода токена или резюме
# -------------------------------------------

@router.message(StateFilter(FSM_short_registration.enter_token))
@log_handler_call
async def process_entered_token_or_resume(message: Message, state: FSMContext, data: dict):
    if not message.text:
        await message.answer("Введите текст.")
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
            await message.answer("Токен не действителен. Попробуйте снова или продолжите анкету.")
            await add_token_attempt(member_id)
            return
        token_id = result.get("token_id")
        if token_id:
            success, msg = await auto_approve_by_token(member_id, token_id)
            if success:
                await message.answer("Авторизация успешна! Вы участник группы.")
                await state.clear()
                return
            else:
                await message.answer(msg)
                await add_token_attempt(member_id)
                return
        else:
            await message.answer("Токен недействителен. Попробуйте снова или продолжите анкету.")
            await add_token_attempt(member_id)
            return
    else:
        # Это не токен → считаем, что это резюме
        logger.info(f"Введено резюме кандидата: {token_input} от пользователя {member_id}")


        await state.update_data(
            resume=token_input,
            member_id=member_id,
            tg_first_name=message.from_user.first_name,
            tg_last_name=message.from_user.last_name,
        )

        user_id = data.get("user_id")

        # Обновляем данные в БД
        if user_id:
            await update_user_data(user_id, tg_first_name=message.from_user.first_name, tg_last_name=message.from_user.last_name)
        if member_id:
            await update_member_data(member_id, resume=token_input)

        # Меняем статус на candidate
        success, result = await new_status(None, member_id, "candidate")
        if not success:
            await message.answer(result)
            return

        # Предлагаем выбрать регистратора
        registrators = await list_of_members("registrator")
        buttons = []
        for item in registrators:
            buttons.append([InlineKeyboardButton(text=item.get("username", "Unknown"), callback_data=str(item.get("tg_id")))])
        buttons.append([InlineKeyboardButton(text="Никого из регистраторов не знаю", callback_data="stranger")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            text="Спасибо!\nВыберите регистратора, которого знаете,\nчтобы он мог подтвердить вашу личность.\n"
                 "Если никого не знаете — нажмите 'Никого не знаю'",
            reply_markup=markup
        )
        await state.set_state(FSM_short_registration.fill_registrator)

        # Удаляем сообщение с инструкцией, если это возможно
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")


# -------------------------------------------
# Хэндлер для выбора регистратора
# -------------------------------------------

@router.callback_query(
    StateFilter(FSM_short_registration.fill_registrator),
    lambda x: x.data.isdigit() or x.data == "stranger",
)
@log_handler_call
async def process_registrator_choise(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Выбран регистратор {callback.data} пользователем {callback.from_user.id}")
        if not callback.message:
            raise Exception("Сообщение не найдено")
        if not callback.data:
            logger.info(f"Пользователь {callback.from_user.id} не выбрал регистратора")
            raise
        if callback.message and isinstance(callback.message, Message):
            try:
                await callback.message.delete()
            except Exception as del_err:
                logger.warning(f"Не удалось удалить сообщение: {del_err}")

        await state.update_data(familiar=callback.data)

        user_dict = await state.get_data()
        tg_id = callback.from_user.id
        member_id = data["member_id"]
        club_id = data["club_id"]
        instance_name = data["instance_name"]

        user_param = {
            "tg_phone_number": user_dict.get("tg_phone_number"),
            "tg_first_name": user_dict.get("tg_first_name"),
            "tg_last_name": user_dict.get("tg_last_name"),
        }
        await update_user_data(tg_id, **user_param)

        member_param = {"resume": user_dict.get("resume")}
        await update_member_data(member_id, **member_param)

        success, result = await new_status_tg(data.get("club_ud"), None, tg_id, "candidate")
        if not success:
            await callback.message.answer(text=result)
            return

        await state.clear()

        await callback.message.answer(
            text="Спасибо! Ваши данные сохранены.\n"
                 "Администрация их проверит и даст вам соответствующие права.\n"
                 "Вы вышли из машины состояний.",
            reply_markup=await user_menu(status= data.get("user_status", "user"))
        )

        if callback.data.isdigit():
            success, result = await notify_registrator_short(int(callback.data), tg_id, user_dict, instance_name)
            if not success:
                await callback.message.answer(text=f"Ошибка при уведомлении регистратора: {result}")
        elif callback.data == "stranger":
            success, result = await notify_super_registrator_short(club_id, tg_id, user_dict, instance_name)
            if not success:
                await callback.message.answer(text=f"Ошибка при уведомлении супер-регистратора: {result}")

    except Exception as e:
        logger.error(f"Ошибка при выборе регистратора: {e}")
        if callback.message:  # Если сообщение не пустое
            await callback.message.answer(text=f"Произошла ошибка: {str(e)}")
        await state.clear()