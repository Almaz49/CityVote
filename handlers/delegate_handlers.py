# Модуль delegate_handlers
# В нем хэндлеры пользователей, обладающих правами делегатов
import logging

from aiogram import F, Bot, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from LEXICON import get_text
from data_base.db_vote import variant_create
from filters.filters import StatusFilter
from FSMs.FSMs import FSMNewVariant, FSMNewVoting
from keyboards.keyboards import confirm_markup, user_menu, variant_markup
from manager.manager import voting_create_manager
from utils import check_fsm_data, log_handler_call, safe_edit

# Настройка логирования
logger = logging.getLogger(__name__)


# Инициализируем роутер уровня модуля
router = Router()

# Навешиваем на роутер фильтр, проверяющий, является ли пользователь Делегатом
router.message.filter(StatusFilter(required_status=["delegate"]))

# Добавляем фильтр на уровень роутера для CallbackQuery
router.callback_query.filter(StatusFilter(required_status=["delegate"]))

"""
СОЗДАНИЕ ГОЛОСОВАНИЯ
"""


# Этот хэндлер будет срабатывать на команду /new_voting
# и переводить бота в состояние ожидания ввода названия голосования
@router.message(Command(commands="new_voting"), StateFilter(default_state))
@log_handler_call
async def process_new_voting_start_command(message: Message, state: FSMContext, data: dict):
    """
    Обработчик команды /new_voting.
    Запускает процесс создания нового голосования.
    """
    logger.info(f"Пользователь {message.from_user.id} начал создание голосования.")  # type: ignore
#     await message.answer(text="Пожалуйста, введите название голосования.")
    await message.answer(text=get_text("delegate.please_enter_title_voting", lang=data.get("lang","ru")))

    await state.set_state(FSMNewVoting.fill_voting_title)


# Этот хэндлер будет срабатывать на нажатие кнопки "создать голосование"
# и переводить бота в состояние ожидания ввода названия голосования
@router.callback_query(StateFilter(default_state), F.data == "new_voting")
@log_handler_call
async def process_new_voting_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки new_voting.
    Запускает процесс создания нового голосования.
    """
    logger.info(f"Пользователь {callback.from_user.id} начал создание голосования.")
#     await callback.message.answer(text="Пожалуйста, введите название голосования.")  # type: ignore
    await callback.message.answer(text=get_text("delegate.please_enter_title_voting_1", lang=data.get("lang","ru")))  # type: ignore

    await state.set_state(FSMNewVoting.fill_voting_title)


# Этот хэндлер будет срабатывать на ввод названия
# и переводить бота в состояние ожидания ввода описания голосования
@router.message(StateFilter(FSMNewVoting.fill_voting_title))
@log_handler_call
async def process_new_voting_title_sent(message: Message, state: FSMContext, data: dict):
    """
    Обработчик ввода названия голосования.
    Сохраняет название и запрашивает описание.
    """
    if not message.text:
        logger.warning("Отсутствует текст сообщения")
        return
    logger.info(f"Пользователь {message.from_user.id} ввел название голосования: {message.text}.")  # type: ignore
    if len(message.text) > 40:
        await message.answer(
#             "Название не должно быть длиннее 40 символов. Попробуйте снова."
            get_text("delegate.title_not_must_be_longer_40_characters_try_again", lang=data.get("lang","ru"))

        )
        return
    await state.update_data(title=message.text)
#     await message.answer(text="Пожалуйста, введите описание голосования.")
    await message.answer(text=get_text("delegate.please_enter_description_voting", lang=data.get("lang","ru")))

    await state.set_state(FSMNewVoting.fill_voting_description)


# Этот хэндлер будет срабатывать после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVoting.fill_voting_description))
@log_handler_call
@check_fsm_data
async def process_new_voting_description_sent(message: Message, state: FSMContext, data: dict):
    """
    Обработчик ввода описания голосования.
    Запрашивает подтверждение данных.
    """
    logger.info(f"Пользователь {message.from_user.id} ввел описание голосования: {message.text}.")  # type: ignore
    await state.update_data(description=message.text)
    fsm_data = await state.get_data()
    title = fsm_data["title"]
    description = fsm_data["description"]

    # Отправляем сообщение с подтверждением
    await message.answer(
#         text=f"""Пожалуйста, подтвердите, правильно ли введены название и описание голосования?
# Название: {title}
# Описание: {description}""",
        text=get_text("delegate.please_confirm_correct_is_entered_title_and_description_voti", lang=data.get("lang","ru")).format(description=description, title=title),

        reply_markup=confirm_markup,
    )
    await state.set_state(FSMNewVoting.fill_OK)


# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK), F.data == "ConfirmOK")
@log_handler_call
@check_fsm_data
async def process_new_voting_yes_confirm_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик подтверждения создания голосования.
    Создает новое голосование в базе данных.
    """
    logger.info(
        f"Пользователь {callback.from_user.id} подтвердил создание голосования."
    )
    # fsm_data = await state.get_data()
    # if not fsm_data:
    #     await callback.message.answer("Сессия устарела. Пожалуйста, начните заново.")
    #     return
    if not callback.bot:
        raise ValueError("Не удалось получить бота")
    bot:Bot = callback.bot
    try:
        fsm_data = await state.get_data()
        logger.debug(f"Получена FSM data:{fsm_data}")
        title = fsm_data["title"]
        description = fsm_data["description"]

        # Создаем новое голосование
        flag, comment = await voting_create_manager(
            bot=bot,
            club_id=data["club_id"],
            creator=data["member_id"],
            title=title,
            text=description,
            voting_status="add_variants",
        )

        if flag:
            await state.clear()

            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (
#                 "Спасибо! Голосование создано! Вы вышли из машины состояний."
                get_text("delegate.thank_you_voting_created_you_exited_from_machines_consisting", lang=data.get("lang","ru"))

            )
            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Пытаемся отредактировать сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

        else:
            # Добавляем данные для SafeEditMiddleware
#             data["response_text"] = f"Ошибка: {comment}"
            data["response_text"] = get_text("delegate.error_value", lang=data.get("lang","ru")).format(comment=comment)

            data["reply_markup"] = None  # Если клавиатура не нужна

            # Пытаемся отредактировать сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

    except Exception as e:
        logger.error(f"Ошибка при создании голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
#         data["response_text"] = f"Произошла ошибка: {str(e)}"
        err = str(e)
        data["response_text"] = get_text("delegate.occurred_error_value", lang=data.get("lang","ru")).format(err = err)

        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_new_voting_no_confirm_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик отмены создания голосования.
    Завершает машину состояний.
    """
    logger.info(f"Пользователь {callback.from_user.id} отменил создание голосования.")
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
#         "Голосование не создано! Попробуйте еще раз. Вы вышли из машины состояний."
        get_text("delegate.voting_not_created_try_also_time_you_exited_from_machines_co", lang=data.get("lang","ru"))

    )
    data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )


"""
Добавление варианта
"""


# Этот хэндлер будет срабатывать на нажатие кнопки с добавлением варианта к конкретному голосованию
# и переводить в машину состояний добавления вариантов
@router.callback_query(
    F.data.regexp(r"^create_variant:\d+$"), StateFilter(default_state)
)
@log_handler_call
async def process_variant_title_sent(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик кнопки добавления варианта.
    Запрашивает ввод названия варианта.
    """
    # Проверяем, что callback.data существует
    if callback.data is None:
        logger.warning("Callback data отсутствует")
#         await callback.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")
        await callback.answer(get_text("delegate.occurred_error_please_try_again", lang=data.get("lang","ru")))

        return
    logger.info(
        f"Пользователь {callback.from_user.id} начал добавление варианта к голосованию ID={callback.data}."
    )
    voting_id = int(callback.data.split(":")[1])
    await state.update_data(voting_id=voting_id)

    # Добавляем данные для SafeEditMiddleware
#     data["response_text"] = "Пожалуйста, введите название варианта."
    data["response_text"] = get_text("delegate.please_enter_title_option", lang=data.get("lang","ru"))

    data["reply_markup"] = None  # Убираем клавиатуру

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем следующее состояние
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на ввод названия варианта
# и переводить бота в состояние ожидания ввода описания
@router.message(StateFilter(FSMNewVariant.fill_variant_title))
@log_handler_call
async def process_variant_description_sent(message: Message, state: FSMContext, data: dict):
    """
    Обработчик ввода названия варианта.
    Запрашивает ввод описания.
    """
    if not message.text:
        logger.warning("Отсутствует текст сообщения")
        return
    logger.info(f"Пользователь {message.from_user.id} ввел название варианта: {message.text}.")  # type: ignore
    if len(message.text) > 40:
        await message.answer(
#             "Название не должно быть длиннее 40 символов. Попробуйте снова."
            get_text("delegate.title_not_must_be_longer_40_characters_try_again_1", lang=data.get("lang","ru"))

        )
        return
    await state.update_data(title=message.text)
#     await message.answer(text="Пожалуйста, введите описание варианта.")
    await message.answer(text=get_text("delegate.please_enter_description_option", lang=data.get("lang","ru")))

    await state.set_state(FSMNewVariant.fill_variant_description)


# Этот хэндлер будет срабатывать после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVariant.fill_variant_description))
@log_handler_call
async def process_new_variant_description_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода описания варианта.
    Запрашивает подтверждение данных.
    """
    logger.info(f"Пользователь {message.from_user.id} ввел описание варианта: {message.text}.")  # type: ignore
    await state.update_data(description=message.text)
    data = await state.get_data()
    title = data["title"]
    description = data["description"]

    # Отправляем сообщение с подтверждением
    await message.answer(
#         text=f"""Пожалуйста, подтвердите, правильно ли введены название и описание варианта?
# Название: {title}
# Описание: {description}""",
        text=get_text("delegate.please_confirm_correct_is_entered_title_and_description_opti", lang=data.get("lang","ru")).format(description=description, title=title),

        reply_markup=confirm_markup,
    )
    await state.set_state(FSMNewVariant.fill_OK)


# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVariant.fill_OK), F.data == "ConfirmOK")
@log_handler_call
async def process_new_variant_yes_confirm_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик подтверждения добавления варианта.
    Создает новый вариант в базе данных.
    """
    logger.info(f"Пользователь {callback.from_user.id} подтвердил добавление варианта.")
    try:
        fsm_data = await state.get_data()
        voting_id = fsm_data["voting_id"]
        title = fsm_data["title"]
        description = fsm_data["description"]
        tg_id = callback.from_user.id
        member_id = data.get("member_id")
        if not member_id:
            raise ValueError("Нет member_id")

        # Создаем новый вариант
        flag, comment = await variant_create(
            voting_id=voting_id, author= member_id, title=title, text=description
        )

        if flag:
            # Добавляем данные для SafeEditMiddleware
            data["response_text"] = (
#                 "Спасибо! Вариант создан!\nХотите ли добавить ещё вариант?"
                get_text("delegate.thank_you_option_created_nkhotite_is_add_eshch_option", lang=data.get("lang","ru"))

            )
            data["reply_markup"] = variant_markup

            # Пытаемся отредактировать сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

            # Устанавливаем следующее состояние
            await state.set_state(FSMNewVariant.fill_more_variant)

        else:
            # Добавляем данные для SafeEditMiddleware
#             data["response_text"] = f"Ошибка: {comment}"
            data["response_text"] = get_text("delegate.error_value_1", lang=data.get("lang","ru")).format(comment=comment)

            data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

            # Пытаемся отредактировать сообщение
            await safe_edit(callback,   # type: ignore
                text=data["response_text"], reply_markup=data["reply_markup"]
            )

    except Exception as e:
        logger.error(f"Ошибка при добавлении варианта: {e}")

        # Добавляем данные для SafeEditMiddleware
#         data["response_text"] = f"Произошла ошибка: {str(e)}"
        err = str(e)
        data["response_text"] = get_text("delegate.occurred_error_value_1", lang=data.get("lang","ru")).format(err=err)

        data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

        # Пытаемся отредактировать сообщение
        await safe_edit(callback,   # type: ignore
            text=data["response_text"], reply_markup=data["reply_markup"]
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK), F.data == "ConfirmNotOK")
@log_handler_call
async def process_new_variant_no_confirm_press(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    # Добавляем данные для SafeEditMiddleware
#     data["response_text"] = "Вариант не создан! Хотите ли добавить другой вариант?"
    data["response_text"] = get_text("delegate.option_not_created_want_is_add_another_option", lang=data.get("lang","ru"))

    data["reply_markup"] = variant_markup

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем следующее состояние
    await state.set_state(FSMNewVariant.fill_more_variant)


# Этот хэндлер будет срабатывать на нажатие кнопки "Добавить ещё вариант"
@router.callback_query(
    StateFilter(FSMNewVariant.fill_more_variant), F.data == "NewVariant"
)
@log_handler_call
async def process_more_variant(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик добавления ещё одного варианта.
    Возвращает пользователя к вводу названия варианта.
    """
    logger.info(
        f"Пользователь {callback.from_user.id} решил добавить ещё один вариант."
    )

    # Добавляем данные для SafeEditMiddleware
#     data["response_text"] = "Пожалуйста, введите название варианта."
    data["response_text"] = get_text("delegate.please_enter_title_option_1", lang=data.get("lang","ru"))

    data["reply_markup"] = None  # Если клавиатура не нужна

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )

    # Устанавливаем следующее состояние
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на нажатие кнопки "Завершить добавление вариантов"
@router.callback_query(
    StateFilter(FSMNewVariant.fill_more_variant), F.data == "Finish_Variant"
)
@log_handler_call
async def process_finish_variant(
    callback: CallbackQuery, state: FSMContext, data: dict
):
    """
    Обработчик завершения добавления вариантов.
    Завершает машину состояний.
    """
    logger.info(f"Пользователь {callback.from_user.id} завершил добавление вариантов.")
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data["response_text"] = (
#         "Спасибо! Все варианты добавлены! Вы вышли из машины состояний."
        get_text("delegate.thank_you_all_options_added_you_exited_from_machines_consist", lang=data.get("lang","ru"))

    )
    data["reply_markup"] = await user_menu(status = data.get("user_status", ["user"]))

    # Пытаемся отредактировать сообщение
    await safe_edit(callback,   # type: ignore
        text=data["response_text"], reply_markup=data["reply_markup"]
    )
