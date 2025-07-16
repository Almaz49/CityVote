# Модуль oll_users_handlers
# В нем хэндлеры, которые работают для всех пользователей
import logging
import traceback

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)
from aiogram.utils.text_decorations import html_decoration as html
from FSMs.FSMs import FSM_become_proxy, FSM_profile
from data_base.db_func import extract_status, get_profile, is_username_uniq, list_of_proxy, list_of_votings
from data_base.db_member import update_member_data, update_user_data
from data_base.db_vote import count_votist, extract_member_choise, get_voting_info
from keyboards.keyboards import (confirm_markup, create_inline_kb,
                                 get_profile_menu_keyboard,
                                 return_to_main_menu_markup, user_menu)
from LEXICON.LEXICON import LEXICON
from services.services import (send_variants_by_status)
from utils import log_handler_call, paginate

# Настройка логирования
logger = logging.getLogger(__name__)

# # Загружаем конфиг в переменную config
# config: Config = load_config('.env')

# Инициализируем роутер уровня модуля
router = Router()

"""
ХЭНДЛЕРЫ
"""

# Обновленный универсальный хэндлер для вызова списка голосований.
# Присылает по сообщению на каждое голосование.
@router.callback_query(
    F.data.regexp(r"^(ongoing_votings|completed_votings|future_votings)$")
)
@log_handler_call
async def process_list_of_votings(callback: CallbackQuery, data: dict):
    # Проверяем, что callback.data существует
    if not callback.data:
        logger.warning("Данные callback пусты")
        await callback.message.edit_text("Произошла ошибка: данные не найдены.")  # type: ignore
        raise ValueError("Callback data отсутствует")
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        # Определяем тип голосования на основе callback.data
        voting_type = callback.data.split("_")[
            0
        ]  # 'ongoing', 'completed', или 'future'
        club_id = data["club_id"]

        # Определяем статусы голосований в зависимости от типа
        if voting_type == "ongoing":
            voting_status = ("ongoing", "confirmation")
            header_message = "Список активных голосований:"
            empty_message = "В настоящее время нет активных голосований."
        elif voting_type == "completed":
            voting_status = ("completed",)
            header_message = "Список завершенных голосований:"
            empty_message = "В настоящее время нет завершенных голосований."
        elif voting_type == "future":
            voting_status = ("add_variants",)
            header_message = "Список будущих голосований:"
            empty_message = (
                "В настоящее время нет голосований в стадии добавления вариантов."
            )

        # Получаем список голосований
        votings = await list_of_votings(club_id, *voting_status)

        # Формируем клавиатуру для возврата в главное меню
        main_menu_markup = return_to_main_menu_markup

        if votings:
            # Отправляем заголовок
            await callback.message.answer(header_message)  # type: ignore

            # Отправляем по одному сообщению на каждое голосование
            for i, voting in enumerate(votings):
                await callback.message.answer(  # type: ignore
                    text=(
                        f"🗳️ <b>{voting.get('title')}</b>\n"
                        f"📝 Описание:\n{voting.get('description')}\n\n"
                        f"<i>Выберите это голосование для просмотра вариантов.</i>"
                    ),
                    parse_mode="HTML",
                    reply_markup=create_inline_kb(
                        1,
                        **{
                            f"show_oll_variants:{voting.get('id')}": "Посмотреть варианты"
                        },
                    ),
                )

            # В последнем сообщении добавляем кнопку "Вернуться в главное меню"
            await callback.message.answer(  # type: ignore
                text=LEXICON.get("return_to_main_menu", "Вернуться в главное меню"),
                reply_markup=main_menu_markup,
            )
        else:
            # Если голосований нет, отправляем сообщение об этом и кнопку "Вернуться в главное меню"
            await callback.message.answer(empty_message)  # type: ignore
            await callback.message.answer(  # type: ignore
                text=LEXICON.get("return_to_main_menu", "Вернуться в главное меню"),
                reply_markup=main_menu_markup,
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке списка голосований ({callback.data}): {e}")
        error_info = traceback.extract_tb(e.__traceback__)
        for frame in error_info:
            logger.error(
                f"Ошибка произошла в файле: {frame.filename}, строка: {frame.lineno}, "
                f"функция: {frame.name}, код: {frame.line}"
            )
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при загрузке списка голосований."
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Редактируем сообщение в случае ошибки
        await callback.message.answer(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для просмотра всех вариантов (обрабатывает кнопку "посмотреть все варианты")
# Присылает по сообщению на каждый вариант, к последнему прикладывает клавиатуру из меню.
# Варианты отсортиованы по числу голосов
# Для членов группы - под каждым вариантом кнопка для голосования
@router.callback_query(F.data.regexp(r"^show_oll_variants:\d+$"))
@log_handler_call
async def process_show_oll_variants(callback: CallbackQuery, data: dict):
    """
    Обработчик просмотра вариантов.
    """
    # Проверяем, что callback.data существует
    if not callback.data:
        logger.warning("Данные callback пусты")
        await callback.message.edit_text("Произошла ошибка: данные не найдены.")  # type: ignore
        raise ValueError("Callback data отсутствует")
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} запросил просмотр вариантов: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        voting_id = int(callback.data.split(":")[1])
        voting_info = await get_voting_info(voting_id)
        s_votist = await count_votist(data["club_id"])

        if voting_info:
            voting_status = voting_info.get("voting_status")
            voting_title = voting_info.get("title")
        else:
            voting_status = None
            voting_title = None

        choise = await extract_member_choise(data["member_id"], voting_id)

        # Экранируем специальные символы в тексте
        escaped_voting_title = (
            html.quote(voting_title) if voting_title else "Без названия"
        )

        await callback.message.answer(  # type: ignore
            text=(
                f"Список вариантов к голосованию\n" f"<b>{escaped_voting_title}</b>\n"
            ),
            parse_mode="HTML",
        )

        flag = False

        success = await send_variants_by_status(
            callback, "winner", voting_id, data["member_id"], data["user_status"]
        )

        if success:
            flag = True

        success = await send_variants_by_status(
            callback, "valid", voting_id, data["member_id"], data["user_status"]
        )
        if success:
            flag = True

        success = await send_variants_by_status(
            callback, "loser", voting_id, data["member_id"], data["user_status"]
        )
        if success:
            flag = True

        if flag:
            text = (
                f"Всего действительных голосов в группе: {s_votist}\n"
                "Выберите дальнейшее действие"
            )
        else:
            text = "В настоящее время нет доступных вариантов."

        # Формируем меню в зависимости от статуса голосования и статуса пользователя
        dict_menu = {}
        if voting_status == "add_variants":
            dict_menu["future_votings"] = LEXICON.get(
                "back_to_votings", "Назад к списку голосований"
            )
            if "delegate" in data["user_status"]:
                dict_menu[f"create_variant:{voting_id}"] = LEXICON.get(
                    "create_variant", "Добавить вариант"
                )
            if "admin" in data["user_status"]:
                dict_menu[f"admin_voting:{voting_id}"] = LEXICON.get(
                    "admin_voting", "Администрирование голосования"
                )
        elif voting_status == "completed":
            dict_menu["completed_votings"] = LEXICON.get(
                "back_to_votings", "Назад к списку голосований"
            )
            # Пока не администрируем завершенные голосования (не перезапускаем)
            # if 'admin' in data["user_status"]:
            #     dict_menu[f'admin_voting:{voting_id}'] = LEXICON.get('admin_voting', 'Администрирование голосования')
        elif voting_status == "ongoing":
            if "admin" in data["user_status"]:
                dict_menu[f"admin_voting:{voting_id}"] = LEXICON.get(
                    "admin_voting", "Администрирование голосования"
                )
            dict_menu["ongoing_votings"] = LEXICON.get(
                "back_to_votings", "Назад к списку голосований"
            )
        elif voting_status == "confirmation":
            if "admin" in data["user_status"]:
                dict_menu[f"admin_voting:{voting_id}"] = LEXICON.get(
                    "admin_voting", "Администрирование голосования"
                )
            dict_menu["ongoing_votings"] = LEXICON.get(
                "back_to_votings", "Назад к списку голосований"
            )

        dict_menu["main_menu"] = LEXICON.get(
            "return_to_main_menu", "Вернуться в главное меню"
        )

        logger.info(f"Словарь меню при показе вариантов: {dict_menu}")
        markup = create_inline_kb(1, **dict_menu)

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Отправляем сообщение
        await callback.message.answer(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(
            f"Ошибка при просмотре вариантов голосования: {e}\n{traceback.format_exc()}"
        )
        error_info = traceback.extract_tb(e.__traceback__)
        for frame in error_info:
            logger.error(
                f"Ошибка произошла в файле: {frame.filename}, строка: {frame.lineno}, "
                f"функция: {frame.name}, код: {frame.line}"
            )
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при просмотре вариантов голосования."
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Отправляем сообщение в случае ошибки
        await callback.message.answer(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки




# Хэндлер для кнопки 'proxy_list'
@router.callback_query(F.data.startswith("proxy_list"))
@log_handler_call
async def process_proxy_list(callback: CallbackQuery, data: dict):
    """
    Обработчик команды /proxy_list.
    Отправляет список представителелей.
    """
    logger.info(f"Пользователь {callback.from_user.id} requested proxy list.")
    try:
        if callback.data is None:
            logger.warning("Callback data отсутствует")
            await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
            return
        # Получаем номер страницы из callback.data
        if ":" in callback.data:
            try:
                page = int(callback.data.split(":")[1])
            except (IndexError, ValueError) as e:
                logger.warning(f"Ошибка при разборе номера страницы: {e}")
                page = 1
        else:
            page = 1

        proxies = await list_of_proxy(data["club_id"])

        if not proxies:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "В данный момент нет доступных представителей."
            data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

            # Редактируем сообщение
            await callback.message.edit_text(  # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Разделяем на страницы
        paginated_proxies, total_pages = paginate(proxies, page)
        # Формируем сообщение с HTML-разметкой
        message_text = "<b>Список представителей:</b>\n\n"

        # Создаем кнопки для представителей
        proxy_buttons = []

        for proxy in paginated_proxies:
            proxy_status = await extract_status(proxy["member_id"])

            username = proxy["username"]
            votes = proxy["trusted_votes"]

            # Определение статуса
            status_label = (
                LEXICON.get("user_status", {}).get("delegate", "делегат")
                if "delegate" in proxy_status
                else LEXICON.get("user_status", {}).get("proxy", "представитель")
            )

            # Формирование строки с HTML разметкой
            message_text += (
                f"👤 <b>{html.quote(username)}</b>\n"
                f"🗳️ Голоса: <code>{votes}</code>\n"
                f"🔖 Статус: {status_label}\n"
                "──────────────\n"
            )

            # Кнопка для просмотра информации о представителе
            proxy_button = InlineKeyboardButton(
                text=f"{username} ({votes})",
                callback_data=f"proxy_info:{proxy['member_id']}:{page}",
            )

            # Добавяем кнопки в список
            proxy_buttons.append([proxy_button])

        message_text += "\nДля более подробной информации о представителе нажмите на соответствующую кнопку."

        # Добавляем кнопки пагинации
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"proxy_list:{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Вперед", callback_data=f"proxy_list:{page + 1}"
                )
            )

        # Добавяем кнопку "Главное меню"
        main_menu_button = InlineKeyboardButton(
            text="Главное меню", callback_data="main_menu"
        )

        # Создаем инлайн-клавиатуру
        markup = InlineKeyboardMarkup(
            inline_keyboard=proxy_buttons + [pagination_buttons, [main_menu_button]]
        )

        # Редактируем сообщение
        data["response_text"] = message_text
        data["reply_markup"] = markup
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"],
            reply_markup=data["reply_markup"],
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'select_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при загрузке списка представителей."
        data["reply_markup"] = await user_menu(status= data.get("user_status", "user"))

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для кнопки 'proxy_info'
@router.callback_query(F.data.startswith("proxy_info"))
@log_handler_call
async def process_proxy_info(callback: CallbackQuery, data: dict):
    """
    Обработчик кнопки 'proxy_info'
    Отправляет информацию об определенном представителе.
    """

    if not callback.data:
        logger.warning("Callback data отсутствует в process_proxy_info")
        await callback.answer("Произошла ошибка. Данные не найдены.")
        return
    if not callback.message:
        logger.warning("Message отсутствует в process_proxy_info")
        await callback.answer("Произошла ошибка. Сообщение не найдено.")
        return

    try:
        proxy_id = int(callback.data.split(":")[1])
        # Продолжаем обработку с proxy_id
        proxy_info = await get_profile(proxy_id)
        if not proxy_info:
            await callback.answer("Произошла ошибка. Данные не найдены.")
            return
        logger.info(
            f"Пользователь {callback.from_user.id} запросил информацию о представителе с ID {proxy_id}."
        )
        text = f"{proxy_info['username']}\n" f"Описание:\n{proxy_info['description']}\n"
        try:
            page = callback.data.split(":")[2]
            page = int(page) if page.isdigit() else 1
        except ValueError:
            page = 1

        dict_menu = {}
        dict_menu[f"proxy_list:{page}"] = LEXICON.get(
            "proxy_list", "Список представителей"
        )
        if "member" in data["user_status"] and "proxy" not in data["user_status"]:
            dict_menu[f"select_proxy:{proxy_id}"] = LEXICON.get(
                "select_proxy", "Выбрать этого представителя"
            )
        dict_menu["main_menu"] = LEXICON.get("main_menu", "Главное меню")
        markup = create_inline_kb(1, **dict_menu)

        # Сохраняем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except (IndexError, ValueError) as e:
        logger.error(f"Ошибка при разборе callback.data: {e}")
        await callback.answer("Некорректные данные.")
        return



# ХЭНДЛЕРЫ ИЗМЕНЕНИЯ ПСЕВДОНИМА


@router.callback_query(F.data == "edit_username", StateFilter(default_state))
@log_handler_call
async def press_edit_username(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик команды /edit_username.
    Редактирует псевдоним пользователя.
    """
    logger.info(
        f"Пользователь {callback.from_user.id} начал редактирование псевдонима."
    )

    # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.answer()
    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        "Введите уникальное имя или псевдоним."
        "Это может быть ваше собственное имя (фамилия)."
        "Важно, чтобы оно было уникальным для этой группы, чтобы пользователи различали представителей."
        "И желательно не длиннее 40 символов"
    )
    data["reply_markup"] = return_to_main_menu_markup

    # Редактируем сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    await state.set_state(FSM_profile.fill_username)


@router.message(StateFilter(FSM_profile.fill_username))
@log_handler_call
async def process_username_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода имени/псевдонима.
    Проверяет уникальность псевдонима.
    Запрашивает подтверждение.
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.info(
        f"Пользователь {message.from_user.id} ввел свой псевдоним: {message.text}."
    )

    if message.text is None:
        await message.answer(
            text="Ошибка: пустое сообщение. Пожалуйста, введите псевдоним."
        )
        raise ValueError("Сообщение пустое")

    flag = await is_username_uniq(message.text)
    if flag:
        await state.update_data(username=message.text)
        # Отправляем сообщение с подтверждением
        await message.answer(
            text=f"""Пожалуйста, подтвердите, правильно ли введено ваше имя/псевдоним?
    {message.text}""",
            reply_markup=confirm_markup,
        )
        await state.set_state(FSM_profile.fill_OK)
    else:
        await message.answer(
            text="Такое имя/псевдоним уже есть. Попрбуйте придумать другой псевдоним или добавьте что-нибудь, что выделяло бы вас",
            reply_markup=return_to_main_menu_markup,
        )


@router.callback_query(StateFilter(FSM_profile.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def press_username_entry(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик нажатия кнопки согласия.
    Записывает в БД новый певдоним
    """
    logger.info(
        f"Кнопка 'ВСЁ ВЕРНО' при подтверждении username нажата пользователем {callback.from_user.id}"
    )
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    fsm_data = await state.get_data()
    username = fsm_data["username"]
    user_id = data["user_id"]
    status = data["user_status"]

    # Записываем username в базу данных
    await update_user_data(user_id=user_id, username=username)

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = "Ваш псевдоним изменен!"
    data["reply_markup"] = get_profile_menu_keyboard(status)

    # Редактируем сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Завершаем машину состояний
    await state.clear()


@router.callback_query(StateFilter(FSM_profile.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_no_confirm_username_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик нажатия кнопки несогласия.
    Предлагает повторить
    """
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        "Спасибо! Псевдоним не изменен\nПопробуйте еще раз, или нажмите кнопку для прерывания процедуры"
    )
    data["reply_markup"] = return_to_main_menu_markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    await state.set_state(FSM_profile.fill_username)


@router.message(StateFilter(FSM_profile.fill_OK))
@log_handler_call
async def warning_new_username(message: Message):
    """
    Обработчик ввода текста когда ожидается нажатие кнопки
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(
        f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSM_become_proxy.fill_OK}"
    )
    await message.answer(
        text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        "Если вы хотите прервать изменение статуса - "
        "нажмите кнопку или отправьте команду /cancel",
        reply_markup=return_to_main_menu_markup,
    )


# ХЭНДЛЕРЫ ИЗМЕНЕНИЯ ОПИСАНИЯ ПОЛЬЗОВАТЕЛЯ


@router.callback_query(F.data == "edit_description", StateFilter(default_state))
@log_handler_call
async def press_edit_description(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик команды /edit_description.
    Редактирует радел О СЕБЕ.
    """
    logger.info(
        f"Пользователь {callback.from_user.id} начал редактирование раздела О СЕБЕ."
    )

    # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.answer()
    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
        "Напишите, что бы вы хотели рассказать о себе другим участникам группы.\n"
        "Если вы станете представителем - этот раздел смогут прочитать потенциальные подписчики\n"
        "Если хотите прервать процедуру - нажмите кнопку или наберите /cancel"
    )
    data["reply_markup"] = return_to_main_menu_markup

    # Редактируем сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    await state.set_state(FSM_profile.fill_description)


@router.message(StateFilter(FSM_profile.fill_description))
@log_handler_call
async def process_description_sent(message: Message, state: FSMContext, data: dict):
    """
    Обработчик ввода О СЕБЕ.
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.info(f"Пользователь {message.from_user.id} ввел О СЕБЕ: {message.text}.")
    # member_data = {'description': message.text}
    member_id = data["member_id"]
    status = data["user_status"]

    # Записываем username в базу данных
    await update_member_data(member_id=member_id, description=message.text)

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = 'Раздел "О себе" изменен!'
    data["reply_markup"] = get_profile_menu_keyboard(status)

    # Редактируем сообщение
    await message.answer(text=data["response_text"], reply_markup=data["reply_markup"])

    # Завершаем машину состояний
    await state.clear()


# ХЭНДЛЕРЫ ВЫБОРА УРОВНЯ ИНФОРМИРОВАНИЯ
@router.callback_query(F.data == "change_info_level", StateFilter(default_state))
@log_handler_call
async def press_edit_info_level(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик команды /change_info_level.
    Редактирует уровень информирования.
    """
    logger.info(
        f"Пользователь {callback.from_user.id} начал выбор уровня информирования."
    )

    # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.answer()
    menu_list = ["max_info", "average_info", "min_info"]

    data["response_text"] = (
        "Выберите уровень информирования.\n"
        "Максимальный: бот будет присылать все сообщения о создании голосований и их ходе.\n"
        "Средний: бот будет присылать сообщения о начале голосвания и его финальных этапах.\n"
        "Минимальный: вы не будете получать сообщений от бота о ходе голосований.\n"
        "При любом уровне информирования вы будете получать важные сообщения от администрации и своего представителя"
    )
    data["reply_markup"] = create_inline_kb(1, *menu_list)

    # Редактируем сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )
    await state.set_state(FSM_profile.fill_info_level)


@router.callback_query(
    F.data.in_({"max_info", "average_info", "min_info"}),
    StateFilter(FSM_profile.fill_info_level),
)
@log_handler_call
async def process_info_level_selection(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик выбора уровня информирования.
    Сохраняет выбранный уровень информирования в БД.
    """
    # Получаем ID пользователя
    member_id = data["member_id"]

    # Определяем выбранный уровень информирования
    selected_level = callback.data  # 'max_info', 'average_info' или 'min_info'

    # Формируем текст подтверждения
    level_description = {
        "max_info": "Максимальный уровень информирования",
        "average_info": "Средний уровень информирования",
        "min_info": "Минимальный уровень информирования",
    }
    # 假设 level_description 是 dict[str, str]
    if selected_level is None:
        confirmation_text = "Вы выбрали: Неизвестный уровень"
    else:
        confirmation_text = f"Вы выбрали: {level_description.get(selected_level, 'Неизвестный уровень')}"
    # Before:
    # info_level = selected_level.split('_')[0]

    # After:
    if selected_level is not None:
        info_level = selected_level.split("_")[0]
    else:
        info_level = "default"  # or handle accordingly

    try:
        # Обновляем данные пользователя в БД
        await update_member_data(member_id=member_id, info_level=info_level)
        logger.info(
            f"Пользователь {member_id} установил уровень информирования: {selected_level}"
        )

        data["response_text"] = confirmation_text
        data["reply_markup"] = get_profile_menu_keyboard(
            data["user_status"]
        )  # Меняем клавиатуру после выбора

        # Редактируем сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )
    except Exception as e:
        # Логируем ошибку и уведомляем пользователя
        logger.error(
            f"Ошибка при обновлении уровня информирования для пользователя {member_id}: {e}"
        )
        await callback.message.edit_text(  # type: ignore
            text="Произошла ошибка при сохранении уровня информирования. Попробуйте позже.",
            reply_markup=None,
        )

    # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.answer()
    # Завершаем машину состояний
    await state.clear()


@router.message(StateFilter(FSM_profile.fill_info_level))
@log_handler_call
async def warning_level_selection(message: Message):
    """
    Обработчик ввода текста когда ожидается нажатие кнопки
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.warning(
        f"Некорректный ввод от пользователя {message.from_user.id} в состоянии {FSM_profile.fill_info_level}"
    )
    await message.answer(
        text="Пожалуйста, воспользуйтесь кнопками выше!\n\n"
        "Если вы хотите прервать процедуру - "
        "нажмите кнопку под этим сообщением или отправьте команду /cancel",
        reply_markup=return_to_main_menu_markup,
    )
