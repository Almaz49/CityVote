# Модуль reg_process_handlers
# Содержит хэндлеры процесса регистрации

import logging

from aiogram import F, Bot, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from data_base.telegram_bot_logic import (get_club_info, list_of_members,
                                          new_status_tg, update_member_data,
                                          update_user_data)
from FSMs.FSMs import FSM_short_registration
from keyboards.keyboards import return_to_main_menu_markup, user_menu
from LEXICON.LEXICON import LEXICON
from services.services import (notify_registrator_short,
                               notify_super_registrator_short)
from utils import log_handler_call

# Настройка логирования
logger = logging.getLogger(__name__)


# Инициализируем роутер уровня модуля
router = Router()

# -------------------------------------------
# Хэндлеры самой упрощенной регистрации участника
# Не запрашивается даже контакт.
# -------------------------------------------


# Хэндлер для кнопки 'registration'
@router.callback_query(F.data == "registration")
@log_handler_call
async def process_registration(callback: CallbackQuery, state: FSMContext, data: dict):
    if not callback.message:
        raise ValueError("Нет сообщения для ответа")
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        if "member" in data["user_status"]:
            await callback.message.answer(  # type: ignore
                text="Вы уже зарегистрированы в группе",
                reply_markup=return_to_main_menu_markup,
            )
            return

        tg_id = callback.from_user.id
        club_id = data["club_id"]
        club_info = await get_club_info(club_id)
        if not club_info:
            logger.error("Нет информации о группе")
            await callback.message.answer(text="Ошибка. Не найдена информация о группе")  # type: ignore
            return

        # Логируем club_info для отладки
        logger.debug(f"Club info: {club_info}")

        text0 = LEXICON.get("registration_message", "Напишите о себе")
        text1 = LEXICON.get("reg_cancel_info")

        # Проверяем, что club_info содержит вопросы
        questions = club_info.get("questions_for_the_candidate")
        if questions is None:
            questions = text0  # Используем текст по умолчанию, если вопроса нет

        text = questions + "\n" + text1
        markup = None  # Не нужна клавиатура

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Убеждаемся, что это доступное сообщение
        if not isinstance(callback.message, Message):
            logger.warning("Сообщение недоступно (InaccessibleMessage)")
            await callback.answer("Сообщение недоступно")
            return

        # Теперь можно безопасно использовать .text и .reply_markup
        current_text = callback.message.text
        current_markup = callback.message.reply_markup
        if (
            current_text != data["response_text"]
            or current_markup != data["reply_markup"]
        ):
            await callback.message.edit_text(
                text=data["response_text"],
                reply_markup=data["reply_markup"],
                parse_mode="HTML",
            )
        else:
            logger.info("Сообщение не изменено, так как содержимое совпадает.")

        # Устанавливаем состояние
        await state.set_state(FSM_short_registration.fill_resume)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'registration': {e}")
        logger.error(f"Текущие данные: {data}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при начале процесса регистрации."
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Пытаемся отредактировать сообщение
        try:
            await callback.message.edit_text(  # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
        except Exception as edit_error:
            logger.error(f"Ошибка при редактировании сообщения: {edit_error}")

        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать, если введено корректное резюме
@router.message(StateFilter(FSM_short_registration.fill_resume))
@log_handler_call
async def process_resume_sent(message: Message, state: FSMContext, data: dict):
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user.id == None)")
    logger.info(
        f"Введено резюме кандидата: {message.text} от пользователя {message.from_user.id}"
    )
    # Сохраняем введенное имя в контексте состояния
    await state.update_data(
        resume=message.text,
        tg_id=message.from_user.id,
        tg_first_name=message.from_user.first_name,
        tg_last_name=message.from_user.last_name,
    )

    # Создаем инлайн-кнопки для выбора регистратора
    registrators = await list_of_members("registrator")
    buttons: list[list[InlineKeyboardButton]] = []
    for item in registrators:
        username = item.get("username", "Unknown")
        tg_id = item.get("tg_id")
        buttons.append([InlineKeyboardButton(text=username, callback_data=str(tg_id))])

    buttons.append(
        [
            InlineKeyboardButton(
                text="Никого из регистраторов не знаю", callback_data="stranger"
            )
        ]
    )

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем пользователю клавиатуру для выбора регистратора
    await message.answer(
        text="Спасибо!\nВыберите регистратора, которого знаете,\nчтобы он смог подтвердить вашу личность\nЕсли никого не знаете,\nНажмите кнопку 'Никого не знаю'",
        reply_markup=markup,  # клавиатура подтверждения
    )
    # Устанавливаем состояние ожидания выбора регистратора
    await state.set_state(FSM_short_registration.fill_registrator)


# Этот хэндлер будет срабатывать на выбор регистратора
@router.callback_query(
    StateFilter(FSM_short_registration.fill_registrator),
    lambda x: x.data.isdigit() or x.data == "stranger",
)
@log_handler_call
async def process_registrator_choise(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    try:
        logger.info(
            f"Выбран регистратор {callback.data} пользователем {callback.from_user.id}"
        )

        # Удаляем сообщение с кнопками подтверждения, если доступно
        if callback.message and isinstance(callback.message, Message):
            try:
                await callback.message.delete()
            except Exception as del_err:
                logger.warning(f"Не удалось удалить сообщение: {del_err}")
        else:
            logger.warning(
                "Сообщение недоступно для удаления (InaccessibleMessage или None)"
            )

        # Сохраняем знакомого модератора (callback.data нажатой кнопки) в контексте состояния по ключу "familiar"
        await state.update_data(familiar=callback.data)
        tg_id = callback.from_user.id

        # Заносим данные регистрации в строку соответствующего пользователя в базе данных
        user_dict = await state.get_data()

        # Записываем в базу данных сведения об участнике
        user_param = {}
        user_param["tg_phone_number"] = user_dict.get("tg_phone_number")
        user_param["tg_first_name"] = user_dict.get("tg_first_name")
        user_param["tg_last_name"] = user_dict.get("tg_last_name")
        await update_user_data(tg_id, **user_param)

        member_id = data["member_id"]
        club_id = data["club_id"]
        instance_name = data["instance_name"]
        member_param = {}
        member_param["resume"] = user_dict.get("resume")
        await update_member_data(member_id, **member_param)

        # Меняем статус пользователя на 'candidate'
        success, result = await new_status_tg(
            club_id, None, tg_id, "candidate"
        )  # меняем статус пользователя на 'candidate'
        if not success:
            await callback.message.answer(text=result)  # type: ignore
            return

        # Завершаем машину состояний
        await state.clear()

        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.answer(  # type: ignore
            text="Спасибо! Ваши данные сохранены.\nАдминистрация их проверит и даст вам соответствующие права\nВы вышли из машины состояний",
            reply_markup=await user_menu(status= data.get("user_status", "user"))
        )

        # Проверяем, что callback.data существует
        if not callback.data:
            logger.warning("Данные callback пусты")
            await callback.message.edit_text("Произошла ошибка: данные не найдены.")  # type: ignore
            raise ValueError("Callback data отсутствует")

        if not callback.bot:
            raise ValueError("Не удалось получить бота")
        bot:Bot = callback.bot

        # Если выбран регистратор, отправляем ему сообщение с просьбой подтвердить регистрацию
        if callback.data.isdigit():
            success, result = await notify_registrator_short(
                bot, int(callback.data), tg_id, user_dict, instance_name
            )
            if not success:
                await callback.message.answer(text=f"Ошибка при уведомлении регистратора: {result}")  # type: ignore
        elif callback.data == "stranger":
            logger.info(f"Пользователь {tg_id} выбрал 'Никого не знаю'.")
            club_id = data["club_id"]
            instance_name = data["instance_name"]
            success, result = await notify_super_registrator_short(bot, club_id, tg_id, user_dict, instance_name)
            if not success:
                await callback.message.answer(text=f"Ошибка при уведомлении супер-регистратора: {result}")  # type: ignore
            # Здесь тоже нужна функция уведомления администрации
    except Exception as e:
        logger.error(f"Ошибка при выборе регистратора: {e}")
        await callback.message.answer(text=f"Произошла ошибка: {str(e)}")  # type: ignore
        # Завершаем машину состояний
        await state.clear()


# Этот хэндлер будет срабатывать, если во время выбора регистратора
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSM_short_registration.fill_registrator))
@log_handler_call
async def warning_not_registrator(message: Message):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(
        f"Некорректный ввод при выборе модератора от пользователя {message.from_user.id}"
    )
    await message.answer(
        text="Пожалуйста, пользуйтесь кнопками при выборе модератора.\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel"
    )
