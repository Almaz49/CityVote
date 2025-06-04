# Модуль reg_process_handlers
# Содержит хэндлеры процесса регистрации

import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Contact
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from FSMs.FSMs import FSMRegistration, FSMRereg, FSM_short_registration
from data_base.telegram_bot_logic import (status_member, extract_user_data_tg, extract_club_info, new_status_tg, list_of_members_tg,
update_address, recording_user_data_1, update_user_data, update_member_data)
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, return_to_main_menu_markup
from filters.filters import ContactFilter
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from LEXICON.LEXICON import LEXICON
from services.services import notify_registrator, notify_registrator_short, notify_super_registrator_short

# Настройка логирования
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()

# -------------------------------------------
# Хэндлеры самой упрощенной регистрации участника
# Не запрашивается даже контакт.
# -------------------------------------------

# Хэндлер для кнопки 'registration'
@router.callback_query(F.data == 'registration')
@log_handler_call
async def process_registration(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        if 'member' in data['user_status']:
            await callback.message.answer(
                text='Вы уже зарегистрированы в группе',
                reply_markup=return_to_main_menu_markup
            )
            return

        tg_id = callback.from_user.id
        club_id = data['club_id']
        club_info = await extract_club_info(club_id)

        # Логируем club_info для отладки
        logger.debug(f"Club info: {club_info}")

        text0 = LEXICON.get('registration_message', 'Напишите о себе')
        text1 = LEXICON.get('reg_cancel_info')

        # Проверяем, что club_info содержит вопросы
        questions = club_info.get('questions_for_the_candidate')
        if questions is None:
            questions = text0  # Используем текст по умолчанию, если вопроса нет

        text = questions + '\n' + text1
        markup = None  # Не нужна клавиатура

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Проверяем, отличается ли новое сообщение от текущего
        current_text = callback.message.text
        current_markup = callback.message.reply_markup
        if current_text != data['response_text'] or current_markup != data['reply_markup']:
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup'],
                parse_mode='HTML'
            )
        else:
            logger.info("Сообщение не изменено, так как содержимое совпадает.")

        # Устанавливаем состояние
        await state.set_state(FSM_short_registration.fill_resume)

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки 'registration': {e}")
        logger.error(f"Текущие данные: {data}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при начале процесса регистрации.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        try:
            await callback.message.edit_text(
                text=data['response_text'],
                reply_markup=data['reply_markup']
            )
        except Exception as edit_error:
            logger.error(f"Ошибка при редактировании сообщения: {edit_error}")

        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать, если введено корректное резюме
@router.message(StateFilter(FSM_short_registration.fill_resume))
@log_handler_call
async def process_resume_sent(message: Message, state: FSMContext):
    logger.info(f"Введено резюме кандидата: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем введенное имя в контексте состояния
    await state.update_data(resume=message.text, tg_id = message.from_user.id,
                            tg_first_name = message.from_user.first_name, tg_last_name = message.from_user.last_name)

    # Создаем инлайн-кнопки для выбора регистратора
    registrators = await list_of_members_tg('registrator')
    buttons: list[list[InlineKeyboardButton]] = []
    for item in registrators:
        name = item[0] if item[0] else item[3] if item[3] else item[5]
        last_name = item[1] if item [1] else item[4] if item[4] else ''
        tg_id = item[2]
        buttons.append([InlineKeyboardButton(
            text=f'{name} {last_name}',
            callback_data=str(tg_id)
        )])

    buttons.append([InlineKeyboardButton(
        text='Никого из регистраторов не знаю',
        callback_data='stranger'
    )])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем пользователю клавиатуру для выбора регистратора
    await message.answer(
        text="Спасибо!\nВыберите регистратора, которого знаете,\nчтобы он смог подтвердить вашу личность\nЕсли никого не знаете,\nНажмите кнопку 'Никого не знаю'",
        reply_markup=markup  # клавиатура подтверждения
    )
    # Устанавливаем состояние ожидания выбора регистратора
    await state.set_state(FSM_short_registration.fill_registrator)


# Этот хэндлер будет срабатывать на выбор регистратора
@router.callback_query(StateFilter(FSM_short_registration
                                   .fill_registrator),
                      lambda x: x.data.isdigit() or x.data == 'stranger')
@log_handler_call
async def process_registrator_choise(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logger.info(f"Выбран регистратор {callback.data} пользователем {callback.from_user.id}")

        # Удаляем сообщение с кнопками подтверждения
        await callback.message.delete()

        # Сохраняем знакомого модератора (callback.data нажатой кнопки) в контексте состояния по ключу "familiar"
        await state.update_data(familiar=callback.data)
        tg_id = callback.from_user.id

        # Заносим данные регистрации в строку соответствующего пользователя в базе данных
        user_dict = await state.get_data()

        # Записываем в базу данных сведения об участнике
        user_param = {}
        user_param['tg_phone_number'] = user_dict.get('tg_phone_number')
        user_param['tg_first_name'] = user_dict.get('tg_first_name')
        user_param['tg_last_name'] = user_dict.get('tg_last_name')
        await update_user_data(tg_id, **user_param )

        member_id = data['member_id']
        member_param = {}
        member_param['resume'] = user_dict.get('resume')
        await update_member_data(member_id, **member_param)




        # Меняем статус пользователя на 'candidate'
        success, result = await new_status_tg(None, tg_id, 'candidate')  # меняем статус пользователя на 'candidate'
        if not success:
            await callback.message.answer(text=result)
            return

        # Завершаем машину состояний
        await state.clear()

        # Отправляем в чат сообщение о выходе из машины состояний
        await callback.message.answer(
            text='Спасибо! Ваши данные сохранены.\nАдминистрация их проверит и даст вам соответствующие права\nВы вышли из машины состояний',
            reply_markup= await user_menu(callback.from_user.id)
        )

        # Если выбран регистратор, отправляем ему сообщение с просьбой подтвердить регистрацию
        if callback.data.isdigit():
            success, result = await notify_registrator_short(int(callback.data), tg_id, user_dict)
            if not success:
                await callback.message.answer(text=f'Ошибка при уведомлении регистратора: {result}')
        elif callback.data == 'stranger':
            logger.info(f"Пользователь {tg_id} выбрал 'Никого не знаю'.")
            success, result = await notify_super_registrator_short(tg_id, user_dict)
            if not success:
                await callback.message.answer(text=f'Ошибка при уведомлении супер-регистратора: {result}')
            # Здесь тоже нужна функция уведомления администрации
    except Exception as e:
        logger.error(f"Ошибка при выборе регистратора: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')
        # Завершаем машину состояний
        await state.clear()

# Этот хэндлер будет срабатывать, если во время выбора регистратора
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSM_short_registration.fill_registrator))
@log_handler_call
async def warning_not_registrator(message: Message):
    logger.warning(f"Некорректный ввод при выборе модератора от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками при выборе модератора.\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )
