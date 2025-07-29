# Модуль candidate_handlers
# В нем хэндлеры, которые работают для всех пользователей
# Даже для тех, у кого нет токена или он просрочен
import logging
import traceback

from aiogram import F, Bot, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (CallbackQuery,  Message, InlineKeyboardButton,
                           InlineKeyboardMarkup)
from FSMs.FSMs import FSM_leave_club, FSMEnterToken
from data_base.db_func import get_profile, list_of_proxy
from data_base.db_token_service import add_token_attempt, auto_approve_by_token, clear_old_attempts, get_token_attempts_count, is_valid_token
from keyboards.keyboards import (confirm_markup, get_info_menu_keyboard, get_info_menu_keyboard, get_profile_menu_keyboard,  user_menu, return_to_main_menu_markup)
from LEXICON.LEXICON import LEXICON
from manager.manager import leave_club
from services.services import club_info, greetings_message, help_message, notify_super_registrator_short, profile_message

from utils import log_handler_call
from utils.utils import paginate

# Настройка логирования
logger = logging.getLogger(__name__)

# # Загружаем конфиг в переменную config
# config: Config = load_config('.env')

# Инициализируем роутер уровня модуля
router = Router()


@router.message(Command(commands=["start"]))
@log_handler_call
async def process_start_command(message: Message, command: CommandObject, data: dict):
    """
    Обработчик команды /start.
    Отправляет приветственное сообщение и главное меню.
    Если команда /start вызвана с параметром (например, через URL), обрабатывает его.
    """
    try:
        # Проверям, существует ли message.from_user
        if not message.from_user:
            raise ValueError("Отправитель сообщения отсутствует (from_user == None)")
        # Извлекаем параметр из команды /start
        args = command.args  # Это то, что идет после ?start= в URL

        # Логика обработки параметра
        if args == "start":
            # Пользователь перешел по ссылке с параметром "start"
            text = (
                "🎉 Добро пожаловать! Вы перешли по специальной ссылке.\n"
                "Это бот для проведения голосований.\n"
                "Пожалуйста, пройдите регистрацию, чтобы пользоваться ботом.\n"
                "Тогда вы получите право голоса и возможность голосовать.\n"
                'Для более подробной информации, нажмите кнопку "Информация".'
            )
        else:
            # Обычный старт без параметра
            markup = await user_menu(status= data["user_status"])
            text = await greetings_message(club_id=data["club_id"])
            text = text or ""
            text = text + "\nВаш статус в группе:"
            for status in data["user_status"]:
                text += f"\n   - {LEXICON.get('user_status',{}).get(status, status)}"

        # Создаем клавиатуру
        markup = await user_menu(status= data["user_status"])

        # Отправляем сообщение
        await message.answer(text=text, reply_markup=markup, parse_mode="HTML")

        logger.info(
            f"Пользователь {message.from_user.id} начал работу с ботом. Параметр: {args}"
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        error_info = traceback.extract_tb(e.__traceback__)
        for frame in error_info:
            logger.error(
                f"Ошибка произошла в файле: {frame.filename}, строка: {frame.lineno}, "
                f"функция: {frame.name}, код: {frame.line}"
            )
        await message.answer(
            text="Произошла ошибка при загрузке главного меню.",
            reply_markup=await user_menu(status=data["user_status"]),
        )


# Хэндлер для команды /help
@router.message(Command(commands=["help"]))
@log_handler_call
async def process_help_command(message: Message, data: dict):
    """
    Обработчик команды /help.
    Отправляет справочную информацию о боте.
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")
    logger.info(f"Пользователь {message.from_user.id} запросил справку.")
    await message.answer(
        text=help_message(data["user_status"]),
        reply_markup=await user_menu(status= data["user_status"]),
        parse_mode="HTML",  # Указываем режим разметки
    )


# Хэндлер для нажатия на кнопку "помощь"
@router.callback_query(F.data == "help")
@log_handler_call
async def process_help_callback(callback: CallbackQuery, data: dict):
    """
    Обработчик нажатия на кнопку "помощь".
    Отправляет справочную информацию о боте.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил справку через кнопку.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = help_message(data["user_status"])
    data["reply_markup"] = await user_menu(status= data["user_status"])

    # Отправляем сообщение со справкой в ответ
    await callback.message.answer(  # type: ignore
        text=data["response_text"],
        reply_markup=data["reply_markup"],
        parse_mode="HTML",  # Указываем режим разметки
    )


# Хэндлер для команды /cancel в состоянии по умолчанию
@router.message(Command(commands="cancel"), StateFilter(default_state))
@log_handler_call
async def process_cancel_command(message: Message, data: dict):
    """
    Обработчик команды /cancel.
    Уведомляет пользователя, что команда работает только внутри машин состояний.
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")
    logger.info(
        f"Пользователь {message.from_user.id} попытался использовать /cancel вне машины состояний."
    )
    markup = await user_menu(status= data["user_status"])
    await message.answer(text="Вы вышли в главное меню.", reply_markup=markup)


# Хэндлер для команды /cancel в любом состоянии, кроме состояния по умолчанию
@router.message(Command(commands="cancel"), ~StateFilter(default_state))
@log_handler_call
async def process_cancel_command_state(message: Message, state: FSMContext, data: dict):
    """
    Обработчик команды /cancel.
    Завершает текущую машину состояний.
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")
    logger.info(f"Пользователь {message.from_user.id} вышел из машины состояний.")
    markup = await user_menu(status= data["user_status"])
    await message.answer(
        text="Вы вышли из машины состояний и вернулись в главное меню.",
        reply_markup=markup,
    )
    # Сбрасываем состояние и очищаем данные
    await state.clear()


# # Хэндлер для кнопки 'Главное меню' в основном состоянии
# @router.callback_query(F.data == "main_menu", StateFilter(default_state))
# @log_handler_call
# async def process_main_menu_button(callback: CallbackQuery, data: dict):
#     """
#     Обработчик кнопки "Главное меню".
#     """
#     logger.info(
#         f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}"
#     )
#     await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

#     markup = await user_menu(status= data["user_status"])

#     # Добавляем данные для SafeEditMiddleware
#     data["response_text"] = "Главное меню:"
#     data["reply_markup"] = markup

#     # Пытаемся отредактировать сообщение
#     await callback.message.edit_text(  # type: ignore
#         text=data["response_text"], reply_markup=data["reply_markup"]
#     )


# # Хэндлер для кнопки 'Главное меню' внутри машины состояний.
# @router.callback_query(F.data == "main_menu", ~StateFilter(default_state))
# @log_handler_call
# async def process_main_menu_button_state(
#     callback: CallbackQuery, state: FSMContext, data: dict
# ):
#     """
#     Обработчик кнопки "Главное меню".
#     """
#     logger.info(
#         f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}"
#     )
#     await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

#     markup = await user_menu(status= data["user_status"])

#     # Сбрасываем состояние и очищаем данные, полученные внутри состояний
#     await state.clear()

#     # Добавляем данные для SafeEditMiddleware
#     data["response_text"] = "Вы вышли из процесса.\nГлавное меню:"
#     data["reply_markup"] = markup

#     # Пытаемся отредактировать сообщение
#     await callback.message.edit_text(  # type: ignore
#         text=data["response_text"], reply_markup=data["reply_markup"]
    # )

@router.callback_query(F.data == "main_menu", StateFilter('*'))
async def return_to_main_menu(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Хэндлер для кнопки "Главное меню".
    Прерывает машину состояний и возвращает в главное меню.
    """
    await state.clear()
    if callback.message and isinstance(callback.message, Message):
        markup = await user_menu(status=data["user_status"])
        try:
            await callback.message.edit_text(
                "Вы возвращены в главное меню.",
                reply_markup=markup
            )
        except Exception:
            await callback.answer("Сообщение устарело. Открываю главное меню.", show_alert=True)
            await callback.message.answer(
                "Вы возвращены в главное меню.",
                reply_markup=markup
            )
    elif callback.message:
        await callback.answer("Не удалось отредактировать сообщение.", show_alert=True)
    else:
        await callback.answer("Ошибка: нет сообщения для редактирования.", show_alert=True)
    await callback.answer()


# Хэндлер для команды /club_info
@router.message(Command(commands=["club_info"]))
@log_handler_call
async def process_club_info_command(message: Message, data: dict):
    """
    Обработчик команды /club_info.
    Отправляет справочную информацию о группе.
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    logger.info(f"Пользователь {message.from_user.id} запросил справку о группе.")
    await message.answer(
        text=await club_info(data["club_id"]),
        reply_markup=await user_menu(status= data["user_status"]),
        parse_mode="HTML",  # Указываем режим разметки
    )


"""
Хэндлеры выхода из группы
"""
# Хэндлер для кнопки 'leave_the_group'
@router.callback_query(F.data == "leave_the_group", StateFilter(default_state))
@log_handler_call
async def process_leave_the_group(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    try:
        logger.info(
            f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}"
        )
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        text = "Вы действительно хотите выйти из группы?\nВсё верно?"
        markup = confirm_markup

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = text
        data["reply_markup"] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.set_state(FSM_leave_club.fill_OK)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'list_of_votes': {e}")
        error_info = traceback.extract_tb(e.__traceback__)
        for frame in error_info:
            logger.error(
                f"Ошибка произошла в файле: {frame.filename}, строка: {frame.lineno}, "
                f"функция: {frame.name}, код: {frame.line}"
            )
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при загрузке списка голосований."
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        raise  # Передаем исключение middleware для обработки


# Хэндлер для кнопки подтверждения выхода из группы
# Этот хендлер будет срабатывать на нажатие кнопки "всё верно" при подтверждении выхода


@router.callback_query(StateFilter(FSM_leave_club.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def process_leave_club_entry(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(
        f"Кнопка 'ВСЁ ВЕРНО' при подтверждении выхода из нажата пользователем {callback.from_user.id}"
    )
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"
    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot

    try:
        # Запускаем процедуру выхода из группы
        member_id = data["member_id"]
        status = data["user_status"]
        await leave_club(bot, member_id, status)
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Вы вышли из группы!"
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Редактируем сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        # Завершаем машину состояний
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при записи username: {e}")
        error_info = traceback.extract_tb(e.__traceback__)
        for frame in error_info:
            logger.error(
                f"Ошибка произошла в файле: {frame.filename}, строка: {frame.lineno}, "
                f"функция: {frame.name}, код: {frame.line}"
            )
        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = f"Произошла ошибка: {str(e)}"
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSM_leave_club.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_no_confirm_leave_club(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    logger.info(f"Кнопка 'НЕ ВЕРНО' нажата пользователем {callback.from_user.id}")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = "Вы остались в группе"
    data["reply_markup"] = await user_menu(status=data["user_status"])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Завершаем машину состояний
    await state.clear()


# Этот хэндлер будет срабатывать, если во время подтверждения
# Обработка некорректного ввода пользователя при попытке выйти из клуба
# Если при выходе из группы будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSM_leave_club.fill_OK))
@log_handler_call
async def warning_leave_club(message: Message):
    """
    Функция предупреждает пользователя о некорректном вводе во время состояния выхода из клуба.
    Она логирует предупреждение и предлагает пользователю использовать кнопки или отправить команду /cancel для отмены действия.

    Параметры:
    - message: Message - сообщение, отправленное пользователем

    Возвращает:
    None
    """
    # Проверям, существует ли message.from_user
    if not message.from_user:
        raise ValueError("Отправитель сообщения отсутствует (from_user == None)")

    # Логирование некорректного ввода пользователя
    logger.warning(
        f"Некорректный ввод от пользователя {message.from_user.id} в состоянии FSM_leave_club.fill_OK"
    )
    # Ответ пользователю с предложением использовать кнопки или отменить действие
    await message.answer(
        text="Пожалуйста, воспользуйтесь кнопками!\n\n"
        "Если вы хотите прервать изменение статуса - "
        "отправьте команду /cancel"
    )



# Хэндлер для кнопки 'club_info'
@router.callback_query(F.data == "club_info")
@log_handler_call
async def process_club_info(callback: CallbackQuery, data: dict):
    """
    Обработчик команды /club_info.
    Отправляет справочную информацию о группе.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил справку о группе.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = await club_info(data["club_id"])
    data["reply_markup"] = get_info_menu_keyboard(exc="club_info")

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"],
        reply_markup=data["reply_markup"],
        parse_mode="HTML",  # Указываем режим разметки
    )


# Хэндлер для кнопки 'info'
@router.callback_query(F.data == "info")
@log_handler_call
async def process_info(callback: CallbackQuery, data: dict):
    """
    Обработчик команды /info.
    Отправляет меню с кнопками информации.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил информацию.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = LEXICON.get("info_menu", "Выберите интересующую информацию")
    data["reply_markup"] = get_info_menu_keyboard()

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"],
        reply_markup=data["reply_markup"],
        parse_mode="HTML",  # Указываем режим разметки
    )


# Хэндлер для кнопки 'profile'
@router.callback_query(F.data == "profile")
@log_handler_call
async def process_profile(callback: CallbackQuery, data: dict):
    """
    Обработчик команды /profile.
    Отправляет меню с кнопками опций профиля.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил профиль.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = await profile_message(
        data["member_id"], data["user_status"]
    )
    data["reply_markup"] = get_profile_menu_keyboard(data["user_status"])
    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"],
        reply_markup=data["reply_markup"],
        parse_mode="HTML",  # Указываем режим разметки
    )


# Хэндлер для кнопки 'bot_info'
@router.callback_query(F.data == "bot_info")
@log_handler_call
async def process_bot_info(callback: CallbackQuery, data: dict):
    """
    Обработчик команды /bot_info.
    Отправляет справочную информацию о группе.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил справку о группе.")
    await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = LEXICON.get(
        "bot_info_text", "Здесь должна была быть информаия о боте"
    )
    data["reply_markup"] = get_info_menu_keyboard(exc="bot_info")

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=data["response_text"],
        reply_markup=data["reply_markup"],
        parse_mode="HTML",  # Указываем режим разметки
    )


@router.callback_query(F.data == "about")
@log_handler_call
async def process_aboute(callback: CallbackQuery, data: dict):
    """
    Обработчик команды /about.
    Отправляет теорию о боте.
    """
    logger.info(f"Пользователь {callback.from_user.id} запросил зачем нужен этот бот.")

    # Отвечаем на callback, чтобы избежать "крутки часов"
    await callback.answer()

    # Получаем текст из LEXICON
    response_text = LEXICON.get("about_text", "Здесь должна была быть теория о ньюдеме")

    # Создаем клавиатуру, исключая кнопку 'about'
    reply_markup = get_info_menu_keyboard(exc="about")

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(  # type: ignore
        text=response_text,
        reply_markup=reply_markup,
        parse_mode="HTML",  # Указываем режим разметки
    )

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
    await callback.answer()
    if not callback.message:
        raise ValueError("Нет сообщения для ответа")
    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot
    member_id = data["member_id"]
    club_id = data["club_id"]
    tg_id = callback.from_user.id
    status = data["user_status"]
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


# Хэндлер для кнопки 'list_of_proxy'
@router.callback_query(
    F.data.startswith("list_of_proxy")
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
            data["reply_markup"] = await user_menu(status= data["user_status"])

            # Редактируем сообщение
            await callback.message.edit_text(  # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Разделяем на страницы
        paginated_proxies, total_pages = paginate(proxies, page)

        # Создаем кнопки для представителей
        proxy_buttons = []
        message_text = f"Список представителей: \n (Псевдоним, число голосов)"
        for proxy in paginated_proxies:
            message_text += f"\n{proxy['username']} - {proxy['trusted_votes']}"
            # Кнопка для получения подробной информации
            details_button = InlineKeyboardButton(
                text=f"{proxy['username']}",
                callback_data=f"proxy_details:{proxy['member_id']}:{proxy['trusted_votes']}:{page}",
            )
            # Добавляем кнопки в список
            proxy_buttons.append([details_button])

        # Добавляем кнопки пагинации
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"list_of_proxy:{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Вперед", callback_data=f"list_of_proxy:{page + 1}"
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
            message_text + "\n\nДля подробной информации нажмите на одну из кнопок ниже:"
        )
        data["reply_markup"] = markup
        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'list_of_proxy': {e}")

        # Добавляем данные для SafeEditMiddleware
        data["response_text"] = "Произошла ошибка при загрузке списка представителей."
        data["reply_markup"] = await user_menu(status= data["user_status"])

        # Редактируем сообщение в случае ошибки
        await callback.message.edit_text(  # type: ignore
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
        proxy_id = int(callback.data.split(":")[1])
        trusted_votes = int(callback.data.split(":")[2])
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

        try:
            page = callback.data.split(":")[3]
            page = int(page) if page.isdigit() else 1
        except ValueError:
            page = 1

        proxies = await list_of_proxy(data["club_id"])

        if not proxies:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = "В данный момент нет доступных представителей."
            data["reply_markup"] = await user_menu(status= data["user_status"])

            # Редактируем сообщение
            await callback.message.edit_text(  # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )
            return

        # Разделяем на страницы
        paginated_proxies, total_pages = paginate(proxies, page)

        # Создаем кнопки для представителей
        proxy_buttons = []
        for proxy in paginated_proxies:
            # Кнопка для получения подробной информации
            details_button = InlineKeyboardButton(
                text=f"{proxy['username']}",
                callback_data=f"proxy_details:{proxy['member_id']}:{proxy['trusted_votes']}:{page}",
            )
            # Добавляем кнопки в список
            proxy_buttons.append([details_button])

        # Добавляем кнопки пагинации
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"list_of_proxy:{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Вперед", callback_data=f"list_of_proxy:{page + 1}"
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

        await callback.message.edit_text(  # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

    except Exception as e:
        logger.error(f"Ошибка при получении подробной информации о представителе: {e}")
        await callback.message.answer("Произошла ошибка при получении информации о представителе.")  # type: ignore