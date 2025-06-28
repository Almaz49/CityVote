# token_handlers.py
# Хэндлеры для управления токенами

import logging
import os
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from filters.filters import StatusFilter
from FSMs.FSMs import FSMTokenManagement
from data_base.db_token_service import (
    create_tokens_for_lot,
    create_tokens_without_lot,
    export_tokens_to_excel,
    mark_token_as_old,
)
from keyboards.keyboards import (
    create_inline_kb,
    main_menu_markup,
)
from services.services import send_file_to_user
from utils import log_handler_call

# Настройка логирования
logger = logging.getLogger(__name__)


# Инициализируем роутер уровня модуля
router = Router()

# Навешиваем на роутер фильтр, проверяющий, является ли пользователь админом или суперрегистратор
router.message.filter(StatusFilter(required_status=["admin","superregistrator","owner"]))

# Добавляем фильтр на уровень роутера для CallbackQuery
router.callback_query.filter(StatusFilter(required_status=["admin","superregistrator","owner"]))



"""
МАРШРУТЫ
"""


# Хэндлер на вход в меню токенов
@router.callback_query(F.data == "tokens")
@log_handler_call
async def tokens_menu(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id} открыл меню управления токенами.")

    menu_buttons = {
        "create_lot": "Выдать токены из лота",
        "issue_token": "Выдать токены без лота",
        "issue_1_token": "Выдать один токен",
        "export_tokens": "Экспортировать токены",
        "mark_expired": "Пометить токен как устаревший",
        "main_menu": "Назад в главное меню",
    }

    markup = create_inline_kb(width=1, **menu_buttons)
    await callback.message.edit_text("Выберите действие:", reply_markup=markup)  # type: ignore
    await state.clear()


# --- СОЗДАНИЕ ЛОТА ТОКЕНОВ ---

@router.callback_query(F.data == "create_lot")
@log_handler_call
async def handle_create_lot(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id} выбрал создание лота.")
    if not callback.message:
        raise ValueError("CallbackQuery.message is None")
    # Клавиатура с кнопкой "Пропустить"
    markup = create_inline_kb(width=1, skip_lot="Пропустить (автоматический номер)")

    await callback.message.answer(
        "Введите номер существующего лота или нажмите кнопку ниже, если лот новый:",
        reply_markup=markup
    )
    await state.set_state(FSMTokenManagement.fill_lot_number)

@router.callback_query(StateFilter(FSMTokenManagement.fill_lot_number), F.data == "skip_lot")
@log_handler_call
async def process_skip_lot(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id} пропустил ввод номера лота.")
    if not callback.message:
        raise ValueError("Нет сообщения для ответа")

    # Устанавливаем lot_number = None → автоматический выбор
    await state.update_data(lot_number=None)
    await callback.message.answer("Сколько токенов создать?")
    await state.set_state(FSMTokenManagement.fill_token_count)

@router.message(StateFilter(FSMTokenManagement.fill_lot_number))
@log_handler_call
async def process_lot_number(message: Message, state: FSMContext):
    lot_number = message.text.strip() if message.text else None

    if lot_number and not lot_number.isdigit():
        await message.answer("Номер лота должен быть числом. Попробуйте ещё раз:")
        return

    await state.update_data(lot_number=int(lot_number) if lot_number else None)
    await message.answer("Сколько токенов создать?")
    await state.set_state(FSMTokenManagement.fill_token_count)



@router.message(StateFilter(FSMTokenManagement.fill_token_count))
@log_handler_call
async def process_token_count(message: Message, state: FSMContext, data: dict):
    if not message.from_user:
        raise ValueError("Отправтель сообщения отсутствует (from_user == None)")
    count = message.text.strip() if message.text else "100"
    if not count.isdigit():
        await message.answer("Введите корректное число.")
        return

    await state.update_data(count=int(count))
    await message.answer("Введите комментарий для этих токенов:")
    await state.set_state(FSMTokenManagement.fill_token_comment)

@router.message(StateFilter(FSMTokenManagement.fill_token_comment))
@log_handler_call
async def process_token_comment(message: Message, state: FSMContext, data: dict):
    if not message.text:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return
    if not message.from_user:
        raise ValueError("Отправтель сообщения отсутствует (from_user == None)")
    comment = message.text.strip()
    if not comment:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return

    fsm_data = await state.get_data()
    count = fsm_data["count"]
    lot_number = fsm_data.get("lot_number")  # Может быть None

    if data.get('club_id'):
        club_id = data['club_id']
    else:
        raise ValueError("Не указан ID клуба")

    if data.get('member_id'):
        creator_id = data['member_id']
    else:
        creator_id = message.from_user.id



    try:
        result = await create_tokens_for_lot(
            club_id=club_id,
            lot=lot_number,
            count=count,
            token_length=9,
            validity_days=30,
            creator_id=creator_id,
            comment=comment  # ← Передаем комментарий
        )
        tokens_list = '\n'.join(result['tokens'])
        await message.answer(f"Создан токены лота №{result['lot']}:\n\n{tokens_list}")
    except Exception as e:
        logger.error(f"Ошибка при создании лота: {e}")
        await message.answer("Не удалось создать лот токенов.")

    await state.clear()
    await message.answer("Возврат в главное меню:", reply_markup=main_menu_markup)

    # fsm_data = await state.get_data()
    # if data.get('club_id'):
    #     club_id = data['club_id']
    # else:
    #     raise ValueError("Не указан ID клуба")


    # lot_number = fsm_data["lot_number"]

    # try:
    #     result = await create_tokens_for_lot(
    #         club_id=club_id,
    #         lot=lot_number,
    #         count=int(count),
    #         token_length=9,
    #         validity_days=30,
    #         creator_id=message.from_user.id
    #     )
    #     tokens_list = '\n'.join(result['tokens'])
    #     await message.answer(f"Создан лот №{result['lot']}:\n\n{tokens_list}")
    # except Exception as e:
    #     logger.error(f"Ошибка при создании лота: {e}")
    #     await message.answer("Не удалось создать лот токенов.")

    # await state.clear()
    # await message.answer("Возврат в главное меню:", reply_markup=main_menu_markup)


# --- ВЫДАЧА ТОКЕНОВ ---

@router.callback_query(F.data == "issue_token")
@log_handler_call
async def handle_issue_token(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id} запросил выдачу токенов без лота.")
    await callback.message.answer("Сколько токенов выдать?")  # type: ignore
    await state.set_state(FSMTokenManagement.fill_token_count)


@router.message(StateFilter(FSMTokenManagement.fill_token_count))
@log_handler_call
async def process_issue_token_count(message: Message, state: FSMContext, data: dict):
    count = message.text.strip() if message.text else "1"
    if not count.isdigit():
        await message.answer("Введите корректное число.")
        return

    await state.update_data(count=int(count))
    await message.answer("Введите комментарий для этих токенов:")
    await state.set_state(FSMTokenManagement.fill_token_comment)

@router.message(StateFilter(FSMTokenManagement.fill_token_comment))
@log_handler_call
async def process_issue_token_comment(message: Message, state: FSMContext, data: dict):
    if not message.text:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return
    if not message.from_user:
        raise ValueError("Отправтель сообщения отсутствует (from_user == None)")

    comment = message.text.strip()
    if not comment:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return

    fsm_data = await state.get_data()
    count = fsm_data["count"]

    club_id = data.get('club_id')
    if not club_id:
        raise ValueError("Не удалось получить ID клуба")

    try:
        tokens = await create_tokens_without_lot(
            club_id=club_id,
            count=count,
            comment=comment,
            creator_id=message.from_user.id)

        tokens_list = "\n".join(tokens)
        await message.answer(f"Выданы токены:\n\n<code>{tokens_list}</code>")
    except Exception as e:
        logger.error(f"Ошибка при выдаче токенов: {e}")
        await message.answer("Не удалось выдать токены.")

    await state.clear()
    await message.answer("Меню управления токенами:", reply_markup=main_menu_markup)


# --- ВЫДАЧА ОДНОГО ТОКЕНА ---

@router.callback_query(F.data == "issue_1_token")
@log_handler_call
async def handle_issue_1_token(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id} запросил выдачу одного токена.")
    if not callback.message:
        raise ValueError("Нет сообщения для ответа ")
    await callback.message.answer("Введите комментарий для этих токенов:")
    await state.set_state(FSMTokenManagement.fill_1_token_comment)

@router.message(StateFilter(FSMTokenManagement.fill_1_token_comment))
@log_handler_call
async def process_issue_1_token_comment(message: Message, state: FSMContext, data: dict):
    if not message.text:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return
    if not message.from_user:
        raise ValueError("Отправтель сообщения отсутствует (from_user == None)")
    comment = message.text.strip()
    if not comment:
        await message.answer("Комментарий не может быть пустым. Попробуйте ещё раз:")
        return

    club_id = data.get('club_id')
    if not club_id:
        raise ValueError("Не удалось получить ID клуба")

    try:
        tokens = await create_tokens_without_lot(
            club_id=club_id,
            count=1,
            comment=comment,
            creator_id=message.from_user.id
            )

        tokens_list = "\n".join(tokens)
        await message.answer(f"Выдан токен:\n\n<code>{tokens_list}</code>")
    except Exception as e:
        logger.error(f"Ошибка при выдаче токенов: {e}")
        await message.answer("Не удалось выдать токены.")

    await state.clear()
    await message.answer("Меню управления токенами:", reply_markup=main_menu_markup)


# --- ЭКСПОРТ ТОКЕНОВ В EXCEL ---

@router.callback_query(F.data == "export_tokens")
@log_handler_call
async def handle_export_tokens(callback: CallbackQuery, data: dict):
    logger.info(f"Пользователь {callback.from_user.id} экспортирует токены.")
    club_id = data.get('club_id')
    if not club_id:
        raise ValueError("Не удалось получить club_id из данных запроса.")

    try:
        file_path = await export_tokens_to_excel(club_id=club_id)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл {file_path} не был создан.")

        # Отправляем файл через нашу функцию
        await send_file_to_user(
            tg_id=callback.from_user.id,
            file_path=file_path,
            caption="Экспорт токенов",
            reply_markup=main_menu_markup
        )

        # Удаляем файл после отправки
        os.remove(file_path)
        logger.info(f"Файл {file_path} удален после отправки.")

    except Exception as e:
        logger.error(f"Ошибка при экспорте токенов: {e}")
        await callback.message.answer("Не удалось экспортировать токены.")  # type: ignore

    await callback.message.answer("Меню управления токенами:", reply_markup=main_menu_markup)  # type: ignore


# --- ПОМЕТКА ТОКЕНА КАК УСТАРЕВШИЙ ---

@router.callback_query(F.data == "mark_expired")
@log_handler_call
async def handle_mark_expired(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Пользователь {callback.from_user.id} хочет пометить токен как устаревший.")
    await callback.message.answer("Введите токен для пометки как устаревший:")  # type: ignore
    await state.set_state(FSMTokenManagement.fill_token_value)


@router.message(StateFilter(FSMTokenManagement.fill_token_value))
@log_handler_call
async def process_token_value(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Введите корректный токен.")
        return
    token = message.text.replace('-', '')  # убираем разделители
    if not token.isdigit():
        await message.answer("Введите корректный токен.")
        return

    try:
        success = await mark_token_as_old(token=token)
        if success:
            await message.answer("Токен успешно помечен как устаревший.")
        else:
            await message.answer("Токен не найден или уже устарел.")
    except Exception as e:
        logger.error(f"Ошибка при пометке токена как устаревшего: {e}")
        await message.answer("Не удалось обновить статус токена.")

    await state.clear()
    await message.answer("Меню управления токенами:", reply_markup=main_menu_markup)