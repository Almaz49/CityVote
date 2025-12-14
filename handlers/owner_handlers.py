# handlers/owner_handlers.py

import logging

from aiogram import F, Bot, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Contact, Message

from LEXICON import get_text
from data_base.telegram_bot_logic import *
from filters.filters import StatusFilter
from FSMs.FSMs import AdminStates, FSMNewStatus
from keyboards.keyboards import *
from services.services import process_channel_info
from utils import log_handler_call, safe_edit

# Настройка логирования
logger = logging.getLogger(__name__)



# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status=["owner"]))
router.callback_query.filter(StatusFilter(required_status=["owner"]))

"""
Хэндлеры FSM присвоения нового статуса выбранному участнику группы
"""


# Этот хэндлер будет срабатывать на команду /new_status
# и переводить бота в состояние ожидания ввода телеграм-ID участника,
# которому меняется статус
@router.message(Command(commands="new_status"), StateFilter(default_state))
@log_handler_call
async def process_new_status(message: Message, state: FSMContext, data: dict):
    await message.answer(
#         text="""Пожалуйста, введите телеграм-ID участника,
# которому вы хотите присвоить новый статус или отправьте контакт с ID"""
        text=get_text("owner.please_enter_telegram_id_member_to_whom_you_want_grant_new_s", lang=data.get("lang","ru"))

    )
    # Устанавливаем состояние ожидания ввода имени
    await state.set_state(FSMNewStatus.fill_ID_User)


# Этот хэндлер будет срабатывать на нажатие кнопки "новый статус" в меню админа
@router.callback_query(StateFilter(default_state), F.data == "new_status")
@log_handler_call
async def process_new_status_cb(callback: CallbackQuery, state: FSMContext, data: dict):
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data[
        "response_text"
#     ] = """Пожалуйста, введите телеграм-ID участника,
# которому вы хотите присвоить новый статус или отправьте контакт с ID"""
    ] = get_text("owner.please_enter_telegram_id_member_to_whom_you_want_grant_new_s_1", lang=data.get("lang","ru"))

    data["reply_markup"] = None  # Если клавиатура не нужна, устанавливаем None

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем состояние ожидания ввода ID
    await state.set_state(FSMNewStatus.fill_ID_User)
    logger.info(f"Установлено состояние: {await state.get_state()}")


# Этот хэндлер будет срабатывать, если введен корректный ID (число)
# и переводить в состояние подтверждения
@router.message(
    StateFilter(FSMNewStatus.fill_ID_User), ~F.contact, (lambda x: x.text.isdigit())
)
@log_handler_call
async def process_user_id_sent(message: Message, state: FSMContext, data: dict):
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
#             await message.answer("Пожалуйста, введите корректное числовое значение.")
            await message.answer(get_text("owner.please_enter_correct_numeric_value", lang=data.get("lang","ru")))

            raise ValueError("Сообщние не содержит числовое значение.")
    else:
        await message.answer(
#             "Сообщение не содержит текст. Пожалуйста, попробуйте снова."
            get_text("owner.message_not_contains_text_please_try_again", lang=data.get("lang","ru"))

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
#                     text=f"""Данные участника которому вы меняете статус:\nИмя: {user_profile.get('first_name')},
#     Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
#     Псевдоним: {user_profile.get('username')} Всё верно?""",
                    text=get_text("owner.data_member_to_whom_you_change_status_name_value_last_name_v", lang=data.get("lang","ru")).format(**user_profile),

                    reply_markup=confirm_markup(lang=data.get("lang","en")),  # клавиатура подтверждения из модуля клавиатур
                )
                # Устанавливаем состояние ожидания подтверждения
                await state.set_state(FSMNewStatus.fill_OK)
            else:
#                 await message.answer(text="Данные участника не найдены")
                await message.answer(text=get_text("owner.data_member_not_found", lang=data.get("lang","ru")))

                # Сбрасываем состояние и очищаем данные, полученные внутри состояний
                await state.clear()
        else:
#             await message.answer(text="Такой участник не найден")
            await message.answer(text=get_text("owner.such_member_not_found", lang=data.get("lang","ru")))

            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        err = str(e)
#         await message.answer(text=f"Произошла ошибка: {str(e)}")
        await message.answer(text=get_text("owner.occurred_error_value", lang=data.get("lang","ru")).format(err = err))

        await state.clear()


# Этот хэндлер будет срабатывать, если  отправлен контакт с ID
# и переводить в состояние подтверждения
@router.message(StateFilter(FSMNewStatus.fill_ID_User), F.contact)
@log_handler_call
async def process_user_contact_sent(
    message: Message, state: FSMContext, data: dict
):
    if message.contact is None:
#         await message.answer("Пожалуйста, отправьте контакт.")
        await message.answer(get_text("owner.please_send_contact", lang=data.get("lang","ru")))

        raise ValueError("Сообщние не содержит контакта.")
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    contact = message.contact
    logger.info(f"Прислан контакт: {contact} от пользователя {message.from_user.id}")

    if not contact.user_id:
        await message.answer(
#             "К сожалению, ID контакта отсутствует. Попробуйте отправить просто ID"
            get_text("owner.to_sorry_id_contact_missing_try_send_simply_id", lang=data.get("lang","ru"))

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
#                     text=f"""Данные участника которому вы меняете статус:\nИмя: {user_profile.get('first_name')},
#     Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
#     Псевдоним: {user_profile.get('username')} Всё верно?""",
                    text=get_text("owner.data_member_to_whom_you_change_status_name_value_last_name_v_1", lang=data.get("lang","ru")).format(**user_profile),

                    reply_markup=confirm_markup(lang=data.get("lang","en")),  # клавиатура подтверждения из модуля клавиатур
                )
            else:
#                 await message.answer(text="Данные участника не найдены")
                await message.answer(text=get_text("owner.data_member_not_found_1", lang=data.get("lang","ru")))

                # Сбрасываем состояние и очищаем данные, полученные внутри состояний
                await state.clear()

            # Устанавливаем состояние ожидания подтверждения
            await state.set_state(FSMNewStatus.fill_OK)
        else:
#             await message.answer(text="Такой участник не найден")
            await message.answer(text=get_text("owner.such_member_not_found_1", lang=data.get("lang","ru")))

            # Сбрасываем состояние и очищаем данные, полученные внутри состояний
            await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при извлечении данных пользователя: {e}")
        err = str(e)
#         await message.answer(text=f"Произошла ошибка: {str(e)}")
        await message.answer(text=get_text("owner.occurred_error_value_1", lang=data.get("lang","ru")).format(err = err))

        await state.clear()


# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def process_status_choice(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    logger.info(f"FSM data: \n{fsm_data}\n")
    member_tg_id = fsm_data["ID"]
    club_id = data.get("club_id")
    if not club_id:
        raise ValueError("ID клуба отсутствует")
    user_id, member_id = await extract_user_member_id(club_id, member_tg_id)
    if not member_id:
        raise ValueError("ID участника отсутствует")

    try:
        status = await extract_status(member_id)
        status = status if status else []
        all_st = await all_status()

        vacansy = list(
            set(all_st)
            - set(status)
            - {"owner", "user", "candidate", "votist", "proxy", "pre-registrator","banned"}
        )
        status = list(set(status) - {"owner", "member", "user", "candidate","frozen","votist"})

        logger.debug(f"Вакансии для пользователя: {vacansy}")

        keyboards = []
        for item in vacansy:
            keyboards.append("AppointAs_" + item)
        for item in status:
            keyboards.append("not_" + item)

        keyboards.append("main_menu")
        markup = create_inline_kb(1, *keyboards)

        # Добавляем данные для SafeEditMiddleware
        data[
            "response_text"
#         ] = """Выберите, какой статус вы хотите добавить пользователю, или удалить.
# \nЕсли хотите прервать процедуру - наберите /cancel"""
        ] = get_text("owner.choose_which_status_you_want_add_user_or_remove_if_want_canc", lang=data.get("lang","ru"))

        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Устанавливаем состояние ожидания выбора статуса
        await state.set_state(FSMNewStatus.fill_choice)

    except Exception as e:
        logger.error(f"Ошибка при формировании клавиатуры статусов: {e}")
        err = str(e)

        # Добавляем данные для SafeEditMiddleware
#         data["response_text"] = f"Произошла ошибка: {str(e)}"
        data["response_text"] = get_text("owner.occurred_error_value_2", lang=data.get("lang","ru")).format(err=err)

        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewStatus.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_no_confirm_status_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
#         "Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний"
        get_text("owner.thank_you_new_status_not_added_try_also_time_you_exited_from", lang=data.get("lang","ru"))

    )
    data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


# Этот хэндлер будет срабатывать, если во время подтверждения
# данных пользователя будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_OK))
@log_handler_call
async def warning_new_status_process(message: Message, data: dict):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(
        f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_OK}"
    )
    await message.answer(
#         text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        text=get_text("owner.please_use_buttons", lang=data.get("lang","ru"))

        # "Если вы хотите прервать назначение регистратора - "
        # "отправьте команду /cancel"
    )


# Этот хэндлер будет срабатывать на выбор одного из статусов (или его отмены)
@router.callback_query(StateFilter(FSMNewStatus.fill_choice), F.data != "main_menu")
@log_handler_call
async def process_new_status_confirm(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Выбран статус: {callback.data} пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    if not callback.data:
        raise ValueError("Нет callback.data")
    club_id = data.get("club_id")
    if not club_id:
        raise ValueError("Нет club_id")
    await state.update_data(status=callback.data)
    status = callback.data
    fsm_data = await state.get_data()
    member_tg_id = fsm_data["ID"]

    try:
        user_id, member_id = await extract_user_member_id(club_id, member_tg_id)
        if not member_id:
            raise ValueError("Нет member_ID пользователя")
        user_profile = await get_profile(member_id)
        if user_profile:
            status_text = get_text(f"{status}",lang=data.get("lang", "ru"))
#             text = f"""Данные участника которому вы меняете статус:\nИмя: {user_profile.get('first_name')},
# Фамилия: {user_profile.get('last_name')}, \n Телефон: {user_profile.get('tg_phone_number')}\n
# Псевдоним: {user_profile.get('username')}\nВы хотите изменить его статус:
# \n{status_text}\nВсё верно?"""
            text = get_text("owner.data_member_to_whom_you_change_status_name_value_last_name_v_2", lang=data.get("lang","ru")).format(**user_profile)

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = confirm_markup(lang=data.get("lang","en"))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.set_state(FSMNewStatus.fill_new_status_confirm)

    except Exception as e:
        logger.error(
            f"Ошибка при извлечении данных пользователя или формировании сообщения: {e}"
        )
        err = str(e)

        # Добавляем данные для SafeEditMiddleware
#         data["response_text"] = f"Произошла ошибка: {str(e)}"
        data["response_text"] = get_text("owner.occurred_error_value_3", lang=data.get("lang","ru")).format(err = err)

        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении
# нового статуса, присваиваемого пользователю
@router.callback_query(
    StateFilter(FSMNewStatus.fill_new_status_confirm), F.data == "ConfirmOK"
)
@log_handler_call
async def process_new_status_entry(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Присваиваем переменной st значение статуса без приставки, чтобы проверить существует ли вообще такой статус
    fsm_data = await state.get_data()
    status = fsm_data["status"]
    st = status
    if status.split("_")[0] == "not":
        st = status[4:]
    if status.split("_")[0] == "AppointAs":
        st = status[10:]

    try:
        if st not in await all_status():
            await state.clear()

            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (
#                 "Извините, такого статуса нет.\n\n Попробуйте снова."
                get_text("owner.sorry_such_status_no_try_again", lang=data.get("lang","ru"))

                # "Вы вышли из машины состояний"
            )
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Пытаемся отредактировать сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
        else:
            member_tg_id = fsm_data["ID"]
            registrator_tg_id = callback.from_user.id
            club_id = data["club_id"]
            ans_str = await new_status_tg(club_id,
                registrator_tg_id, member_tg_id, status
            )  # Вызов функции присвоения нового статуса

            if isinstance(ans_str, str) and "Ошибка" in ans_str:
                # Добавляем данные для SafeEditMiddleware
#                 data["response_text"] = f"Произошла ошибка: {ans_str}"
                data["response_text"] = get_text("owner.occurred_error_value_4", lang=data.get("lang","ru")).format(ans_str=ans_str)

                data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

                # Пытаемся отредактировать сообщение
                await safe_edit(callback,   # type: ignore
                    text=data["response_text"], reply_markup=data["reply_markup"]
                )
                return

            # Завершаем машину состояний
            await state.clear()

            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (
#                 "Спасибо! Статус участника обновлен!\n\n" "Вы вышли из машины состояний"
                get_text("owner.thank_you_status_member_updated", lang=data.get("lang","ru"))
            )
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Пытаемся отредактировать сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

    except Exception as e:
        logger.error(f"Ошибка при присвоении нового статуса: {e}")
        err = str(e)

        # Добавляем данные для SafeEditMiddleware
#         data["response_text"] = f"Произошла ошибка: {str(e)}"
        data["response_text"] = get_text("owner.occurred_error_value_5", lang=data.get("lang","ru")).format(err = err)

        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(
    StateFilter(FSMNewStatus.fill_new_status_confirm), F.data == "ConfirmNotOK"
)
@log_handler_call
async def process_no_confirm_status(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Завершаем машину состояний
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
#         "Спасибо! Новый статус не добавлен!\nПопробуйте еще раз.\nВы вышли из машины состояний"
        get_text("owner.thank_you_new_status_not_added_try_also_time_you_exited_from_1", lang=data.get("lang","ru"))

    )
    data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


# Этот хэндлер будет срабатывать, если во время подтверждения
# статуса будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSMNewStatus.fill_new_status_confirm))
@log_handler_call
async def warning_new_status(message: Message, data: dict):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(
        f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSMNewStatus.fill_new_status_confirm}"
    )
    await message.answer(
#         text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        text=get_text("owner.please_use_buttons_1", lang=data.get("lang","ru"))

        # "Если вы хотите прервать изменение статуса - "
        # "отправьте команду /cancel"
    )


"""
АДМИНИСТРИРОВАНИЕ БОТА
"""


# Обрабатывает нажатие кнопик "admin_bot", присылает клавиатуру администрирования
@router.callback_query(F.data == "admin_bot")
@log_handler_call
async def admin_menu(callback: CallbackQuery):
    markup = get_admin_menu_keyboard()
    await safe_edit(callback, "Выберите действие:", reply_markup=markup)  # type: ignore


# Изменение имени группы


@router.callback_query(F.data == "edit_club_name")
@log_handler_call
async def edit_club_name_start(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Введите новое имя группы:")  # type: ignore
    await callback.message.answer(get_text("owner.enter_new_name_group", lang=data.get("lang","ru")))  # type: ignore

    await state.set_state(AdminStates.entering_club_name)


@router.message(AdminStates.entering_club_name)
@log_handler_call
async def process_club_name(message: Message, state: FSMContext, club_id: int, data: dict):
    if not message.text:
#         await message.answer("Имя не может быть пустым. Попробуйте снова.")
        await message.answer(get_text("owner.name_not_can_be_empty_try_again", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")
    new_name = message.text.strip()
    if not new_name:
#         await message.answer("Имя не может быть пустым. Попробуйте снова.")
        await message.answer(get_text("owner.name_not_can_be_empty_try_again_1", lang=data.get("lang","ru")))

        return

    success = await update_club_name(club_id=club_id, new_name=new_name)
    if success:
#         await message.answer(f"Имя группы успешно изменено на: {new_name}")
        await message.answer(get_text("owner.name_group_success_changed_to_value", lang=data.get("lang","ru")).format(new_name=new_name))

    else:
#         await message.answer("Произошла ошибка при изменении имени группы.")
        await message.answer(get_text("owner.occurred_error_with_changes_name_group", lang=data.get("lang","ru")))


    await state.clear()


# Изменение описания группы


@router.callback_query(F.data == "edit_club_description")
@log_handler_call
async def edit_club_description_start(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Введите новое описание группы:")  # type: ignore
    await callback.message.answer(get_text("owner.enter_new_description_group", lang=data.get("lang","ru")))  # type: ignore

    await state.set_state(AdminStates.entering_club_description)


@router.message(AdminStates.entering_club_description)
@log_handler_call
async def process_club_description(message: Message, state: FSMContext, club_id: int, data: dict):
    if not message.text:
#         await message.answer("Описание не может быть пустым. Попробуйте снова.")
        await message.answer(get_text("owner.description_not_can_be_empty_try_again", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")
    new_description = message.text.strip()
    if not new_description:
#         await message.answer("Описание не может быть пустым. Попробуйте снова.")
        await message.answer(get_text("owner.description_not_can_be_empty_try_again_1", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")

    success = await update_club_description(
        club_id=club_id, new_description=new_description
    )
    if success:
#         await message.answer(f"Описание группы успешно изменено.")
        await message.answer(get_text("owner.description_group_success_changed", lang=data.get("lang","ru")))

    else:
#         await message.answer("Произошла ошибка при изменении описания группы.")
        await message.answer(get_text("owner.occurred_error_with_changes_description_group", lang=data.get("lang","ru")))


    await state.clear()


# Изменение условий участия


@router.callback_query(F.data == "edit_club_conditions")
@log_handler_call
async def edit_club_conditions_start(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Введите новые условия участия в группе:")  # type: ignore
    await callback.message.answer(get_text("owner.enter_new_conditions_participation_in_group", lang=data.get("lang","ru")))  # type: ignore

    await state.set_state(AdminStates.entering_club_conditions)


@router.message(AdminStates.entering_club_conditions)
@log_handler_call
async def process_club_conditions(message: Message, state: FSMContext, club_id: int, data: dict):
    if not message.text:
#         await message.answer("Условия не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.conditions_not_can_be_empty_try_again", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")
    new_conditions = message.text.strip()
    if not new_conditions:
#         await message.answer("Условия не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.conditions_not_can_be_empty_try_again_1", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")

    success = await update_club_conditions(
        club_id=club_id, new_conditions=new_conditions
    )
    if success:
#         await message.answer(f"Условия участия успешно изменены.")
        await message.answer(get_text("owner.conditions_participation_success_changed", lang=data.get("lang","ru")))

    else:
#         await message.answer("Произошла ошибка при изменении условий участия.")
        await message.answer(get_text("owner.occurred_error_with_changes_conditions_participation", lang=data.get("lang","ru")))


    await state.clear()


# Добавление телеграм-канала


@router.callback_query(F.data == "add_channel")
@log_handler_call
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Введите ID или ссылку на канал/чат для рассылок:")  # type: ignore
    await callback.message.answer(get_text("owner.enter_id_or_link_to_channel_chat_for_mailing", lang=data.get("lang","ru")))  # type: ignore

    await state.set_state(AdminStates.adding_telegram_channel)


@router.message(AdminStates.adding_telegram_channel)
@log_handler_call
async def process_add_channel(message: Message, state: FSMContext, data: dict):
    if not message.text:
#         await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.id_or_link_not_can_be_empty_try_again", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")
    if not message.bot:
        raise ValueError("Бот не найден")
    bot:Bot = message.bot
    channel_info = message.text.strip()
    if not channel_info:
#         await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.id_or_link_not_can_be_empty_try_again_1", lang=data.get("lang","ru")))

        raise
    club_id = data["club_id"]

    result = await process_channel_info(bot, channel_info, club_id, "add")
    await message.answer(result["message"])
    await state.clear()


# Удаление телеграм-канала


@router.callback_query(F.data == "remove_channel")
@log_handler_call
async def remove_channel_start(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Введите ID или ссылку на канал/чат для удаления из рассылок:")  # type: ignore
    await callback.message.answer(get_text("owner.enter_id_or_link_to_channel_chat_for_deletion_from_mailing", lang=data.get("lang","ru")))  # type: ignore

    await state.set_state(AdminStates.removing_telegram_channel)


@router.message(AdminStates.removing_telegram_channel)
@log_handler_call
async def process_remove_channel(message: Message, state: FSMContext, data: dict):
    if not message.text:
#         await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.id_or_link_not_can_be_empty_try_again_2", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")
    if not message.bot:
        raise ValueError("Бот не найден")
    bot:Bot = message.bot
    channel_info = message.text.strip()
    if not channel_info:
#         await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.id_or_link_not_can_be_empty_try_again_3", lang=data.get("lang","ru")))

        return

    club_id = data["club_id"]
    result = await process_channel_info(bot, channel_info, club_id, "remove")
    await message.answer(result["message"])
    await state.clear()


# Установка основного канала


@router.callback_query(F.data == "set_main_channel")
@log_handler_call
async def set_main_channel_start(callback: CallbackQuery, state: FSMContext):
#     await callback.message.answer("Введите ID или ссылку на основной канал/чат:")  # type: ignore
    await callback.message.answer(get_text("owner.enter_id_or_link_to_main_channel_chat", lang=data.get("lang","ru")))  # type: ignore

    await state.set_state(AdminStates.setting_main_channel)


@router.message(AdminStates.setting_main_channel)
@log_handler_call
async def process_set_main_channel(message: Message, state: FSMContext, data: dict):
    if not message.text:
#         await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.id_or_link_not_can_be_empty_try_again_4", lang=data.get("lang","ru")))

        raise ValueError("Текст сообщения пуст")
    if not message.bot:
        raise ValueError("Бот не найден")
    bot:Bot = message.bot
    channel_info = message.text.strip()
    if not channel_info:
#         await message.answer("ID или ссылка не могут быть пустыми. Попробуйте снова.")
        await message.answer(get_text("owner.id_or_link_not_can_be_empty_try_again_5", lang=data.get("lang","ru")))

        return
    club_id = data['club_id']
    result = await process_channel_info(bot, channel_info, club_id, "set_main")
    # Логирование результата
    logger.debug(f"Результат операции: {result}")

    if isinstance(result, dict) and "message" in result:
        await message.answer(result["message"])
    else:
#         await message.answer("Произошла ошибка при обработке запроса.")
        await message.answer(get_text("owner.occurred_error_with_processing_request", lang=data.get("lang","ru")))


    await state.clear()


# Установка продолжительности этапов голосования


# 1. Команда для запуска процесса
@router.message(Command(commands="set_stage_durations"), StateFilter(default_state))
@log_handler_call
async def start_setting_stage_durations(message: Message, state: FSMContext, data: dict):
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")
    logger.info(
        f"Команда /set_stage_durations сработала для пользователя {message.from_user.id}"
    )
    await message.answer(
#         text="Введите продолжительность этапов голосования (в сутках) в следующем формате:\n"
        text=get_text("owner.enter_duration_stages_voting_in_days_in_next_formate", lang=data.get("lang","ru"))

        # "1. Продолжительность этапа добавления вариантов\n"
        # "2. Продолжительность основного этапа\n"
        # "3. Продолжительность финального этапа\n"
        # "4. Продолжительность этапа утверждения итогов\n"
        # "Пример: `2 3 1 1` (через пробел)."
    )
    await state.set_state(AdminStates.setting_stage_durations)


# Тоже самое при обработке кнопки 'set_stage_durations'
@router.callback_query(StateFilter(default_state), F.data == "set_stage_durations")
@log_handler_call
async def process_set_stage_durations_cb(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик нажатия кнопки "Установить продолжительность этапов голосования" в меню администрирования.
    """
    logger.info(
        f"Кнопка 'set_stage_durations' нажата пользователем {callback.from_user.id}"
    )
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Формируем текст и клавиатуру для ответа
    response_text = (
#         "Введите продолжительность этапов голосования (в сутках) в следующем формате:\n"
        get_text("owner.enter_duration_stages_voting_in_days_in_next_formate_1", lang=data.get("lang","ru"))

        # "1. Продолжительность этапа добавления вариантов\n"
        # "2. Продолжительность основного этапа\n"
        # "3. Продолжительность финального этапа\n"
        # "4. Продолжительность этапа утверждения итогов\n"
        # "Пример: `2 3 1 1` (через пробел)."
    )
    reply_markup = None  # Клавиатура не нужна

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = response_text
    data["reply_markup"] = reply_markup

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем состояние ожидания ввода продолжительности этапов
    await state.set_state(AdminStates.setting_stage_durations)


# 2. Хэндлер для обработки ввода значений


@router.message(StateFilter(AdminStates.setting_stage_durations), F.text)
@log_handler_call
async def process_stage_durations_input(message: Message, state: FSMContext, data: dict):
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.info(
        f"Пользователь {message.from_user.id} ввел продолжительность этапов: {message.text}"
    )
    try:
        if not message.text:
#             await message.answer("Произошла ошибка: данные не найдены.")
            await message.answer(get_text("owner.occurred_error_data_not_found", lang=data.get("lang","ru")))

            logger.warning("Данные введены пустыми")
            raise ValueError("Данные введены пустыми")
        # Разбиваем введенные данные на список чисел
        durations = list(map(int, message.text.split()))
        if len(durations) != 4 or any(d <= 0 for d in durations):
#             await message.answer("Произошла ошибка: данные некорректны. Должно быть 4 положительных числа.")
            await message.answer(get_text("owner.occurred_error_data_incorrect_must_be_4_positive_number", lang=data.get("lang","ru")))

            logger.warning("Некорректные данные")
            raise ValueError("Должно быть 4 положительных числа")


        # Сохраняем данные в FSM
        await state.update_data(
            duration_add_variants=durations[0],
            duration_first_stage=durations[1],
            duration_final=durations[2],
            duration_confirmation=durations[3],
        )

        duration_add_variants=durations[0],
        duration_first_stage=durations[1],
        duration_final=durations[2],
        duration_confirmation=durations[3],

        # Формируем текст для подтверждения
        confirmation_text = (
#             f"Подтвердите продолжительность этапов голосования (в сутках):\n"
            get_text("owner.confirm_duration_stages_voting_in_days", lang=data.get("lang","ru")).format(
                duration_add_variants=duration_add_variants,
                duration_first_stage=duration_first_stage,
                duration_final=duration_final,
                duration_confirmation=duration_confirmation
                )
)

            # f"1. Этап добавления вариантов: {duration_add_variants} суток\n"
            # f"2. Основной этап: {duration_first_stage} суток\n"
            # f"3. Финальный этап: {duration_final} суток\n"
            # f"4. Этап утверждения итогов: {duration_confirmation} суток\n"
            # "Всё верно?"


        # Отправляем сообщение с подтверждением
        markup = confirm_markup(lang=data.get("lang","ru"))
        await message.answer(text=confirmation_text, reply_markup=markup)
        await state.set_state(AdminStates.setting_stage_durations)

    except ValueError as e:
        logger.warning(
            f"Ошибка ввода длительности этапов от пользователя {message.from_user.id}: {e}"
        )
        await message.answer(
#             text=f"Некорректный ввод: {e}\nПожалуйста, введите четыре положительных числа через пробел."
            text=get_text("owner.invalid_input_value_please_enter_four_positive_number_throug", lang=data.get("lang","ru")).format(e=e)

        )


# 3. Хэндлер для подтверждения ввода
@router.callback_query(
    StateFilter(AdminStates.setting_stage_durations), F.data == "ConfirmOK"
)
@log_handler_call
async def confirm_stage_durations(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    club_id = data["club_id"]
    result = await update_stage_duration(
        club_id=club_id,
        duration_add_variants=fsm_data["duration_add_variants"],
        duration_first_stage=fsm_data["duration_first_stage"],
        duration_final=fsm_data["duration_final"],
        duration_confirmation=fsm_data["duration_confirmation"],
    )

    # Формируем ответ
    response_text = (
        result if isinstance(result, str) else "Произошла ошибка при сохранении данных."
    )
    markup = await user_menu(status= data.get("user_status", "user"))

    # Отправляем ответ и завершаем машину состояний
    await safe_edit(callback, text=response_text, reply_markup=markup)  # type: ignore
    await state.clear()


# 4. Хэндлер для отмены подтверждения
@router.callback_query(
    StateFilter(AdminStates.setting_stage_durations), F.data == "ConfirmNotOK"
)
@log_handler_call
async def cancel_stage_durations(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Завершаем машину состояний
    await state.clear()

    # Отправляем сообщение об отмене
#     response_text = "Установка продолжительности этапов отменена."
    response_text = get_text("owner.setting_prodolzhitelьnosti_stages_cancelled", lang=data.get("lang","ru"))

    markup = await user_menu(status= data.get("user_status", "user"))
    await safe_edit(callback, text=response_text, reply_markup=markup)  # type: ignore


# Установка электоральных порогов для делегатов.
# Один порог - в голосах, другой - в процентах. Работать будет тот, который больше.


# 1. Хэндлер для обработки нажатия кнопки с callback_data='set_threshold'
@router.callback_query(StateFilter(default_state), F.data == "set_threshold")
@log_handler_call
async def process_set_threshold_cb(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик нажатия кнопки "Установить пороги доверенных голосов" в меню администрирования.
    """
    logger.info(f"Кнопка 'set_threshold' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Формируем текст для инструкции
    response_text = (
#         "Введите пороги доверенных голосов в следующем формате:\n"
        get_text("owner.enter_thresholds_trusted_votes_in_next_formate", lang=data.get("lang","ru"))

        # "1. Минимальное количество голосов (число с плавающей точкой или запятой)\n"
        # "2. Минимальный процент от общего числа голосов (число с плавающей точкой или запятой)\n"
        # "Примеры:\n"
        # "- `10.5 5`\n"
        # "- `10,5 1,5`\n"
        # "- `10 15`\n"
        # "Через пробел."
    )

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = response_text
    data["reply_markup"] = None  # Клавиатура не нужна

    # Редактируем сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем состояние ожидания ввода порогов
    await state.set_state(AdminStates.setting_thresholds)


# 2. Хэндлер для обработки ввода значений порогов
@router.message(StateFilter(AdminStates.setting_thresholds), F.text)
@log_handler_call
async def process_thresholds_input(message: Message, state: FSMContext, data: dict):
    if not message.text:
#         await message.answer("Введите значения порогов через пробел.")
        await message.answer(get_text("owner.enter_value_thresholds_through_space", lang=data.get("lang","ru")))

        raise ValueError("Введено пустое значение")
    if not message.from_user:
        raise ValueError("Отправтель сообщения отсутствует (from_user == None)")

    logger.info(f"Пользователь {message.from_user.id} ввел пороги: {message.text}")
    try:
        # Заменяем запятую на точку для единообразия
        input_text = message.text.replace(",", ".")

        # Разбиваем введенные данные на список чисел
        thresholds = list(map(float, input_text.split()))

        # Проверяем, что введено ровно два значения
        if len(thresholds) != 2:
            raise ValueError("Неверное количество значений. Введите ровно два числа.")

        # Сохраняем данные в FSM
        await state.update_data(
            threshold_in_voices=thresholds[0], threshold_in_percent=thresholds[1]
        )

        threshold_in_voices=thresholds[0],
        threshold_in_percent=thresholds[1]

        # Формируем текст для подтверждения
        confirmation_text = (
#             f"Подтвердите пороги доверенных голосов:\n"
            get_text("owner.confirm_thresholds_trusted_votes", lang=data.get("lang","ru")).format(
                threshold_in_voices = threshold_in_voices,
                threshold_in_percent = threshold_in_percent
                )

            # f"1. Минимальное количество голосов: {threshold_in_voices}\n"
            # f"2. Минимальный процент от общего числа голосов: {threshold_in_percent}\n"
            # "Всё верно?"
        )

        # Отправляем сообщение с подтверждением
        markup = confirm_markup(lang=data.get("lang","ru"))
        await message.answer(text=confirmation_text, reply_markup=markup)
        await state.set_state(AdminStates.setting_thresholds)

    except ValueError as e:
        logger.warning(
            f"Ошибка ввода порогов от пользователя {message.from_user.id}: {e}"
        )
        await message.answer(
#             text=f"Некорректный ввод: {e}\n"
            text=get_text("owner.invalid_input_value", lang=data.get("lang","ru")).format(e=e)

            # "Пожалуйста, введите два числа через пробел.\n"
            # "Разделителем между целой и дробной частью может быть точка или запятая."
        )


# 3. Хэндлер для подтверждения ввода
@router.callback_query(
    StateFilter(AdminStates.setting_thresholds), F.data == "ConfirmOK"
)
@log_handler_call
async def confirm_thresholds(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'ВСЁ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    club_id = data["club_id"]
    result = await update_thresholds(
        club_id=club_id,
        threshold_in_voices=fsm_data["threshold_in_voices"],
        threshold_in_percent=fsm_data["threshold_in_percent"],
    )

    # Формируем ответ
    response_text = (
        result if isinstance(result, str) else "Произошла ошибка при сохранении данных."
    )
    markup = await user_menu(status= data.get("user_status", "user"))

    # Отправляем ответ и завершаем машину состояний
    await safe_edit(callback, text=response_text, reply_markup=markup)  # type: ignore
    await state.clear()


# 4. Хэндлер для отмены подтверждения
@router.callback_query(
    StateFilter(AdminStates.setting_thresholds), F.data == "ConfirmNotOK"
)
@log_handler_call
async def cancel_thresholds(callback: CallbackQuery, state: FSMContext, data: dict):
    logger.info(f"Кнопка 'НЕВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()

    # Завершаем машину состояний
    await state.clear()

    # Отправляем сообщение об отмене
#     response_text = "Установка порогов доверенных голосов отменена."
    response_text = get_text("owner.setting_thresholds_trusted_votes_cancelled", lang=data.get("lang","ru"))

    markup = await user_menu(status= data.get("user_status", "user"))
    await safe_edit(callback, text=response_text, reply_markup=markup)  # type: ignore
