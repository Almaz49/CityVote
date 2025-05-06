# Модуль delegate_handlers
# В нем хэндлеры пользователей, обладающих правами делегатов
from aiogram import Bot, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from filters.filters import StatusFilter
from FSMs.FSMs import FSMNewVoting, FSMNewVariant
from keyboards.keyboards import confirm_markup, variant_markup, create_inline_kb, user_menu
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import *
import logging
from utils import log_handler_call, check_fsm_data
from manager.manager import voting_create_manager

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()

# Навешиваем на роутер фильтр, проверяющий, является ли пользователь Делегатом
router.message.filter(StatusFilter(required_status = ['delegate']))

# Добавляем фильтр на уровень роутера для CallbackQuery
router.callback_query.filter(StatusFilter(required_status=['delegate']))

"""
СОЗДАНИЕ ГОЛОСОВАНИЯ
"""

# Этот хэндлер будет срабатывать на команду /new_voting
# и переводить бота в состояние ожидания ввода названия голосования
@router.message(Command(commands='new_voting'), StateFilter(default_state))
@log_handler_call
async def process_new_voting_start(message: Message, state: FSMContext):
    """
    Обработчик команды /new_voting.
    Запускает процесс создания нового голосования.
    """
    logger.info(f"Пользователь {message.from_user.id} начал создание голосования.")
    await message.answer(text='Пожалуйста, введите название голосования.')
    await state.set_state(FSMNewVoting.fill_voting_title)

# Этот хэндлер будет срабатывать на нажатие кнопки "создать голосование"
# и переводить бота в состояние ожидания ввода названия голосования
@router.callback_query(StateFilter(default_state), F.data == 'new_voting')
@log_handler_call
async def process_new_voting_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки new_voting.
    Запускает процесс создания нового голосования.
    """
    logger.info(f"Пользователь {callback.from_user.id} начал создание голосования.")
    await callback.message.answer(text='Пожалуйста, введите название голосования.')
    await state.set_state(FSMNewVoting.fill_voting_title)


# Этот хэндлер будет срабатывать на ввод названия
# и переводить бота в состояние ожидания ввода описания голосования
@router.message(StateFilter(FSMNewVoting.fill_voting_title))
@log_handler_call
async def process_new_voting_title_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода названия голосования.
    Сохраняет название и запрашивает описание.
    """
    logger.info(f"Пользователь {message.from_user.id} ввел название голосования: {message.text}.")
    if len(message.text) > 40:
        await message.answer("Название не должно быть длиннее 40 символов. Попробуйте снова.")
        return
    await state.update_data(title=message.text)
    await message.answer(text='Пожалуйста, введите описание голосования.')
    await state.set_state(FSMNewVoting.fill_voting_description)


# Этот хэндлер будет срабатывать после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVoting.fill_voting_description))
@log_handler_call
@check_fsm_data
async def process_new_voting_description_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода описания голосования.
    Запрашивает подтверждение данных.
    """
    logger.info(f"Пользователь {message.from_user.id} ввел описание голосования: {message.text}.")
    await state.update_data(description=message.text)
    fsm_data = await state.get_data()
    title = fsm_data['title']
    description = fsm_data['description']

    # Отправляем сообщение с подтверждением
    await message.answer(
        text=f'''Пожалуйста, подтвердите, правильно ли введены название и описание голосования?
Название: {title}
Описание: {description}''',
        reply_markup=confirm_markup
    )
    await state.set_state(FSMNewVoting.fill_OK)


# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
@check_fsm_data
async def process_new_voting_yes_confirm_press(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик подтверждения создания голосования.
    Создает новое голосование в базе данных.
    """
    logger.info(f"Пользователь {callback.from_user.id} подтвердил создание голосования.")
    # fsm_data = await state.get_data()
    # if not fsm_data:
    #     await callback.message.answer("Сессия устарела. Пожалуйста, начните заново.")
    #     return
    try:
        fsm_data = await state.get_data()
        logger.debug(f'Получена FSM data:{fsm_data}')
        title = fsm_data['title']
        description = fsm_data['description']
        tg_id = callback.from_user.id

        # Создаем новое голосование
        flag, comment = await voting_create_manager(club_id = data['club_id'], creator= data['member_id'],
                                         title=title, text=description, voting_status='add_variants')

        if flag:
            await state.clear()

            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Спасибо! Голосование создано! Вы вышли из машины состояний.'
            data['reply_markup'] = await user_menu(status=data['user_status'])

            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

        else:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = f'Ошибка: {comment}'
            data['reply_markup'] = None  # Если клавиатура не нужна

            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

    except Exception as e:
        logger.error(f"Ошибка при создании голосования: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f"Произошла ошибка: {str(e)}"
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_new_voting_no_confirm_press(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик отмены создания голосования.
    Завершает машину состояний.
    """
    logger.info(f"Пользователь {callback.from_user.id} отменил создание голосования.")
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Голосование не создано! Попробуйте еще раз. Вы вышли из машины состояний.'
    data['reply_markup'] = await user_menu(status = data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

"""
Добавление варианта
"""

# # Этот хэндлер будет срабатывать на команду /new_variant
# # и переводить бота в состояние ожидания выбора голосования
# @router.message(Command(commands='new_variant'), StateFilter(default_state))
# @log_handler_call
# async def process_new_variant_start(message: Message, state: FSMContext, data:dict):
#     """
#     Обработчик команды /new_variant.
#     Запрашивает выбор голосования для добавления варианта.
#     """
#     logger.info(f"Пользователь {message.from_user.id} начал добавление варианта.")
#     try:
#         list_of_votings = await list_of_votings_tg('add_variants')
#         if not list_of_votings:
#             await message.answer(text='Сейчас нет активных голосований, вы не можете добавить вариант.',
#                                  reply_markup=await user_menu(message.from_user.id))
#             return

#         # Создаем клавиатуру с активными голосованиями
#         keyboards = {str(item[0]): item[1] for item in list_of_votings}
#         markup = create_inline_kb(1, **keyboards)

#         await message.answer(text='Пожалуйста, выберите, к какому голосованию вы хотите добавить вариант:',
#                             reply_markup=markup)
#         await state.set_state(FSMNewVariant.fill_voting_choise)
#     except Exception as e:
#         logger.error(f"Ошибка при получении списка голосований: {e}")
#         await message.answer(
#             text=f"Произошла ошибка: {str(e)}",
#             reply_markup=await user_menu(message.from_user.id, data['user_status'])
#             )

# # Этот хэндлер будет срабатывать на нажатие кнопки new_variant
# # и переводить бота в состояние ожидания выбора голосования
# @router.callback_query(F.data =='new_variant', StateFilter(default_state))
# @log_handler_call
# async def process_new_variant_cb_start(callback: CallbackQuery, state: FSMContext, data:dict):
#     """
#     Обработчик кнопки new_variant.
#     Запрашивает выбор голосования для добавления варианта.
#     """
#     logger.info(f"Пользователь {callback.from_user.id} начал добавление варианта.")
#     try:
#         list_of_votings = await list_of_votings_tg('add_variants')
#         if not list_of_votings:
#             # Добавляем данные для SafeEditMiddleware
#             data['response_text'] = 'Сейчас нет голосованийв стадии добавления варианта, вы не можете добавить вариант.'
#             data['reply_markup'] = await user_menu(status = data['user_status'])  # Убираем клавиатуру

#             # Пытаемся отредактировать сообщение
#             await callback.message.edit_text(
#                 text=data['response_text'],
#                 reply_markup=data['reply_markup']
#             )

#             return

#         # Создаем клавиатуру с активными голосованиями
#         keyboards = {str(item[0]): item[1] for item in list_of_votings}

#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = 'Пожалуйста, выберите, к какому голосованию вы хотите добавить вариант:'
#         data['reply_markup'] = create_inline_kb(1, **keyboards)

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#         await state.set_state(FSMNewVariant.fill_voting_choise)

#     except Exception as e:
#         logger.error(f"Ошибка при получении списка голосований: {e}")
#         # Добавляем данные для SafeEditMiddleware
#         data['response_text'] = f"Произошла ошибка: {str(e)}"
#         data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

#         # Пытаемся отредактировать сообщение
#         await callback.message.edit_text(
#             text=data['response_text'],
#             reply_markup=data['reply_markup']
#         )

#         await state.clear()




# # Этот хэндлер будет срабатывать на нажатие кнопки с названием голосования в машине
# # состояний добавления вариантов
# @router.callback_query(StateFilter(FSMNewVariant.fill_voting_choise), F.data.isdigit())
# @log_handler_call
# async def process_variant_title_sent(callback: CallbackQuery, state: FSMContext, data: dict):
#     """
#     Обработчик выбора голосования.
#     Запрашивает ввод названия варианта.
#     """
#     logger.info(f"Пользователь {callback.from_user.id} выбрал голосование ID={callback.data}.")
#     voting_id = int(callback.data)
#     await state.update_data(voting_id=voting_id)

#     # Добавляем данные для SafeEditMiddleware
#     data['response_text'] = 'Пожалуйста, введите название варианта.'
#     data['reply_markup'] = None  # Убираем клавиатуру

#     # Пытаемся отредактировать сообщение
#     await callback.message.edit_text(
#         text=data['response_text'],
#         reply_markup=data['reply_markup']
#     )

#     # Устанавливаем следующее состояние
#     await state.set_state(FSMNewVariant.fill_variant_title)

# Этот хэндлер будет срабатывать на нажатие кнопки с добавлением варианта к конкретному голосованию
# и переводить в машину состояний добавления вариантов
@router.callback_query(F.data.regexp(r'^create_variant:\d+$'), StateFilter(default_state))
@log_handler_call
async def process_variant_title_sent(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик кнопки добавления варианта.
    Запрашивает ввод названия варианта.
    """
    logger.info(f"Пользователь {callback.from_user.id} начал добавление варианта к голосованию ID={callback.data}.")
    voting_id = int(callback.data.split(':')[1])
    await state.update_data(voting_id=voting_id)

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Пожалуйста, введите название варианта.'
    data['reply_markup'] = None  # Убираем клавиатуру

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Устанавливаем следующее состояние
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на ввод названия варианта
# и переводить бота в состояние ожидания ввода описания
@router.message(StateFilter(FSMNewVariant.fill_variant_title))
@log_handler_call
async def process_variant_description_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода названия варианта.
    Запрашивает ввод описания.
    """
    logger.info(f"Пользователь {message.from_user.id} ввел название варианта: {message.text}.")
    if len(message.text) > 40:
        await message.answer("Название не должно быть длиннее 40 символов. Попробуйте снова.")
        return
    await state.update_data(title=message.text)
    await message.answer(text='Пожалуйста, введите описание варианта.')
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
    logger.info(f"Пользователь {message.from_user.id} ввел описание варианта: {message.text}.")
    await state.update_data(description=message.text)
    data = await state.get_data()
    title = data['title']
    description = data['description']

    # Отправляем сообщение с подтверждением
    await message.answer(
        text=f'''Пожалуйста, подтвердите, правильно ли введены название и описание варианта?
Название: {title}
Описание: {description}''',
        reply_markup=confirm_markup
    )
    await state.set_state(FSMNewVariant.fill_OK)


# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVariant.fill_OK), F.data == 'ConfirmOK')
@log_handler_call
async def process_new_variant_yes_confirm_press(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик подтверждения добавления варианта.
    Создает новый вариант в базе данных.
    """
    logger.info(f"Пользователь {callback.from_user.id} подтвердил добавление варианта.")
    try:
        fsm_data = await state.get_data()
        voting_id = fsm_data['voting_id']
        title = fsm_data['title']
        description = fsm_data['description']
        tg_id = callback.from_user.id

        # Создаем новый вариант
        flag, comment = await new_variant_tg(voting_id=voting_id, creator_tg_id=tg_id, title=title, text=description)

        if flag:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = 'Спасибо! Вариант создан!\nХотите ли добавить ещё вариант?'
            data['reply_markup'] = variant_markup

            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

            # Устанавливаем следующее состояние
            await state.set_state(FSMNewVariant.fill_more_variant)

        else:
            # Добавляем данные для SafeEditMiddleware
            data['response_text'] = f'Ошибка: {comment}'
            data['reply_markup'] = await user_menu(status = data['user_status'])

            # Пытаемся отредактировать сообщение
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )

    except Exception as e:
        logger.error(f"Ошибка при добавлении варианта: {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = f"Произошла ошибка: {str(e)}"
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.clear()
        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK), F.data == 'ConfirmNotOK')
@log_handler_call
async def process_new_variant_no_confirm_press(callback: CallbackQuery, state: FSMContext, data: dict):
    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Вариант не создан! Хотите ли добавить другой вариант?'
    data['reply_markup'] = variant_markup

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Устанавливаем следующее состояние
    await state.set_state(FSMNewVariant.fill_more_variant)

# Этот хэндлер будет срабатывать на нажатие кнопки "Добавить ещё вариант"
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant), F.data == 'NewVariant')
@log_handler_call
async def process_more_variant(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик добавления ещё одного варианта.
    Возвращает пользователя к вводу названия варианта.
    """
    logger.info(f"Пользователь {callback.from_user.id} решил добавить ещё один вариант.")

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Пожалуйста, введите название варианта.'
    data['reply_markup'] = None  # Если клавиатура не нужна

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )

    # Устанавливаем следующее состояние
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на нажатие кнопки "Завершить добавление вариантов"
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant), F.data == 'Finish_Variant')
@log_handler_call
async def process_finish_variant(callback: CallbackQuery, state: FSMContext, data: dict):
    """
    Обработчик завершения добавления вариантов.
    Завершает машину состояний.
    """
    logger.info(f"Пользователь {callback.from_user.id} завершил добавление вариантов.")
    await state.clear()

    # Добавляем данные для SafeEditMiddleware
    data['response_text'] = 'Спасибо! Все варианты добавлены! Вы вышли из машины состояний.'
    data['reply_markup'] = await user_menu(status=data['user_status'])

    # Пытаемся отредактировать сообщение
    await callback.message.edit_text(
        text=data['response_text'],
        reply_markup=data['reply_markup']
    )
