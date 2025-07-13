# Модуль registrator_handlers
# Содержит хэндлеры регистраторов (тех, кто подтверждает членство
# в группе новых участников)
import logging
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from config_data.config import Config, load_config
from data_base.db_func import (
    extract_user_member_id
)
from data_base.telegram_bot_logic import (new_status,
                                          update_member_data)
from filters.filters import StatusFilter
from keyboards.keyboards import user_menu
from services.services import send_notification_to_user
from utils import log_handler_call
from FSMs.FSMs import FSMRegistration
from data_base.db_token_service import mark_token_as_used, create_tokens_without_lot

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config(".env")

# Инициализируем роутер уровня модуля
router = Router()

# Навешиваем фильтр, проверяющий, является ли пользователь Регистратором
router.message.filter(StatusFilter(required_status=["registrator", "superregistrator"]))

router.callback_query.filter(
    StatusFilter(required_status=["registrator", "superregistrator"])
)

"""
ХЭНДЛЕРЫ
"""


"""
Подтверждение или отклонение членства участника регистратором после заполнения анкеты
"""


# Этот хэндлер срабатывает при нажатии регистратором кнопки "Подтверждаю"
@router.callback_query(F.data.startswith("yes_registration:"))
@log_handler_call
async def process_registrator_yes_press(
    callback: CallbackQuery, data: dict, state: FSMContext
):
    """
    Обработчик подтверждения членства нового участника.
    Запрашивает комментарий, создаёт токен, обновляет статус пользователя.
    """
    if not callback.message:
        raise ValueError("Callback message is None")

    if not isinstance(callback.message, Message):
        logger.warning("Получено InaccessibleMessage, нельзя удалить клавиатуру")
        await callback.answer("Сообщение недоступно")
        return

    try:
        # Извлекаем Telegram ID пользователя из callback_data
        if not callback.data:
            logger.warning("Данные callback пусты")
            await callback.message.edit_text("Произошла ошибка: данные не найдены.")
            raise ValueError("Callback data отсутствует")

        tg_id = int(callback.data.split(":")[1])
        logger.info(
            f"Регистратор {callback.from_user.id} подтверждает членство пользователя {tg_id}."
        )

        # Сохраняем tg_id в FSMContext для следующего шага
        await state.update_data(tg_id=tg_id)

        # Переходим к вводу комментария
        await callback.message.answer("Введите комментарий для токена:")
        await state.set_state(FSMRegistration.fill_comment)

    except Exception as e:
        logger.error(f"Ошибка при подтверждении членства пользователя {tg_id}: {e}")
        await callback.message.answer(
            text="Произошла ошибка при подтверждении членства."
        )

# Хэндлер для ввода комментария и выдачи токена
@router.message(StateFilter(FSMRegistration.fill_comment))
@log_handler_call
async def process_token_comment(message: Message, state: FSMContext, data: dict):
    if not message.text:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return
    if not message.from_user:
        await message.answer("Не удалось получить ID пользователя. Пожалуйста, попробуйте ещё раз.")
        return
    comment = message.text.strip()
    if not comment:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return

    # Получаем данные из FSM
    fsm_data = await state.get_data()
    tg_id = fsm_data.get("tg_id")
    club_id = data.get("club_id")

    if not tg_id or not club_id:
        logger.error("Не удалось получить tg_id или club_id")
        await message.answer("Внутренняя ошибка. Попробуйте позже.")
        await state.clear()
        return

    try:
        # Генерируем токен с комментарием
        token = await create_tokens_without_lot(
            club_id=club_id,
            comment=comment,
            count=1,
            creator_id=message.from_user.id,
        )


        if isinstance(token, list):
            token = token[0]

        # Получаем user_id и member_id
        user_id, member_id = await extract_user_member_id(club_id, tg_id)
        if not member_id:
            await message.answer(f"Пользователь с ID {tg_id} не найден.")
            return

        # Привязываем токен к пользователю
        await update_member_data(member_id=member_id, token=token)

        # Помечаем токен как использованный
        await mark_token_as_used(token, message.from_user.id)

        # Обновляем статус на 'member'
        await new_status(
            registrator=data["member_id"], member_id=member_id, status="member"
        )

        # Уведомляем регистратора
        await message.answer(
            text=f"Спасибо! Пользователь {tg_id} получил статус 'Участник'.",
            reply_markup=await user_menu(message.from_user.id, data["user_status"]),
        )

        # Отправляем уведомление пользователю
        await send_notification_to_user(
            tg_id,
            message_text=(
                "Поздравляем! Ваша заявка на вступление в группу одобрена. Теперь вы полноправный участник группы и можете принимать участие в голосованиях.\n\n"
                "Обратите внимание - чтобы ваш голос учитывался, вам нужно либо выбрать себе представителя, либо сами стать представителем.\n"
                "Выбор представителя не ограничивает вашу возможность голосовать самому в любом голосовании.\n"
                "Но если вы не приняли участие в голосовании, будет учитываться то, как за вас проголосовал ваш представитель.\n"
                "Если вас не будет устраивать то, как за вас голосует ваш представитель, вы в любой момент сможете его поменять, либо сами стать представителем.\n"
                "Статус представителя накладывает обязательства, например — участие во всех голосованиях.\n"
                "Представитель может выбрать себе заместителя, который будет голосовать за него в случае отсутствия.\n"
                "Представитель несёт ответственность за голосование своего заместителя, как за своё собственное."
            ),
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при выдаче токена или обновлении статуса для {tg_id}: {e}")
        await message.answer("Не удалось завершить регистрацию.")
        await state.clear()

# Этот хэндлер срабатывает при нажатии регистратором кнопки "Не подтверждаю"
@router.callback_query(F.data.startswith("no_registration:"))
@log_handler_call
async def process_registrator_no_press(callback: CallbackQuery, data):
    """
    Обработчик отказа от подтверждения членства нового участника.
    Изменяет поле "familiar" пользователя в базе данных.
    """
    # Проверяем, что callback.data существует
    if not callback.data:
        logger.warning("Данные callback пусты")
        await callback.message.edit_text("Произошла ошибка: данные не найдены.")  # type: ignore
        raise ValueError("Callback data отсутствует")
    try:
        # Извлекаем Telegram ID пользователя из callback_data
        tg_id = int(callback.data.split(":")[1])
        logger.info(
            f"Регистратор {callback.from_user.id} отклоняет членство пользователя {tg_id}."
        )

        club_id = data.get("club_id")
        if not club_id:  # type: ignore
            raise ValueError("Нет club_id")


        # Получаем member_id пользователя
        user_id, member_id = await extract_user_member_id(club_id, tg_id)
        if not member_id:
            await callback.message.answer(text=f"Пользователь с ID {tg_id} не найден.")  # type: ignore
            return
        if not callback.message:
            raise ValueError("Callback message is None")

        if not isinstance(callback.message, Message):
            logger.warning("Получено InaccessibleMessage, нельзя удалить клавиатуру")
            await callback.answer("Получено InaccessibleMessage")
            raise ValueError("Callback message is None")

        # Обновляем поле "familiar" пользователя в базе данных
        await update_member_data(member_id=member_id, familiar="stranger")
        await callback.message.delete_reply_markup()  # Удаляем кнопки

        # Отправляем уведомление об отказе
        await callback.message.answer(
            text=f"Спасибо! Пользователь {tg_id} не получил статус 'Участник'.",
            reply_markup=await user_menu(callback.from_user.id, data["user_status"]),
        )
    except Exception as e:
        logger.error(f"Ошибка при отклонении членства пользователя {tg_id}: {e}")
        await callback.message.answer(  # type: ignore
            text="Произошла ошибка при отклонении членства.",
            reply_markup=await user_menu(callback.from_user.id, data["user_status"]),
        )
