import logging

from aiogram import F, Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, ReplyKeyboardRemove)

from data_base.db_member import trust

from data_base.telegram_bot_logic import *
from filters.filters import StatusFilter
from FSMs.FSMs import (FSM_appoint_deputy, FSM_become_proxy,
                       FSM_become_registrator)
from keyboards.keyboards import (confirm_markup, return_to_main_menu_markup,
                                 user_menu)
from services.services import (not_votist_because_proxy_quit,
                               votist_because_proxy_returned)
from utils import log_handler_call, paginate, safe_edit

# Настройка логирования
logger = logging.getLogger(__name__)


# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(StatusFilter(required_status=["member"]))
router.callback_query.filter(StatusFilter(required_status=["member"]))


# Хэндлер для выбора конкретного варианта при голосовании
@router.callback_query(F.data.regexp(r"^variant:\d+$"))
@log_handler_call
async def process_variant_selection(callback: CallbackQuery, data: dict):
    """
    Обработчик выбора конкретного варианта голосования.
    """
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return
        logger.info(
            f"Пользователь {callback.from_user.id} выбрал вариант: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        variant_id = int(callback.data.split(":")[1])
        member_id = data["member_id"]
        success, message = await election(member_id, variant_id)

        if success:
            text = f"{message}\n\nВоспользуйтесь кнопками под последним сообщением для дальнейших действий"
        else:
            text = f"Ошибка при голосовании: {message}"

        # markup = create_inline_kb(1, 'main_menu')

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = None  # markup

        # Отправляем ответ
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при выборе конкретного варианта голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при голосовании."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Отправляем новое сообщение в случае ошибки
        await callback.message.answer(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для кнопки 'select_proxy' обычным участником
@router.callback_query(
    F.data.startswith("select_proxy"), ~StatusFilter(required_status=["proxy"])
)
@log_handler_call
async def process_select_proxy(callback: CallbackQuery, data: dict):
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} запросил список представителей."
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        try:
            # Проверяем, что callback.data существует
            if callback.data is None:
                logger.warning("Callback data отсутствует")
                await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
                return
            _, page = callback.data.split(":")
            page = int(page) if page.isdigit() else 1
        except ValueError:
            page = 1

        proxies = await list_of_proxy(data["club_id"])

        if not proxies:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "В данный момент нет доступных представителей."
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Разделяем на страницы
        paginated_proxies, total_pages = paginate(proxies, page)

        # Создаем кнопки для представителей
        proxy_buttons = []
        for proxy in paginated_proxies:
            # Кнопка для доверия голосов
            trust_button = InlineKeyboardButton(
                text=f"{proxy['username']} ({proxy['trusted_votes']})",
                callback_data=f"trust:{proxy['member_id']}",
            )
            # Кнопка для получения подробной информации
            details_button = InlineKeyboardButton(
                text="Подробная информация",
                callback_data=f"proxy_details:{proxy['member_id']}:{proxy['trusted_votes']}:{page}",
            )
            # Добавляем кнопки в список
            proxy_buttons.append([trust_button, details_button])

        # Добавляем кнопки пагинации
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"select_proxy:{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Вперед", callback_data=f"select_proxy:{page + 1}"
                )
            )

        # Добавляем кнопку "Главное меню"
        main_menu_button = InlineKeyboardButton(
            text="Главное меню", callback_data="main_menu"
        )

        # Создаем инлайн-клавиатуру
        markup = InlineKeyboardMarkup(
            inline_keyboard=proxy_buttons + [pagination_buttons, [main_menu_button]]
        )

        # Редактируем сообщение
        data["response_text"] = (
            "Выберите представителя, которому вы доверите свой голос:"
        )
        data["reply_markup"] = markup
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при загрузке списка представителей."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для доверия голоса
@router.callback_query(
    F.data.startswith("trust:"), ~StatusFilter(required_status=["proxy"])
)
@log_handler_call
async def process_trust(callback: CallbackQuery, data: dict):
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return
        proxy = int(callback.data.split(":")[1])
        logger.info(
            f"Пользователь {callback.from_user.id} доверил свой голос пользователю с tg_id {proxy}."
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        ans_str = await trust(data["member_id"], proxy)

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = ans_str
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при доверии голоса: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при доверии голоса."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер предоставления подробной информации
@router.callback_query(F.data.startswith("proxy_details:"))
@log_handler_call
async def process_proxy_details(callback: CallbackQuery, data: dict):
    try:
        # Проверяем, что callback.data существует
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return
        parts = callback.data.split(":")
        if len(parts) < 4:
            await callback.answer("Некорректные данные.")
            return

        try:
            proxy_id = int(parts[1])
            trusted_votes = int(parts[2])
            page = int(parts[3]) if len(parts) > 3 else 1
        except (ValueError, IndexError):
            await callback.answer("Ошибка в данных.")
            return
        logger.info(
            f"Пользователь {callback.from_user.id} запросил подробную информацию о представителе с ID {proxy_id}."
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        # Получаем информацию о представителе
        proxy_info = await get_profile(proxy_id)
        if not proxy_info:
            await callback.message.answer(  # type: ignore
                text="Не найдена информация о представителе",
                reply_markup=return_to_main_menu_markup,
            )
            return

        # Формируем текст с подробной информацией
        text = f"Username: {proxy_info['username']}\nОписание: {proxy_info['description']}\nЧисло доверенных голосов: {trusted_votes}"

        proxies = await list_of_proxy(data["club_id"])

        if not proxies:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "В данный момент нет доступных представителей."
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Разделяем на страницы
        paginated_proxies, total_pages = paginate(proxies, page)

        # Создаем кнопки для представителей
        proxy_buttons = []
        for proxy in paginated_proxies:
            # Кнопка для доверия голосов
            trust_button = InlineKeyboardButton(
                text=f"{proxy['username']} ({proxy['trusted_votes']})",
                callback_data=f"trust:{proxy['member_id']}",
            )
            # Кнопка для получения подробной информации
            details_button = InlineKeyboardButton(
                text="Подробная информация",
                callback_data=f"proxy_details:{proxy['member_id']}:{proxy['trusted_votes']}:{page}",
            )
            # Добавляем кнопки в список
            proxy_buttons.append([trust_button, details_button])

        # Добавляем кнопки пагинации
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"select_proxy:{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Вперед", callback_data=f"select_proxy:{page + 1}"
                )
            )

        # Добавляем кнопку "Главное меню"
        main_menu_button = InlineKeyboardButton(
            text="Главное меню", callback_data="main_menu"
        )

        # Создаем инлайн-клавиатуру
        markup = InlineKeyboardMarkup(
            inline_keyboard=proxy_buttons + [pagination_buttons, [main_menu_button]]
        )

        # Редактируем сообщение
        data["response_text"] = text
        data["reply_markup"] = markup

        await safe_edit(callback,
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при получении подробной информации о представителе: {e}")
        await callback.message.answer("Произошла ошибка при получении информации о представителе.")  # type: ignore


# Хэндлер для кнопки 'select_subproxy' представителем (выбор заместителя)
@router.callback_query(
    F.data == "select_subproxy",
    StatusFilter(required_status=["proxy"]),
    StateFilter(default_state),
)
@log_handler_call
async def process_select_deputy(callback: CallbackQuery, data: dict, state: FSMContext):
    try:
        logger.info(f"Представитеь {callback.from_user.id} хочет выбрать заместителя.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        # Добавляем данные для SafeEditMiddleware
        data[
            "response_text"
        ] = """Пожалуйста, введите телеграм-ID участника,
    которого вы хотите псделать своим заместителем или отправьте контакт с ID"""
        data["reply_markup"] = None  # Если клавиатура не нужна, устанавливаем None

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Устанавливаем состояние ожидания ввода ID
        await state.set_state(FSM_appoint_deputy.fill_id)
        logger.info(f"Установлено состояние: {await state.get_state()}")

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'select_subproxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при загрузке списка представителей."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        raise  # Передаем исключение middleware для обработки


@router.message(
    StatusFilter(required_status=["proxy"]),
    StateFilter(FSM_appoint_deputy.fill_id),
    F.text.isdigit() | F.contact,
)
@log_handler_call
async def process_appoint_deputy(message: Message, data: dict, state: FSMContext):
    try:
        if not message.from_user:
            raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

        user_id = message.from_user.id
        member_id = data.get("member_id")
        if not member_id:
            raise ValueError("ID пользователя отсутствует")
        club_id = data.get("club_id")
        if not club_id:
            raise ValueError("ID клуба отсутствует")

        if message.contact:
            deputy_tg_id = message.contact.user_id
        else:
            if message.text is None:
                raise ValueError("Текст сообщения отсутствует")
            deputy_tg_id = int(message.text)

        if not deputy_tg_id:  # type: ignore
            raise ValueError("ID заместителя отсутствует")

        logger.info(
            f"Представитель {user_id} выбрал своим заместителем пользователя с tg_id {deputy_tg_id}."
        )

        deputy_user_id, deputy_member_id = await extract_user_member_id(club_id, deputy_tg_id)

        ans_str = await trust(member_id, deputy_member_id)

        if not ans_str:
            ans_str = "Неизвестная ошибка при назначении заместителя."

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = ans_str
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Отвечаем
        await message.answer(
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при выборе заместителя: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при выборе заместителя."
        data["reply_markup"] = (
            await user_menu(status = data.get("user_status", ["user"]))
            if message.from_user
            else ReplyKeyboardRemove()
        )

        # Отправляем сообщение в случае ошибки
        await message.answer(
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        await state.clear()

        raise


# Хэндлер для кнопки 'become_proxy'
@router.callback_query(F.data == "become_proxy", StateFilter(default_state))
@log_handler_call
async def process_become_proxy(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} запросил статус 'proxy'.")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
        if not callback.bot:
            raise ValueError("Не удалось получить бота")
        bot:Bot = callback.bot

        member_id = data["member_id"]
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы не являетесь участником группы."
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        if "proxy" in data["user_status"]:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы уже являетесь представителем"
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        profile = await get_profile(data["member_id"])
        if not profile:
            await callback.message.answer(text="Не найден профиль пользователя")  # type: ignore
            return
        if profile.get("username"):
            # Присваиваем статус 'proxy'
            await new_status(member_id, member_id, "proxy")
            # Присваиваем статус 'votist' (если его не было)
            await new_status(member_id, member_id, "votist")
            # Присваем статус 'votist' тем, кто каким-то образом уже доверил ему голос
            await votist_because_proxy_returned(bot, member_id)

            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы стали представителем!"
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            await state.clear()
        else:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (
                "Введите уникальное имя или псевдоним."
                "Это может быть ваше собственное имя (фамилия)."
                "Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей."
                "И желательно не длиннее 40 символов"
            )
            data["reply_markup"] = None

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

            await state.set_state(FSM_become_proxy.fill_username)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'become_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при присвоении статуса представителя."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        await state.clear()

        raise  # Передаем исключение middleware для обработки


@router.message(StateFilter(FSM_become_proxy.fill_username), F.text)
@log_handler_call
async def process_username_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода имени/псевдонима.
    Запрашивает подтверждение.
    """
    if not message.from_user:
        logger.error("Отправитель сообщения не определён.")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()
        return

    user_id = message.from_user.id

    # Явная проверка наличия текста (гарантирована фильтром, но Pylance хочет явности)
    if not message.text:
        logger.error("Получено сообщение без текста")
        await message.answer("Введите псевдоним.")
        return

    username: str = message.text  # Теперь безопасно

    logger.info(f"Пользователь {user_id} ввёл свой псевдоним: {username}.")

    flag = await is_username_uniq(username)
    if flag:
        await state.update_data(username=username)
        # Отправляем сообщение с подтверждением
        await message.answer(
            text=f"""Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?
{username}""",
            reply_markup=confirm_markup,
        )
        await state.set_state(FSM_become_proxy.fill_OK)
    else:
        await message.answer(
            text="Такое имя/псевдоним уже есть. Попробуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас"
        )


# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении username


@router.callback_query(StateFilter(FSM_become_proxy.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def process_username_entry(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(
        f"Кнопка 'ВСЁ ВЕРНО' при подтверждении username нажата пользователем {callback.from_user.id}"
    )
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot

    fsm_data = await state.get_data()
    username = fsm_data["username"]
    user_id = data["user_id"]
    member_id = data["member_id"]

    try:
        # Записываем username в базу данных
        await update_user_data(user_id, username=username)
        # Присваиваем статус 'proxy'
        await new_status(member_id, member_id, "proxy")
        # Присваиваем статус 'votist' (если его не было)
        await new_status(member_id, member_id, "votist")
        # Присваем статус 'votist' тем, кто каким-то образом уже доверил ему голос
        await votist_because_proxy_returned(bot, member_id)

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Вы стали представителем!"
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Завершаем машину состояний
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при записи username: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = f"Произошла ошибка: {str(e)}"
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSM_become_proxy.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_no_confirm_proxy_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        "Спасибо! Псевдоним не доавлен\nПопробуйте еще раз, или нажмите кнопку для прерывания процедуры"
    )
    data["reply_markup"] = return_to_main_menu_markup

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    await state.set_state(FSM_become_proxy.fill_username)


@router.message(StateFilter(FSM_become_proxy.fill_OK))
@log_handler_call
async def warning_new_status(message: Message):
    user_id = message.from_user.id if message.from_user else "неизвестный пользователь"
    logger.warning(
        f"Некорректный ввод от пользователя {user_id} в состоянии FSM_become_proxy.fill_OK"
    )

    await message.answer(
        text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        "Если вы хотите прервать изменение статуса - "
        "отправьте команду /cancel"
    )


# Хэндлер для кнопки ''resign_from_proxy''
@router.callback_query(F.data == "resign_from_proxy")
@log_handler_call
async def process_resign_from_proxy(callback: CallbackQuery, data: dict):

    logger.info(
        f"Пользователь {callback.from_user.id} отказывается от статуса 'proxy'."
    )

    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot

    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    member_id = data["member_id"]
    if not member_id:
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Вы не являетесь участником группы."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        return

    # Убираем статус 'proxy'
    await new_status(member_id, member_id, "not_proxy")
    await not_votist_because_proxy_quit(bot, member_id)
    flag = await is_votist(member_id)
    text = "Вы перестали быть представителем!"
    if not flag:
        text = (
            "\nВам требуется выбрать себе представителя, чтобы иметь право голосовать"
        )

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = text
    data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

    # Редактируем сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


# Хэндлер для кнопки 'resign_from_registrator'
# Удаляет статус регистратора  или кандидата в регистраторы при отказе быть регистратором
@router.callback_query(F.data == "resign_from_registrator")
@log_handler_call
async def process_resign_from_registrator(callback: CallbackQuery, data: dict):
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} отказывается от статуса 'registrator'."
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = data["member_id"]
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы не являетесь участником группы."
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Убираем статус 'registrator'
        await new_status(member_id, member_id, "not_registrator")  # Для регистратора
        await new_status(
            member_id, member_id, "not_pre-registrator"
        )  # Для кандидата в регистраторы
        text = "Вы отказались от роли регистратора!"

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'resign_from_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при удалении статуса представителя."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для кнопки 'resign_from_admin'
# Удаляет статус администратора при отказе быть администратором
@router.callback_query(F.data == "resign_from_admin")
@log_handler_call
async def process_resign_from_admin(callback: CallbackQuery, data: dict):
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} отказывается от статуса 'admin'."
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = data["member_id"]
        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы не являетесь участником группы."
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Убираем статус 'registrator'
        await new_status(member_id, member_id, "not_admin")
        text = "Вы отказались от роли администратора!"

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'resign_from_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при удалении статуса администратора."
        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


@router.callback_query(
    F.data.regexp(r"^pre_registrator_yes:\d+:\d+$"), StateFilter(default_state)
)
@log_handler_call
async def process_become_registrator(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    try:
        if not callback.from_user:
            logger.error("Отправитель callback не определён.")
            await callback.answer("Ошибка: пользователь не найден")
            return

        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} дал согласие стать регистратором.")

        await callback.answer()  # Подтверждаем callback

        # Проверяем, что callback.data существует
        if not callback.data:
            logger.warning("Данные callback пусты")
            await safe_edit(callback, "Произошла ошибка: данные не найдены.")  # type: ignore
            return

        # Парсим callback_data
        action, admin_id, member_tg_id = callback.data.split(":")
        admin_id = int(admin_id)
        member_tg_id = int(member_tg_id)

        # Проверяем, что пользователь тот же, что и в данных
        if user_id != member_tg_id:
            data["response_text"] = (
                "Предложение стать регистратором предназначалось не вам"
            )
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Получаем member_id из данных
        member_id = data.get("member_id")
        if not member_id:
            data["response_text"] = "Вы не являетесь участником группы."
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        if "registrator" in data.get("user_status", []):
            data["response_text"] = "Вы уже являетесь регистратором"
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        if "pre-registrator" not in data.get("user_status", []):
            data["response_text"] = "Вы не являетесь кандидатом в регистраторы"
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Получаем профиль пользователя
        profile = await get_profile(data["member_id"])
        if not profile:
            logger.error("Профиль пользователя не найден")
            await safe_edit(callback, "Ошибка: профиль не найден.")  # type: ignore
            return

        username = profile.get("username")

        if username:
            await new_status(member_id, member_id, "registrator")
            await new_status(member_id, member_id, "not_pre-registrator")

            data["response_text"] = "Вы стали регистратором!"
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            await state.clear()
        else:
            data["response_text"] = (
                "Введите уникальное имя или псевдоним.\n"
                "Это может быть ваше собственное имя (фамилия).\n"
                "Важно, чтобы оно было уникальным для этой группы,\n"
                "чтобы пользователи различали представителей.\n"
                "Желательно не длиннее 40 символов."
            )
            data["reply_markup"] = None

            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

            await state.set_state(FSM_become_registrator.fill_username)

    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.warning("Попытка изменить сообщение с тем же текстом")
        elif "message to edit not found" in str(e):
            logger.warning("Сообщение для редактирования не найдено")
        else:
            logger.error(f"Telegram API ошибка: {e}")
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'pre_registrator_yes': {e}")

        data["response_text"] = "Произошла ошибка при присвоении статуса регистратора."
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise


# Хэндлер для позднего согласия стать регистратором (кнопка основного меню become_registrator: )
@router.callback_query(F.data == "become_registrator", StateFilter(default_state))
@log_handler_call
async def process_become_registrator_own(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} дал согласие стать регистратором."
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        member_id = data["member_id"]
        status = data.get("user_status", ["user"])

        if "registrator" in status:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы уже являетесь регистратором"
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        if "pre-registrator" not in status:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы не являетесь кандидатом в регистраторы"
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Переходим к обработке запроса. Проверяем, есть ли у кандидата псевдоним
        profile = await get_profile(data["member_id"])
        if not profile:
            logger.error("Профиль пользователя не найден")
            await safe_edit(callback, "Ошибка: профиль не найден.")  # type: ignore
            return
        username = profile.get("username")
        # Если есть псевдоним - записываем новый статус
        if username:
            # Присваиваем статус 'registrator'
            await new_status(member_id, member_id, "registrator")
            # Удаляем статус 'pre-registrator'
            await new_status(member_id, member_id, "not_pre-registrator")

            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы стали регистратором!"
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            await state.clear()
        # Если нет псевдонима, просим его создать
        else:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (
                "Введите уникальное имя или псевдоним."
                "Это может быть ваше собственное имя (фамилия)."
                "Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей."
                "И желательно не длиннее 40 символов"
            )
            data["reply_markup"] = None

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

            await state.set_state(FSM_become_registrator.fill_username)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'pre_registrator_yes': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при присвоении статуса представителя."
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        await state.clear()

        raise  # Передаем исключение middleware для обработки


# Хэндлер для отказа стать регистратором (кнопки pre_registrator_no: )
@router.callback_query(
    F.data.regexp(r"^pre_registrator_no:\d+:\d+$"), StateFilter(default_state)
)
@log_handler_call
async def process_not_become_registrator(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} не дал согласие стать регистратором."
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        # Проверяем, что callback.data существует
        if not callback.data:
            logger.warning("Данные callback пусты")
            await safe_edit(callback, "Произошла ошибка: данные не найдены.")  # type: ignore
            return

        # Разбираем callback_data на части
        action, admin_id, member_tg_id = callback.data.split(":")

        # Преобразуем ID в целые числа
        member_tg_id = int(member_tg_id)

        member_id = data["member_id"]

        # Проверяем, что отправитель коллбэка и кандидат в регистраторы - один и тот же аккаунт
        if callback.from_user.id != member_tg_id:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (
                "Предложение стать регистратором предназначалось не вам"
            )
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        if not member_id:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы не являетесь участником группы."
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        if "pre-registrator" not in data["user_status"]:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "Вы не являетесь кандидатом в регистраторы"
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Редактируем сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Удаляем статус 'pre-registrator'
        await new_status(member_id, member_id, "not_pre-registrator")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Вы не стали регистратором!"
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Редактируем сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'pre_registrator_no': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при присвоении статуса представителя."
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Редактируем сообщение в случае ошибки
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
        await state.clear()

        raise  # Передаем исключение middleware для обработки


@router.message(StateFilter(FSM_become_registrator.fill_username), F.text)
@log_handler_call
async def process_reg_username_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода имени/псевдонима.
    Запрашивает подтверждение.
    """
    if not message.from_user:
        logger.error("Отправитель сообщения не определён.")
        await message.answer("Произошла ошибка. Попробуйте позже.")
        await state.clear()
        return

    user_id = message.from_user.id

    # Явная проверка наличия текста (гарантирована фильтром, но Pylance хочет явности)
    if not message.text:
        logger.warning("Получено сообщение без текста")
        await message.answer("Введите псевдоним.")
        return

    username = message.text.strip()  # Теперь безопасно

    logger.info(f"Пользователь {user_id} ввёл свой псевдоним: {username}.")

    flag = await is_username_uniq(username)
    if flag:
        await state.update_data(username=username)
        # Отправляем сообщение с подтверждением
        await message.answer(
            text=f"""Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?
{username}""",
            reply_markup=confirm_markup,
        )
        await state.set_state(FSM_become_registrator.fill_OK)
    else:
        await message.answer(
            text="Такое имя/псевдоним уже есть. Попробуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас"
        )


# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении username


@router.callback_query(
    StateFilter(FSM_become_registrator.fill_OK), F.data == "ConfirmOK"
)
@log_handler_call
async def process_reg_username_entry(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(
        f"Кнопка 'ВСЁ ВЕРНО' при подтверждении username нажата пользователем {callback.from_user.id}"
    )
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    username = fsm_data["username"]
    user_id = data["user_id"]
    member_id = data["member_id"]

    try:
        # Записываем username в базу данных
        await update_user_data(user_id=user_id, username=username)
        # Присваиваем статус 'registrator'
        await new_status(member_id, member_id, "registrator")
        # Удаляем статус 'pre-registrator'
        await new_status(member_id, member_id, "not_pre-registrator")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Вы стали регистратором!"
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))
        # Редактируем сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Завершаем машину состояний
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при записи username: {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = f"Произошла ошибка: {str(e)}"
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(
    StateFilter(FSM_become_registrator.fill_OK), F.data == "ConfirmNotOK"
)
@log_handler_call
async def process_no_confirm_registrator_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        "Спасибо! Псевдоним не доавлен\nПопробуйте ввести псевдоним еще раз, или нажмите кнопку для прерывания процедуры"
    )
    data["reply_markup"] = return_to_main_menu_markup

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    await state.set_state(FSM_become_registrator.fill_username)


@router.message(StateFilter(FSM_become_proxy.fill_OK))
@log_handler_call
async def warning_reg_resume(message: Message):
    if message.from_user:
        user_id = message.from_user.id
    else:
        user_id = "неизвестный пользователь"

    logger.warning(
        f"Некорректный ввод от пользователя {user_id} в состоянии FSM_become_proxy.fill_OK"
    )

    await message.answer(
        text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        "Если вы хотите прервать процедуру - "
        "отправьте команду /cancel"
    )
