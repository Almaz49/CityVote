# Модуль admin_handlers , сожержит хэндлеры для админов и владельца группы

import logging
import os

from aiogram import F, Bot, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Contact, Message)
from data_base.db_func import extract_user_member_id, get_profile
from data_base.db_member import ban_member, new_status, export_list_of_members
from data_base.db_vote import delete_variant
from data_base.telegram_bot_logic import extract_new_registrator_data, new_status_tg
from filters.filters import StatusFilter
from FSMs.FSMs import FSMExportMembers, FSMNewRegistrator, FSMBan, FSMTextMailing
from keyboards.keyboards import *
from manager.manager import *
from services.services import send_file_to_user, send_notification_to_members, send_notification_to_user
from utils import log_handler_call, safe_edit
from LEXICON import get_text

# Настройка логирования
logger = logging.getLogger(__name__)


# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status=["admin", "owner"]))
router.callback_query.filter(StatusFilter(required_status=["admin", "owner"]))


"""
Хэндлеры FSM создания нового регистратора
"""


# Этот хэндлер будет срабатывать на команду /new_registrator
# и переводить бота в состояние ожидания ввода ID нового регистратора
@router.message(Command(commands="new_registrator"), StateFilter(default_state))
@log_handler_call
async def process_new_registrator(message: Message, state: FSMContext, data: dict):
    lang = data.get("lang", "ru")
    if message.from_user is None:
        logger.warning("Сообщение от пользователя без данных from_user")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
        return

    logger.info(
        f"Команда /new_registrator сработала для пользователя {message.from_user.id}"
    )
    await message.answer(text=get_text("admin.process_new_registrator", lang=lang))
    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMNewRegistrator.fill_ID_NewRegistrator)


# Этот хэндлер будет срабатывать на нажатие кнопки "новый регистратор" в меню админа
@router.callback_query(StateFilter(default_state), F.data == "new_registrator")
@log_handler_call
async def process_new_registrator_cb(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    lang = data["lang"]
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = get_text("admin.process_new_registrator", lang=lang)
    data["reply_markup"] = None  # Если клавиатура не нужна, устанавливаем None

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )
    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMNewRegistrator.fill_ID_NewRegistrator)


# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# или отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(
    StateFilter(FSMNewRegistrator.fill_ID_NewRegistrator), (lambda x: x.text.isdigit())
)
@log_handler_call
async def process_registrator_id_sent(message: Message, state: FSMContext, data: dict):
    lang = data["lang"]
    # Проверяем, что message.text существует и является строкой
    if message.text is None:
        logger.warning("Получено сообщение без текста")
        await message.answer(get_text("admin.process_registrator_id_sent&no_text", lang=lang))
        return

    logger.info(f"Введенный ID нового регистратора: {message.text} от пользователя {message.from_user.id}")  # type: ignore

    # Преобразуем текст в целое число
    member_tg_id = int(message.text)
    await state.update_data(ID=member_tg_id)

    # Извлекаем данные о новом регистраторе
    club_id = data.get("club_id")
    if not club_id:  # Если club_id не существует
        logger.warning("club_id не существует")
        raise ValueError("club_id не существует")

    user_id, member_id = await extract_user_member_id(club_id, member_tg_id)
    if not member_id:  # Если member_id не существует
        logger.warning("member_id не существует")
        await message.answer(get_text("admin.process_registrator_id_sent&no_member_id", lang=lang))
        return
    profile = await get_profile(member_id)
    if profile != {}:
        # Создаем объект инлайн-клавиатуры
        markup = confirm_markup(lang=data.get("lang","en"))

        # TODO: Вместо этого использовать get_text

        short_profile = {
        'id': profile.get('member_id'),
        'first_name': profile.get('first_name') or profile.get('tg_first_name') or get_text("not specified", lang=lang),
        'last_name': profile.get('last_name') or profile.get('tg_last_name') or get_text("not specified", lang=lang),
        'username': profile.get('username') or get_text("not specified", lang=lang),
        'description': profile.get('description') or get_text("not specified", lang=lang)
    }


        user_info = get_text("profile_info",lang=lang).format(**short_profile)
        # Добавляем данные для SafeEditMiddleware
        response_text = get_text("admin.confirm_new_registrator", lang=lang).format(user_info=user_info)
        data["response_text"] = response_text
        data["reply_markup"] = markup

        # Отправляем пользователю сообщение с клавиатурой
        await message.answer(
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Устанавливаем состояние ожидания подтверждения
        await state.set_state(FSMNewRegistrator.fill_OK)

    else:
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.process_registrator_profile_not_found", lang=lang)
        data["reply_markup"] = main_menu_markup(lang=lang)

        # Отправляем сообщение об ошибке
        await message.answer(
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Сбрасываем состояние и очищаем данные
        await state.clear()


# Этот хэндлер будет срабатывать, если отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewRegistrator.fill_ID_NewRegistrator), F.contact)
@log_handler_call
async def process_registrator_contact_sent(
    message: Message, state: FSMContext, data: dict
):
    lang = data["lang"]
    # Проверяем, что контакт существует
    if message.contact is None:
        logger.warning("Получено сообщение без контакта")
        await message.answer(get_text("admin.process_registrator_contact_sent&no_contact", lang=lang)
        )
        return

    contact = message.contact

    # Проверяем, что from_user существует
    if message.from_user is None:
        logger.warning("Сообщение от пользователя без данных from_user")
        await message.answer(
            text=get_text("An error occurred, please try again", lang=lang)
)
        return

    logger.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")
    member_tg_id = contact.user_id
    if not member_tg_id:  # Если member_tg_id не существует
        logger.warning("member_tg_id не существует")
        raise ValueError("member_tg_id не существует")
    club_id = data.get("club_id")
    if not club_id:  # Если club_id не существует
        logger.warning("club_id не существует")
        raise ValueError("club_id не существует")

    flag, ans_str = await extract_new_registrator_data(
       club_id, member_tg_id
    )  # извлекаем данные о новом регистраторе

    # Создаем объект инлайн-клавиатуры
    markup = confirm_markup(lang=data.get("lang","en"))

    if flag:
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = (get_text("admin.confirm_new_registrator", lang=lang).format(user_info=ans_str))
        data["reply_markup"] = markup

        # Отправляем пользователю сообщение с клавиатурой
        await message.answer(
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Устанавливаем состояние ожидания подтверждения
        await state.set_state(FSMNewRegistrator.fill_OK)

    else:
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = ans_str
        data["reply_markup"] = None  # Клавиатура не нужна

        # Отправляем сообщение об ошибке
        await message.answer(
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Сбрасываем состояние и очищаем данные
        await state.clear()


# Хэндлер для обработки нажатии кнопки ВСЁ ВЕРНО
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def process_yes_registrator_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    lang = data["lang"]
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot

    # Меняем в базе данных статус пользователя по ключу tg_id пользователя и tg_id регистратора
    fsm_data = await state.get_data()
    member_tg_id = fsm_data["ID"]
    if not member_tg_id:
        await callback.message.answer(get_text("admin.failed_to_get_participant_id",lang=lang)) # type: ignore
        return
    admin_tg_id = callback.from_user.id
    admin_id = data["member_id"]
    club_id = data["club_id"]


    try:
        ans_str = await new_status_tg(club_id,
            admin_tg_id, member_tg_id, "pre-registrator"
        )  # Вызов функции присвоения нового статуса
        if isinstance(ans_str, str) and "Ошибка" in ans_str:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (get_text("admin.error_during_registrator_assignment", lang=lang).format(ans_str=ans_str))
            data["reply_markup"] = await user_menu(
                status = data.get("user_status", ["user"])
            )
            # Пытаемся отредактировать сообщение
            await safe_edit(callback, text=data["response_text"], reply_markup=data["reply_markup"])  # type: ignore
            return

        # Завершаем машину состояний
        await state.clear()

        # Формируем и отправляем запрос кандидату в регистраторы - согласен ли он

        notification = get_text("admin.registrator_invitation_message", lang=lang)

        keyboard = {
            f"pre_registrator_yes:{admin_id}:{member_tg_id}": "Согласен",
            f"pre_registrator_no:{admin_id}:{member_tg_id}": "Не согласен",
        }

        pre_reg_markup = create_inline_kb(2, **keyboard)

        response = await send_notification_to_user(
            bot, member_tg_id, notification, pre_reg_markup
        )

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.registrator_added_success", lang=lang).format(response=response)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Отправляем в чат сообщение о выходе из машины состояний
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при назначении регистратора: {e}")
        # Необходимость явной обработки ошибок здесь минимальна,
        # так как LoggingAndErrorHandlingMiddleware уже позаботится об этом.
        raise  # Передаем исключение middleware для обработки

# ====================================================================================================

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕВЕРНО"
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_no_registrator_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик отмены добавления нового Регистратора.
    """
    lang = data["lang"]

    logger.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = get_text("admin.registrator_not_added", lang=lang)
    data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


# Этот хэндлер будет срабатывать, если во время подтверждения
# регистратора будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewRegistrator.fill_OK))
@log_handler_call
async def warning_registrator(message: Message, data: dict):
    """
    Обработчик некорректного ввода в машине состояний.
    """
    lang = data["lang"]

    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewRegistrator.fill_OK}")  # type: ignore
    await message.answer(
        text= get_text("admin.use_buttons_or_cancel", lang=lang)
    )


"""
Хэндлеры создани списка регистраторов (суперрегистраторов) и редактирования и статусов
"""


# Добавляем обработку нажатия кнопки "список регистраторов" в меню администратора
@router.callback_query(F.data == "registrators_list")
@log_handler_call
async def process_registrators_list(callback: CallbackQuery, data: dict):
    """
    Обработчик нажатия кнопки "список регистраторов" в меню администратора.
    """
    lang = data["lang"]

    # Проверяем, что callback.from_user существует
    if callback.from_user is None:
        logger.warning("Callback from_user отсутствует")
        return
    logger.info(f"Пользователь {callback.from_user.id} запросил список регистраторов")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Проверяем, доступно ли сообщение для редактирования
    if callback.message is None:
        logger.warning("Сообщение недоступно для редактирования")
        # Проверяем, что callback.bot существует
        if callback.bot is None:
            logger.error("Bot объект недоступен")
            return
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text=get_text("admin.error_loading_registrators", lang=lang)
        )
        return

    # Здесь будет логика получения и отображения списка регистраторов и суперрегистраторов
    registrators = await list_of_members(
        data["club_id"], status="registrator"
    )  # Функция для получения списка регистраторов
    super_registrators = await list_of_members(
        data["club_id"], status="superregistrator"
    )  # Функция для получения списка суперрегистраторов

    if not registrators and not super_registrators:
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.no_registrators", lang=lang)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Редактируем сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        return

    for registrator in registrators:
        # Отправляем сообщение про каждого регистратора
        await callback.message.answer(
            text=(
                f"Регистратор: {registrator['username']} "
                f"{registrator['first_name'] if registrator['first_name'] else ''} "
                f"{registrator['last_name'] if registrator['last_name'] else ''}"
            ),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Удалить из регистраторов",
                            callback_data=f"remove_registrator:{registrator['member_id']}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Сделать суперрегистратором",
                            callback_data=f"promote_to_super:{registrator['member_id']}",
                        )
                    ],
                ]
            ),
        )

    for super_registrator in super_registrators:
        # Отправляем сообщение про каждого суперрегистратора
        await callback.message.answer(
            text=(
                f"Суперегистратор: {super_registrator['username']} \n"
                f"{super_registrator['first_name'] if super_registrator['first_name'] else ''} "
                f"{super_registrator['last_name'] if super_registrator['last_name'] else ''}"
            ),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Удалить из суперрегистраторов",
                            callback_data=f"remove_superregistrator:{super_registrator['member_id']}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Разжаловать в простые регистраторы",
                            callback_data=f"demote_to_registrator:{super_registrator['member_id']}",
                        )
                    ],
                ]
            ),
        )

    await callback.message.answer(
        text="Вернуться в основное меню", reply_markup=return_to_main_menu_markup(lang=lang)
    )


@router.callback_query(F.data.regexp(r"^remove_registrator:\d+$"))
@log_handler_call
async def process_remove_registrator(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления регистратора
    """
    lang = data["lang"]
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return

        logger.info(
            f"Пользователь {callback.from_user.id} удаляет регистратора: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        # Извлекаем member_id из callback.data
        member_id = int(callback.data.split(":")[1])
        registrator = callback.from_user.id

        # Выполняем операцию изменения статуса
        result1 = await new_status(
            registrator=registrator, member_id=member_id, status="not_registrator"
        )

        if result1:
            success1, text = result1

        markup = None

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении регистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_removing_registrator", lang=lang)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r"^promote_to_super:\d+$"))
@log_handler_call
async def process_promote_to_super(callback: CallbackQuery, data: dict):
    """
    Обработчик назначения суперрегистратора
    """
    lang = data["lang"]
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.error_removing_registrator", lang=lang))
            return

        logger.info(
            f"Пользователь {callback.from_user.id} делает регистратора суперрегистратором: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = int(callback.data.split(":")[1])
        registrator = callback.from_user.id

        result1 = await new_status(
            registrator=registrator, member_id=member_id, status="superregistrator"
        )

        if result1:
            success1, text = result1

        markup = None

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при  назначениии суперрегистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_promoting_to_super", lang=lang)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r"^remove_superregistrator:\d+$"))
@log_handler_call
async def process_remove_superregistrator(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления суперрегистратора
    """
    lang = data["lang"]
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return

        logger.info(
            f"Пользователь {callback.from_user.id} удаляет суперрегистратора: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        # Извлекаем member_id из callback.data
        member_id = int(callback.data.split(":")[1])
        registrator = callback.from_user.id

        result1 = await new_status(
            registrator=registrator, member_id=member_id, status="not_superregistrator"
        )
        print(result1)

        if result1:
            success1, text = result1

        markup = None

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении суперрегистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_removing_superregistrator", lang=lang)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r"^demote_to_registrator:\d+$"))
@log_handler_call
async def process_demote_to_registrator(callback: CallbackQuery, data: dict):
    """
    Обработчик разжалования суперрегистратора в регистраторы
    """
    lang = data["lang"]
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        logger.info(
            f"Пользователь {callback.from_user.id} разжалует суперрегистратора в регистраторы: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = int(callback.data.split(":")[1])
        registrator = callback.from_user.id

        result1 = await new_status(
            registrator=registrator, member_id=member_id, status="not_superregistrator"
        )
        result2 = await new_status(
            registrator=registrator, member_id=member_id, status="registrator"
        )

        if result1:
            success1, text1 = result1
        if result2:
            success2, text2 = result2

        text = f"{text1}\n{text2}"

        markup = None

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении регистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_removing_registrator", lang=lang)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


"""
Администрирование голосования
"""


# Хэндлер для обработки кнопки "администрирование голосования"
# callback.data 'admin_voting':{voting_id}
@router.callback_query(F.data.regexp(r"^admin_voting:\d+$"))
@log_handler_call
async def process_admin_voting_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик кнопки "администри >>> голосо >>>"
    """
    lang = data["lang"]

    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        logger.info(
            f"Пользователь {callback.from_user.id} запустил администрирование голосвания: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        voting_info = await get_voting_info(voting_id)
        if not voting_info:
            logger.warning(f"Голосование с ID {voting_id} не найдено")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            raise  # Возвращаем ответ и прерываем обработку
        if voting_info.get("club_id") != data["club_id"]:
            await callback.answer(get_text("admin.voting_not_from_your_group", lang=lang))
            return
        voting_status = voting_info.get("voting_status")
        variants = await list_of_variants(voting_id, "valid")
        if variants:
            amount = len(variants)
        else:
            amount = 0
        if amount == 2:
            voting_status = "final" if voting_status == "ongoing" else voting_status

        dict_menu = {}
        if voting_status == "add_variants":
            dict_menu[f"voting_start:{voting_id}"] = get_text("voting_start", lang=lang)
            dict_menu[f"voting_complete:{voting_id}"] = get_text("voting_complete", lang=lang)
        # Пока не пишу восстановление голосования - слоишком сложно "проворачивать фарш назад"
        # elif voting_status == 'completed':
#         #     dict_menu[f'voting_reopen:{voting_id}'] = get_text('reopen', 'reopen')
        #     dict_menu[f'voting_reopen:{voting_id}'] = get_text("reopen", lang=data.get("lang", "ru"))
        elif voting_status == "ongoing":
            dict_menu[f"voting_stage:{voting_id}"] = get_text("voting_stage", lang=lang)
            dict_menu[f"voting_final:{voting_id}"] = get_text( "voting_final", lang=lang)
            dict_menu[f"voting_complete:{voting_id}"] = get_text( "voting_complete", lang=lang)
        elif voting_status == "final":
            dict_menu[f"voting_complete:{voting_id}"] = get_text( "voting_complete", lang=lang)
        elif voting_status == "confirmation":
            dict_menu[f"voting_complete:{voting_id}"] = get_text( "voting_complete", lang=lang)
        else:
            logger.warning(f"Голосование {voting_id} имеет некорректный статус: {voting_status}")
            await callback.message.answer(  # type: ignore
            text= get_text("admin.unknown_voting_status", lang=lang),
            reply_markup=return_to_main_menu_markup(lang=lang)
        )

#         dict_menu["main_menu"] = LEXICON.get("return_to_main_menu", "main menu")
        dict_menu["main_menu"] = get_text("return_to_main_menu", lang=data.get("lang", "ru"))

        logger.info(f"словарь меню при показе вариантов: {dict_menu}")
        markup = create_inline_kb(1, **dict_menu)

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.choose_action", lang=lang)
        data["reply_markup"] = markup

        # Отправляем или редактируем сообщение
        await callback.message.answer(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при просмотре вариантов голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_removing_registrator", lang=lang)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Редактируем сообщение в случае ошибки
        await callback.message.answer(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r"^voting_start:\d+$"))
@log_handler_call
async def process_voting_start_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    lang = data["lang"]
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        if not callback.bot:
            raise ValueError("Не удалось получить бота")
        bot:Bot = callback.bot

        logger.info(
            f"Пользователь {callback.from_user.id} запускает голосование: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        club_id = data["club_id"]

        result = await voting_manager(
            bot, voting_id, club_id=club_id, admin=member_id, stage_type="start"
        )

        # Гарантируем, что text всегда является строкой
        if result and "message" in result:
            text = result["message"]
            logger.info(text)
        else:
            text = get_text("admin.error_starting_voting", lang=lang)
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status = data.get("user_status", ["user"]))

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = get_text("admin.error_starting_voting", lang=lang)
        data["reply_markup"] = await user_menu(
            status = data.get("user_status", ["user"])
        )

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для промежуточного итога голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r"^voting_stage:\d+$"))
@log_handler_call
async def process_voting_stage_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик нажатия кнопки старта промежуточного этапа голосования.
    """
    lang = data.get("lang","ru")
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        if not callback.bot:
            raise ValueError("Не удалось получить бота")
        bot:Bot = callback.bot
        logger.info(
            f"Пользователь {callback.from_user.id} запускает промежуточный этап голосования: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        club_id = data["club_id"]

        result = await voting_manager(
            bot, voting_id, club_id=club_id, admin=member_id, stage_type="stage"
        )

        if result:
            text = result.get("message")
            logger.info(text)
        else:
            text = get_text("admin.error_intermediate_voting_results", lang=lang)
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status = data.get("user_status", ["user"]))

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = text if isinstance(text, str) else get_text("admin.unknown_error", lang=lang)
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_starting_voting", lang=lang)
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для перехода в финал голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r"^voting_final:\d+$"))
@log_handler_call
async def process_voting_final_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик перехода в финал конкретного голосования.
    """
    lang = data.get("lang","ru")
    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        logger.info(
            f"Пользователь {callback.from_user.id} запускает финальный этап голосования: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        club_id = data["club_id"]

        result = await voting_manager(
            bot, voting_id, club_id=club_id, admin=member_id, stage_type="final"
        )

        if result:
            text = result.get("message")
            logger.info(f"Сообщение о результате перехода в финал: {text}")
        else:
            text = get_text("admin.error_intermediate_voting_results", lang=lang)
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status = data.get("user_status", ["user"]))

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = text if isinstance(text, str) else get_text("admin.unknown_error", lang=lang)
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_starting_voting", lang=lang)
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для завершения голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r"^voting_complete:\d+$"))
@log_handler_call
async def process_voting_complete_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного голосования.
    """
    lang = data.get("lang","ru")
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        if not callback.bot:
            raise ValueError("Не удалось получить бота")
        bot:Bot = callback.bot
        logger.info(
            f"Пользователь {callback.from_user.id} завершает голосование: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        club_id = data["club_id"]

        result = await voting_manager(
            bot, voting_id, club_id=club_id, admin=member_id, stage_type="complete"
        )
        if result:
            text = result.get("message")
            logger.info(f"Сообщение о завершении голосования: {text}")
        else:
            text = get_text("admin.error_completing_voting", lang=lang)
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status = data.get("user_status", ["user"]))

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = text if isinstance(text, str) else get_text("admin.unknown_error", lang=lang)
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_starting_voting", lang=lang)
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для снятия варианта после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r"^delete_variant:\d+$"))
@log_handler_call
async def process_delete_variant_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления варианта
    """
    lang = data.get("lang","ru")
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        logger.info(
            f"Пользователь {callback.from_user.id} удалаяет вариант: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        variant_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        club_id = data["club_id"]

        result = await delete_variant(variant_id, admin=member_id)
        if result:
            text = result[0]
            logger.info(text)
        else:
            text = get_text("admin.error_deleting_variant", lang=lang)
            logger.info(text + f":{variant_id}")

        markup = None

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении варианта: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_deleting_variant", lang=lang)
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для завершения утверждения голосования после нажатия соотвествующей кнопки в меню администратора
@router.callback_query(F.data.regexp(r"^confirmation_of_voting_results_stop:\d+$"))
@log_handler_call
async def process_stop_confirmation_cb(callback: CallbackQuery, data: dict):
    """
    Обработчик завершения утверждения голосования (то есть, последне стадии).
    """
    lang = data.get("lang","ru")
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer(get_text("admin.generic_error_try_again", lang=lang))
            return
        logger.info(
            f"Пользователь {callback.from_user.id} завершает голосование: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        club_id = data["club_id"]

        result = await confirmation_of_voting_results_stop(
            voting_id, finisher=member_id
        )
        if result:
            text = result.get(
                "message",
                "Произошла непредвиденная ошибка при звершении утверждения голосования",
            )
            logger.info(text)
        else:
            text = get_text("admin.error_finishing_confirmation", lang=lang)
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status = data.get("user_status", ["user"]))

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = get_text("admin.error_starting_voting", lang=lang)
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))


        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# При нажатии кнопки "Управление участниками" выдается клавиатура с кнопками "экспорт списка участников", "забанить", "разбанить", "Основное меню"
@router.callback_query(F.data=="admin_members")
async def admin_members(callback: CallbackQuery, data:dict) -> None:
    lang = data.get("lang","ru")
    if not callback.message:
        raise ValueError("Callback message is None")
    buttons = [
        [
            InlineKeyboardButton(
#                 text=LEXICON.get("export_members","Экспорт списка участников"), callback_data="export_members"
                text=get_text("export_members", lang=data.get("lang", "ru")), callback_data="export_members"
            ),
        ],
        [
            InlineKeyboardButton(
#                 text=LEXICON.get("ban_member","Забанить"), callback_data="ban_member"
                text=get_text("ban_member", lang=data.get("lang", "ru")), callback_data="ban_member"
            ),
        ],
        [
            InlineKeyboardButton(
#                 text=LEXICON.get("unban_member","Разбанить"), callback_data="unban_member"
                text=get_text("unban_member", lang=data.get("lang", "ru")), callback_data="unban_member"
            )
        ],
        [
            InlineKeyboardButton(
#                 text=LEXICON.get("return_to_main_menu","Назад"), callback_data="return_to_main_menu"
                text=get_text("return_to_main_menu", lang=data.get("lang", "ru")), callback_data="return_to_main_menu"
            )
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(
        text= get_text("admin.choose_action", lang=lang),
        reply_markup=markup
        )


"""
Хэндлеры бана пользователя
"""
@router.callback_query(StateFilter(default_state), F.data == "ban_member")
async def ban_user(callback: CallbackQuery, state: FSMContext, data:dict) -> None:
    """
    Хендлер нажатия кнопки "Забанить"
    """
    lang = data.get("lang","ru")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = get_text("admin.ban_enter_user_id_or_contact", lang=lang)
    data["reply_markup"] = None  # Если клавиатура не нужна, устанавливаем None

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMBan.fill_ID_User)
    logger.info(f"Установлено состояние: {await state.get_state()}")

# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# и переводить в состояние подтверждения
@router.message(
    StateFilter(FSMBan.fill_ID_User), ~F.contact, (lambda x: x.text.isdigit())
)
@log_handler_call
async def process_ban_user_id_sent(message: Message, state: FSMContext, data: dict):
    lang = data.get("lang","ru")
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.info(
        f"Введенный ID пользователя: {message.text} от пользователя {message.from_user.id}"
    )
    if message.text is not None:
        try:
            user_tg_id = int(message.text.strip())
        except ValueError:
            await message.answer(get_text("admin.invalid_numeric_input", lang=lang))
            raise ValueError("Сообщние не содержит числовое значение.")
    else:
        await message.answer(
            get_text("admin.message_has_no_text", lang=lang))
        raise ValueError("Сообщние не содержит текст")
    await state.update_data(ID=user_tg_id)
    club_id = data.get("club_id")
    if not club_id:  # type: ignore
        raise ValueError("ID группы отсутствует")
    try:
        user_id, user_member_id = await extract_user_member_id(club_id, user_tg_id)
        if user_member_id:
            user_profile = await get_profile(user_member_id)
            if user_profile:
                await message.answer(
                    text=get_text("admin.details_of_the_user_you_want_to_ban",lang=lang).format(user_profile),

    #                 f"""
    #                 Данные участника которого вы хотите забанить:\n
    #                 Имя: {user_profile.get('first_name')},
    # Фамилия: {user_profile.get('last_name')}, \n
    # Телефон: {user_profile.get('tg_phone_number')}\n
    # Псевдоним: {user_profile.get('username')} Всё верно?
    # """,
                    reply_markup=confirm_markup(lang=data.get("lang","en")),  # клавиатура подтверждения из модуля клавиатур
                )
                # Устанавливаем состояние ожидания подтверждения
                await state.set_state(FSMBan.fill_OK)
            else:
                await message.answer(text= get_text("admin.user_profile_not_found", lang=lang))
                # Сбрасываем состояние и очищаем данные, полученные внутри состояний
                await state.clear()
        else:
            await message.answer(text= get_text("admin.user_not_found_in_group", lang=lang))
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        err = str(e)
        await message.answer(text= get_text("admin.error_message", lang=lang).format( err = err))
        await state.clear()

# Этот хэндлер будет срабатывать, если  отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMBan.fill_ID_User), F.contact)
@log_handler_call
async def process_ban_user_contact_sent(
    message: Message, state: FSMContext, contact: Contact, data: dict
):
    lang = data.get("lang","ru")
    if message.contact is None:
        await message.answer( get_text("admin.please_send_contact", lang=lang))
        raise ValueError("Сообщние не содержит контакта.")
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    contact = message.contact
    logger.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")

    if not contact.user_id:
        await message.answer(
            get_text("admin.contact_has_no_id", lang=lang)
        )
        raise ValueError("Сообщние не содержит ID контакта.")

    user_tg_id = contact.user_id

    club_id = data.get("club_id")
    if not club_id:
        raise ValueError("ID клуба отсутствует")

    await state.update_data(ID=user_tg_id)
    try:
        user_id, user_member_id = await extract_user_member_id(club_id, user_tg_id)
        if user_member_id:
            user_profile = await get_profile(user_member_id)
            if user_profile:
                await message.answer(
                    text=get_text("admin.details_of_the_user_you_want_to_ban",lang=lang).format(user_profile)
                    )
            else:
                await message.answer(text="Данные участника не найдены")
                # Сбрасываем состояние и очищаем данные, полученные внутри состояний
                await state.clear()

            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMBan.fill_OK)
        else:
            await message.answer(text="Такой участник не найден")
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        err = str(e)
        await message.answer(text= get_text("admin.error_message", lang=lang).format(err = err))
        await state.clear()

# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMBan.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def process_ban_period_choice(callback: CallbackQuery, state: FSMContext, data: dict):
    lang = data.get("lang","ru")
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Формируем клавиатуру из возможных сроков бана: 3 дня, 7 дней, 15 дней, 30 дней, 90 дней, 180 дней
    buttons = {"3":"3 дня", "7":"7 дней", "15":"15 дней", "30":"30 дней", "90":"90 дней", "180":"180 дней","back_to_main_menu":"Назад в главное меню"}
    markup = create_inline_kb(1, **buttons)
        # Добавляем данные для SafeEditMiddleware
    data["response_text"] = get_text("admin.choose_ban_period_or_cancel", lang=lang)
    data["reply_markup"] = markup

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем состояние ожидания выбора статуса
    await state.set_state(FSMBan.fill_period)




# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMBan.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_no_confirm_ban_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    lang = data.get("lang","ru")
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        get_text("admin.ban_cancelled", lang=lang)
    )
    data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


# Этот хэндлер будет срабатывать, если во время подтверждения
# данных пользователя будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMBan.fill_OK))
@log_handler_call
async def warning_ban_process(message: Message, data: dict):
    lang = data.get("lang","ru")
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(
        f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMBan.fill_OK}"
    )
    await message.answer(
        text= get_text("admin.use_buttons_or_cancel_ban", lang=lang)
    )

# Обрабатываем нажатие кнопки со сроком бана. Извлекаем число дней из callback_data и отправляем в функцию для выставления бана ban_member
@router.callback_query(StateFilter(FSMBan.fill_period), (F.data.isdigit()) )
@log_handler_call
async def process_ban_execute(callback: CallbackQuery, state: FSMContext, data: dict):
    lang = data.get("lang","ru")
    if not callback.data:
        raise ValueError("callback.data отсутствует")
    if not callback.message:
        raise ValueError("Сообщение отсутствует (message == None)")
    # Проверям, существует ли callback.from_user
    if not callback.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    # Правильно получаем значение из callback.data
    callback_data = callback.data
    logger.info(f"Введенный срок бана: {callback_data} от пользователя {callback.from_user.id}")

    try:
        ban_time_days = int(callback_data)
    except (ValueError, TypeError):
        await callback.message.answer( get_text("admin.ban_button_not_a_number", lang=lang))
        raise ValueError("callback.data не является числом.")


    fsm_data = await state.get_data()
    logger.info(f"FSM data: \n{fsm_data}\n")
    club_id = data["club_id"]
    member_tg_id = fsm_data["ID"]
    if not member_tg_id:
        await callback.message.answer( get_text("admin.failed_to_get_user_id_for_ban", lang=lang))
        return
    user_id, member_id = await extract_user_member_id(club_id, member_tg_id)
    if not member_id:
        raise ValueError("ID участника отсутствует")
    admin_id = data["member_id"]
    await ban_member(member_id, admin_id, ban_time_days)
    await callback.message.answer(
        text= get_text("admin.user_banned_for_days", lang=lang).format(ban_time_days = ban_time_days),
        reply_markup=return_to_main_menu_markup(lang=lang)
        )

"""
Хэндлеры разбана пользователя
"""

# TODO: сделать хэндлеры обработки нажатия кнопки unban_member
@router.callback_query(StateFilter(default_state),F.data == "unban_member")
@log_function_call
async def unban_member(callback: CallbackQuery, state: FSMContext, data: dict) -> None:
    lang = data.get("lang","ru")
    if not callback.message:
        raise ValueError("Нет сообщения для ответа")


"""
Хэндлеры экспорта списка участников
"""
@router.callback_query(StateFilter(default_state), F.data == "export_members")
@log_handler_call
async def export_members_start(callback: CallbackQuery, state: FSMContext, data:dict) -> None:
    """
    Хендлер нажатия кнопки "Экспорт списка участников"
    """
    lang = data.get("lang","ru")
    if not callback.message:
        raise ValueError("Callback message is None")
    text= get_text("admin.choose_member_status_for_export", lang=lang)
#     button_dict = LEXICON.get("user_status")
    button_dict:dict = get_text("user_status", lang=data.get("lang", "ru"))
    if not button_dict: button_dict = {}
#     button_dict["main_menu"] = LEXICON.get("main_menu", "Главное меню")
    button_dict["main_menu"] = get_text("main_menu", lang=data.get("lang", "ru"))
    markup = create_inline_kb(2, **button_dict)
    await callback.message.answer(text, reply_markup=markup)
    await state.set_state(FSMExportMembers.fill_status)

# Этот хэндлер будет срабатывать на выбор одного из статусов (или его отмены)
@router.callback_query(StateFilter(FSMExportMembers.fill_status), F.data != "main_menu")
@log_handler_call
async def process_export_members(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    lang = data.get("lang","ru")
    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot
    if not callback.data: return
    if not callback.message: return
    club_id = data.get('club_id')
    if not club_id: return
    status = callback.data
    if status == "all members":
        status = "all"
    try:
        file_path = await export_list_of_members(club_id=club_id, status=status)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл {file_path} не был создан.")

        # Отправляем файл через нашу функцию
        await send_file_to_user(
            bot=bot,
            tg_id=callback.from_user.id,
            file_path=file_path,
            caption= get_text("admin.export_members_start", lang=lang),
            reply_markup=main_menu_markup(lang=lang)
        )

        # Удаляем файл после отправки
        os.remove(file_path)
        logger.info(f"Файл {file_path} удален после отправки.")

    except Exception as e:
        logger.error(f"Ошибка при экспорте списка участников: {e}")
        await callback.message.answer(get_text("admin.export_failed", lang=lang))  # type: ignore

    await callback.message.answer("Главное меню:", reply_markup=main_menu_markup(lang=lang))  # type: ignore
    await state.clear()

"""
Хэндлеры рассылок администратора
"""

@router.callback_query(StateFilter(default_state), F.data == "mailing_list")
@log_handler_call
async def mailing_list_start(callback: CallbackQuery, state: FSMContext, data:dict) -> None:
    """
    Хендлер нажатия кнопки "Рассылка"
    """
    lang = data.get("lang","ru")
    if not callback.message: return
    buttons = ["mailing_all", "mailing_members", "mailing_user","main_menu"]
    markup = create_inline_kb(1, *buttons)
    await callback.message.answer(
        text= get_text("admin.choose_mailing_audience", lang=lang),
        reply_markup=markup
        )
    await state.set_state(FSMTextMailing.fill_choice)


@router.callback_query(FSMTextMailing.fill_choice, F.data.in_(["mailing_all", "mailing_members", "mailing_user"]))
@log_handler_call
async def mailing_all_start(callback: CallbackQuery, state: FSMContext, data:dict) -> None:
    """
    Хендлер выбора типа рассылки
    """
    lang = data.get("lang","ru")
    if not callback.message: return
    # Записываем в FSM данные о том, какой тип рассылки выбран
    await state.update_data(choice=callback.data, ID = None)
    if callback.data == "mailing_user":
        await callback.message.answer(
            text= get_text("admin.enter_user_id_or_contact_for_mailing", lang=lang),
            reply_markup=return_to_main_menu_markup(lang=lang)
            )
        await state.set_state(FSMTextMailing.fill_tg_id)
    else:
        await callback.message.answer(text="Введите текст рассылки:", reply_markup=return_to_main_menu_markup(lang=lang))
        await state.set_state(FSMTextMailing.fill_text)




@router.message(FSMTextMailing.fill_tg_id, F.text.isdigit() | F.contact)
@log_handler_call
async def fill_mailing_tg_id_or_contact(message: Message, state: FSMContext, data: dict):
    lang = data.get("lang","ru")
    if message.contact:
        user_tg_id = message.contact.user_id
        if not user_tg_id:
            await message.answer(
                text = get_text("admin.contact_has_no_id", lang=lang),
                reply_markup=return_to_main_menu_markup(lang=lang)
                                 )
            return
        logger.info(f"Получен контакт с ID: {user_tg_id}")
    elif message.text:  # тогда message.text.isdigit()
        try:
            user_tg_id = int(message.text.strip())
        except ValueError:
            await message.answer(
                text= get_text("admin.invalid_numeric_input", lang=lang),
                reply_markup=return_to_main_menu_markup(lang=lang))
            return
    else:
        await message.answer(
             text= get_text("admin.message_has_no_text", lang=lang),
             reply_markup=return_to_main_menu_markup(lang=lang)
             )
        logger.warning(f"Пользователь {message.from_user.id if message.from_user else 'неизвестен'} ввел некорректный контакт: {message.text}")
        return

    await state.update_data(ID=user_tg_id)
    await message.answer("Введите текст послания:", reply_markup=return_to_main_menu_markup(lang=lang))
    await state.set_state(FSMTextMailing.fill_text)


@router.message(F.text, FSMTextMailing.fill_text)
@log_handler_call
async def fill_mailing_text_for_all(message: Message, state: FSMContext, data: dict):
    """
    Хэндлер для отправки текста рассылки
    """
    lang = data.get("lang","ru")
    if not message.text:
        await message.answer( get_text("admin.message_has_no_text", lang=lang))
        return
    if len(message.text) > 4000:
        await message.answer(
            text = get_text("admin.message_too_long_max_4000", lang=lang),
            reply_markup=return_to_main_menu_markup(lang=lang))
        return
    message_text = message.text
    bot = message.bot
    if not bot:
        raise ValueError("Бот не найден")
    club_id = data["club_id"]

    fsm_data = await state.get_data()

    if fsm_data.get("choice") == "mailing_user":
        text = await send_notification_to_user(bot, fsm_data["ID"], message_text)
    elif fsm_data.get("choice") == "mailing_all":
        text = await send_notification_to_members(bot, club_id, message_text)
    elif fsm_data.get("choice") == "mailing_members":
        text = await send_notification_to_members(bot, club_id, message_text, status="member")
    else:
        raise ValueError("Неизвестное значение choice")

    await message.answer(text=text, reply_markup=main_menu_markup(lang=lang))
    await state.clear()
