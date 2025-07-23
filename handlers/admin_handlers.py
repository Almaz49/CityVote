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
from FSMs.FSMs import FSMExportMembers, FSMNewRegistrator, FSMBan
from keyboards.keyboards import *
from manager.manager import *
from services.services import send_file_to_user, send_notification_to_user
from utils import log_handler_call

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
async def process_new_registrator(message: Message, state: FSMContext):
    if message.from_user is None:
        logger.warning("Сообщение от пользователя без данных from_user")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
        return

    logger.info(
        f"Команда /new_registrator сработала для пользователя {message.from_user.id}"
    )
    await message.answer(
        text="""Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус или отправьте контакт с ID"""
    )
    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMNewRegistrator.fill_ID_NewRegistrator)


# Этот хэндлер будет срабатывать на нажатие кнопки "новый регистратор" в меню админа
@router.callback_query(StateFilter(default_state), F.data == "new_registrator")
@log_handler_call
async def process_new_registrator_cb(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data[
        "response_text"
    ] = """Пожалуйста, введите телеграм-ID участника,
которому вы хотите присвоить новый статус или отправьте контакт с ID"""
    data["reply_markup"] = None  # Если клавиатура не нужна, устанавливаем None

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
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
    # Проверяем, что message.text существует и является строкой
    if message.text is None:
        logger.warning("Получено сообщение без текста")
        await message.answer("Произошла ошибка. Пожалуйста, отправьте корректный ID.")
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
    flag, ans_str = await extract_new_registrator_data(club_id,member_tg_id)

    # Создаем объект инлайн-клавиатуры
    markup = confirm_markup

    if flag:
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = (
            f"Данные участника, которого вы назначаете регитратором:\n{ans_str}\nВсё верно?"
        )
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
        data["reply_markup"] = main_menu_markup

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
    # Проверяем, что контакт существует
    if message.contact is None:
        logger.warning("Получено сообщение без контакта")
        await message.answer(
            "Произошла ошибка. Пожалуйста, отправьте корректный контакт."
        )
        return

    contact = message.contact

    # Проверяем, что from_user существует
    if message.from_user is None:
        logger.warning("Сообщение от пользователя без данных from_user")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
    markup = confirm_markup

    if flag:
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = (
            f"Данные участника, которого вы назначаете регитратором:\n{ans_str}\nВсё верно?"
        )
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
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot

    # Меняем в базе данных статус пользователя по ключу tg_id пользователя и tg_id регистратора
    fsm_data = await state.get_data()
    member_tg_id = fsm_data["ID"]
    admin_tg_id = callback.from_user.id
    admin_id = data["member_id"]
    club_id = data["club_id"]
    instance_name = data["instance_name"]

    try:
        ans_str = await new_status_tg(club_id,
            admin_tg_id, member_tg_id, "pre-registrator"
        )  # Вызов функции присвоения нового статуса
        if isinstance(ans_str, str) and "Ошибка" in ans_str:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = f"Произошла ошибка: {ans_str}"
            data["reply_markup"] = await user_menu(
                status= data["user_status"]
            )
            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(text=data["response_text"], reply_markup=data["reply_markup"])  # type: ignore
            return

        # Завершаем машину состояний
        await state.clear()

        # Формируем и отправляем запрос кандидату в регистраторы - согласен ли он

        notification = (
            "Здравствуйте! Администрация группы назначила вас регистратором.\n"
            "Это означает, что вам будут приходить заявки на вступления в группу, "
            "которые вы можете подтверждать или игнорировать.\n"
            'Если вы согласны на роль Регистратора, нажмите кнопку "Согласен".\n'
            'Если не согласны - кнопку "Не согласен"'
        )

        keyboard = {
            f"pre_registrator_yes:{admin_id}:{member_tg_id}": "Согласен",
            f"pre_registrator_no:{admin_id}:{member_tg_id}": "Не согласен",
        }

        pre_reg_markup = create_inline_kb(2, **keyboard)

        response = await send_notification_to_user(
            bot, member_tg_id, notification, pre_reg_markup, instance_name=instance_name
        )

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = (
            "Спасибо! Кандидат в Регистраторы добавлен!\n"
            "Результат отправки сообщения кандидату:\n"
            f"{response}"
            "\nВы вышли из машины состояний"
        )
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
        )

        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при назначении регистратора: {e}")
        # Необходимость явной обработки ошибок здесь минимальна,
        # так как LoggingAndErrorHandlingMiddleware уже позаботится об этом.
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕВЕРНО"
@router.callback_query(StateFilter(FSMNewRegistrator.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_no_registrator_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        "Спасибо! Регистратор не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний"
    )
    data["reply_markup"] = await user_menu(status= data["user_status"])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


# Этот хэндлер будет срабатывать, если во время подтверждения
# регистратора будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewRegistrator.fill_OK))
@log_handler_call
async def warning_registrator(message: Message):
    logger.warning(f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewRegistrator.fill_OK}")  # type: ignore
    await message.answer(
        text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        "Если вы хотите прервать назначение регистратора - "
        "отправьте команду /cancel"
    )


"""
Хэндлеры создани списка регистраторов (суперрегистраторов) и редактирования и статусов
"""


# Добавляем обработку нажатия кнопки "список регистраторов" в меню администратора
@router.callback_query(F.data == "registrators_list")
@log_handler_call
async def process_registrators_list(callback: CallbackQuery, data: dict):
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
            text="Произошла ошибка при формировании списка регистраторов. Попробуйте снова.",
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
        data["response_text"] = "В данный момент нет регистраторов."
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
        )

        # Редактируем сообщение
        await callback.message.edit_text(  # type: ignore
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
        text="Вернуться в основное меню", reply_markup=return_to_main_menu_markup
    )


@router.callback_query(F.data.regexp(r"^remove_registrator:\d+$"))
@log_handler_call
async def process_remove_registrator(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления регистратора
    """
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
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении регистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при удалении регистратора."
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
        )

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r"^promote_to_super:\d+$"))
@log_handler_call
async def process_promote_to_super(callback: CallbackQuery, data: dict):
    """
    Обработчик назначения суперрегистратора
    """
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при  назначениии суперрегистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при назначении суперрегистратора."
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
        )

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r"^remove_superregistrator:\d+$"))
@log_handler_call
async def process_remove_superregistrator(callback: CallbackQuery, data: dict):
    """
    Обработчик удаления суперрегистратора
    """
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении суперрегистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при удалении суперрегистратора."
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
        )

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(F.data.regexp(r"^demote_to_registrator:\d+$"))
@log_handler_call
async def process_demote_to_registrator(callback: CallbackQuery, data: dict):
    """
    Обработчик разжалования суперрегистратора в регистраторы
    """
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении регистратора: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при удалении регистратора."
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
        )

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
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
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return
        logger.info(
            f"Пользователь {callback.from_user.id} запустил администрирование голосвания: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        voting_info = await get_voting_info(voting_id)
        if not voting_info:
            logger.warning(f"Голосование с ID {voting_id} не найдено")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            raise  # Возвращаем ответ и прерываем обработку
        voting_status = voting_info["status"]
        variants = await list_of_variants(voting_id, "valid")
        if variants:
            amount = len(variants)
        else:
            amount = 0
        if amount == 2:
            voting_status = "final"

        dict_menu = {}
        if voting_status == "add_variants":
            dict_menu[f"voting_start:{voting_id}"] = LEXICON.get(
                "voting_start", "voting_start"
            )
            dict_menu[f"voting_complete:{voting_id}"] = LEXICON.get(
                "voting_complete", "voting_complete"
            )
        # Пока не пишу восстановление голосования - слоишком сложно "проворачивать фарш назад"
        # elif voting_status == 'completed':
        #     dict_menu[f'voting_reopen:{voting_id}'] = LEXICON.get('reopen', 'reopen')
        elif voting_status == "ongoing":
            dict_menu[f"voting_stage:{voting_id}"] = LEXICON.get(
                "voting_stage", "voting_stage"
            )
            dict_menu[f"voting_final:{voting_id}"] = LEXICON.get(
                "voting_final", "voting_final"
            )
            dict_menu[f"voting_complete:{voting_id}"] = LEXICON.get(
                "voting_complete", "voting_complete"
            )
        elif voting_status == "final":
            dict_menu[f"voting_complete:{voting_id}"] = LEXICON.get(
                "voting_complete", "voting_complete"
            )
        elif voting_status == "confirmation":
            dict_menu[f"voting_complete:{voting_id}"] = LEXICON.get(
                "voting_complete", "voting_complete"
            )

        dict_menu["main_menu"] = LEXICON.get("return_to_main_menu", "main menu")

        logger.info(f"словарь меню при показе вариантов: {dict_menu}")
        markup = create_inline_kb(1, **dict_menu)

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Выберите действие"
        data["reply_markup"] = markup

        # Отправляем или редактируем сообщение
        await callback.message.answer(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при просмотре вариантов голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при просмотре вариантов голосования."
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
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
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
        instance_name = data["instance_name"]

        result = await voting_manager(
            bot, voting_id, instance_name=instance_name ,club_id=club_id, admin=member_id, stage_type="start"
        )

        # Гарантируем, что text всегда является строкой
        if result and "message" in result:
            text = result["message"]
            logger.info(text)
        else:
            text = "Что-то пошло не так при запуске голосования"
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status=data["user_status"])

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = "Произошла ошибка при запуске голосования."
        data["reply_markup"] = await user_menu(
            status= data["user_status"]
        )

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
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
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
        instance_name = data["instance_name"]

        result = await voting_manager(
            bot, voting_id, instance_name=instance_name, club_id=club_id, admin=member_id, stage_type="stage"
        )

        if result:
            text = result.get("message")
            logger.info(text)
        else:
            text = "Что-то пошло не так при подведении промежуточного итога голосования"
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status=data["user_status"])

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = text if isinstance(text, str) else "Неизвестная ошибка"
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при запуске голосования."
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
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
    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return
        logger.info(
            f"Пользователь {callback.from_user.id} запускает финальный этап голосования: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        club_id = data["club_id"]
        instance_name = data["instance_name"]

        result = await voting_manager(
            bot, voting_id, instance_name=instance_name, club_id=club_id, admin=member_id, stage_type="final"
        )

        if result:
            text = result.get("message")
            logger.info(f"Сообщение о результате перехода в финал: {text}")
        else:
            text = "Что-то пошло не так при подведении промежуточного итога голосования"
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status=data["user_status"])

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = text if isinstance(text, str) else "Неизвестная ошибка"
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при запуске голосования."
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
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
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
        instance_name = data["instance_name"]

        result = await voting_manager(
            bot, voting_id, club_id=club_id, admin=member_id, stage_type="complete", instance_name=instance_name
        )
        if result:
            text = result.get("message")
            logger.info(f"Сообщение о завершении голосования: {text}")
        else:
            text = "Что-то пошло не так при завершении голосования"
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status=data["user_status"])

        # Гарантируем, что response_text всегда является строкой
        data["response_text"] = text if isinstance(text, str) else "Неизвестная ошибка"
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при запуске голосования."
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
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
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
            text = "Что-то пошло не так при удалении варианта"
            logger.info(text + f":{variant_id}")

        markup = None

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении варианта: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при удалении варианта."
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
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
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
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
            text = "Что-то пошло не так при завершении утверждения голосования"
            logger.info(text + f":{voting_id}")

        markup = await user_menu(status=data["user_status"])

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при запуске голосования."
        data["reply_markup"] = await user_menu(status= data["user_status"])


        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# При нажатии кнопки "Управление участниками" выдается клавиатура с кнопками "экспорт списка участников", "забанить", "разбанить", "Основное меню"
@router.callback_query(F.data=="admin_members")
async def admin_members(callback: CallbackQuery) -> None:
    if not callback.message:
        raise ValueError("Callback message is None")
    buttons = [
        [
            InlineKeyboardButton(
                text=LEXICON.get("export_members","Экспорт списка участников"), callback_data="export_members"
            ),
        ],
        [
            InlineKeyboardButton(
                text=LEXICON.get("ban_member","Забанить"), callback_data="ban_member"
            ),
        ],
        [
            InlineKeyboardButton(
                text=LEXICON.get("unban_member","Разбанить"), callback_data="unban_member"
            )
        ],
        [
            InlineKeyboardButton(
                text=LEXICON.get("back_to_menu","Назад"), callback_data="back_to_menu"
            )
        ]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text="Выберите действие:", reply_markup=markup)


"""
Хэндлеры бана пользователя
"""
@router.callback_query(StateFilter(default_state), F.data == "ban_member")
async def ban_user(callback: CallbackQuery, state: FSMContext, data:dict) -> None:
    """
    Хендлер нажатия кнопки "Забанить"
    """
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data[
        "response_text"
    ] = """Пожалуйста, введите телеграм-ID участника,
которого вы хотите забанить или отправьте контакт с ID"""
    data["reply_markup"] = None  # Если клавиатура не нужна, устанавливаем None

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
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
            await message.answer("Пожалуйста, введите корректное числовое значение.")
            raise ValueError("Сообщние не содержит числовое значение.")
    else:
        await message.answer(
            "Сообщение не содержит текст. Пожалуйста, попробуйте снова."
        )
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
                    text=f"""Данные участника которому вы хотите забанить:\nИмя: {user_profile.get('first_name')},
    Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
    Псевдоним: {user_profile.get('username')} Всё верно?""",
                    reply_markup=confirm_markup,  # клавиатура подтверждения из модуля клавиатур
                )
                # Устанавливаем состояние ожидания подтверждения
                await state.set_state(FSMBan.fill_OK)
            else:
                await message.answer(text="Данные участника не найдены")
                # Сбрасываем состояние и очищаем данные, полученные внутри состояний
                await state.clear()
        else:
            await message.answer(text="Такой участник не найден")
            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        await message.answer(text=f"Произошла ошибка: {str(e)}")
        await state.clear()

# Этот хэндлер будет срабатывать, если  отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMBan.fill_ID_User), F.contact)
@log_handler_call
async def process_ban_user_contact_sent(
    message: Message, state: FSMContext, contact: Contact, data: dict
):
    if message.contact is None:
        await message.answer("Пожалуйста, отправьте контакт.")
        raise ValueError("Сообщние не содержит контакта.")
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    contact = message.contact
    logger.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")

    if not contact.user_id:
        await message.answer(
            "К сожалению, ID контакта отсутствует. Попробуйте отправить просто ID"
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
                    text=f"""Данные участника которого вы хотите забанить:\nИмя: {user_profile.get('first_name')},
    Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
    Псевдоним: {user_profile.get('username')} Всё верно?""",
                    reply_markup=confirm_markup,  # клавиатура подтверждения из модуля клавиатур
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
        await message.answer(text=f"Произошла ошибка: {str(e)}")
        await state.clear()

# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMBan.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def process_ban_period_choice(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Формируем клавиатуру из возможных сроков бана: 3 дня, 7 дней, 15 дней, 30 дней, 90 дней, 180 дней
    buttons = {"3":"3 дня", "7":"7 дней", "15":"15 дней", "30":"30 дней", "90":"90 дней", "180":"180 дней","back_to_main_menu":"Назад в главное меню"}
    markup = create_inline_kb(1, **buttons)
        # Добавляем данные для SafeEditMiddleware
    data["response_text"] = """Выберите, какой срок бана вы хотите назначить. \nЕсли хотите прервать процедуру - наберите /cancel"""
    data["reply_markup"] = markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
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
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        "Спасибо! Новый бан не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний"
    )
    data["reply_markup"] = await user_menu(status= data["user_status"])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


# Этот хэндлер будет срабатывать, если во время подтверждения
# данных пользователя будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMBan.fill_OK))
@log_handler_call
async def warning_ban_process(message: Message):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(
        f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMBan.fill_OK}"
    )
    await message.answer(
        text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        "Если вы хотите прервать выставление бана - "
        "отправьте команду /cancel"
    )

# Обрабатываем нажатие кнопки со сроком бана. Извлекаем число дней из callback_data и отправляем в функцию для выставления бана ban_member
@router.callback_query(StateFilter(FSMBan.fill_period), (F.data.isdigit()) )
@log_handler_call
async def process_ban_execute(callback: CallbackQuery, state: FSMContext, data: dict):
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
        await callback.message.answer("Нажатая кнопка не является числом. Сообщите администратору")
        raise ValueError("callback.data не является числом.")


    fsm_data = await state.get_data()
    logger.info(f"FSM data: \n{fsm_data}\n")
    club_id = data["club_id"]
    member_tg_id = fsm_data["ID"]
    user_id, member_id = await extract_user_member_id(club_id, member_tg_id)
    if not member_id:
        raise ValueError("ID участника отсутствует")
    admin_id = data["member_id"]
    await ban_member(member_id, admin_id, ban_time_days)
    await callback.message.answer(text=f"Участник забанен на {ban_time_days} дней",
                                  reply_markup=return_to_main_menu_markup)

"""
Хэндлеры экспорта списка участников
"""
@router.callback_query(StateFilter(default_state), F.data == "export_members")
@log_handler_call
async def export_members_start(callback: CallbackQuery, state: FSMContext, data:dict) -> None:
    """
    Хендлер нажатия кнопки "Экспорт списка участников"
    """
    if not callback.message:
        raise ValueError("Callback message is None")
    text="Выберите, с каким статусом участников вы хотите выгрузить список:"
    button_dict = LEXICON.get("user_status")
    if not button_dict: button_dict = {}
    button_dict["main_menu"] = LEXICON.get("main_menu", "Главное меню")
    markup = create_inline_kb(2, **button_dict)
    await callback.message.answer(text, reply_markup=markup)
    await state.set_state(FSMExportMembers.fill_status)

# Этот хэндлер будет срабатывать на выбор одного из статусов (или его отмены)
@router.callback_query(StateFilter(FSMExportMembers.fill_status), F.data != "main_menu")
@log_handler_call
async def process_export_members(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot
    if not callback.data: return
    if not callback.message: return
    club_id = data.get('club_id')
    if not club_id: return
    instance_name = data.get('instance_name')
    if not instance_name: return
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
            instance_name=instance_name,
            file_path=file_path,
            caption="Экспорт списка участников",
            reply_markup=main_menu_markup
        )

        # Удаляем файл после отправки
        os.remove(file_path)
        logger.info(f"Файл {file_path} удален после отправки.")

    except Exception as e:
        logger.error(f"Ошибка при экспорте списка участников: {e}")
        await callback.message.answer("Не удалось экспортировать список участников.")  # type: ignore

    await callback.message.answer("Главное меню:", reply_markup=main_menu_markup)  # type: ignore
    await state.clear()