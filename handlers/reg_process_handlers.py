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
from data_base.telegram_bot_logic import (status_member, extract_user_data_tg, new_status_tg, list_of_members_tg,
update_address, recording_user_data_1, recording_user_data, recording_member_data)
from keyboards.keyboards import reg_markup, contact_markup, remove_markup, user_menu, return_to_main_menu_markup
from filters.filters import ContactFilter
from config_data.config import Config, load_config
from utils import log_handler_call, log_function_call
from LEXICON.LEXICON import LEXICON
from services.services import notify_registrator, notify_registrator_short, notify_super_registrator_short

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()

# -------------------------------------------
#  Хэндлеры упрощенной регистрации участника
# -------------------------------------------

# Хэндлер для кнопки 'registration'
@router.callback_query(F.data == 'registration')
@log_handler_call
async def process_registration(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logging.info(f"Пользователь {callback.from_user.id} нажал на кнопку: {callback.data}")
        await callback.answer()  # Отвечаем на callback, чтобы избежать "крутки часов"

        tg_id = callback.from_user.id

        club_id = data['club_id']

        text = ('Напишите пожалуйста, кто вы и почему хотите вступить в группу.'
                'Эта информация будет переслана выбранному вами регистратору, чтобы он смог принять решение, подтверждать ли ваше вступление в группу.'
                'Если вы согласны продолжать процесс регистрации - пришлите в ответ сообщение.'
                'Если хотите прервать - наберите или нажмите /cancel либо нажмите кнопку "Вернуться в главное меню"'

                )
        markup = return_to_main_menu_markup

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = text
        data['reply_markup'] = markup

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        await state.set_state(FSM_short_registration.fill_resume)

    except Exception as e:
        logging.error(f"Ошибка при обработке кнопки 'registration': {e}")

        # Добавляем данные для SafeEditMiddleware
        data['response_text'] = 'Произошла ошибка при начале процесса регистрации.'
        data['reply_markup'] = await user_menu(callback.from_user.id, data['user_status'])

        # Пытаемся отредактировать сообщение
        await callback.message.edit_text(
            text=data['response_text'],
            reply_markup=data['reply_markup']
        )

        raise  # Передаем исключение middleware для обработки


# Этот хэндлер будет срабатывать, если введено корректное резюме
@router.message(StateFilter(FSM_short_registration.fill_resume))
@log_handler_call
async def process_resume_sent(message: Message, state: FSMContext):
    logging.info(f"Введено резюме кандидата: {message.text} от пользователя {message.from_user.id}")
    # Сохраняем введенное имя в контексте состояния
    await state.update_data(resume=message.text)

    await message.answer(
        text=('Отправьте ваш контакт(телефон)\n'
              'Нажимая кнопку "Отправить телефон", вы даете оператору данного чат-бота на сбор и обработку персональных данных.'
        'Если согласны - нажмите кнопку в самом низу экрана'
        'Если хотите прервать процесс регистрации - наберите или нажмите /cancel'
        'Вы можете обратитьтся к администрации группы напрямую'
             ),
        reply_markup=contact_markup
    )


    # Устанавливаем состояние ожидания отправки контакта
    await state.set_state(FSM_short_registration.fill_contact)

# Этот хэндлер срабатывает на кнопку "Прислать контакт".
@router.message(F.contact, StateFilter(FSM_short_registration.fill_contact))
@log_handler_call
async def process_get_contact_short(message: Message, state: FSMContext):
    # Удаляем сообщение с кнопками, потому что следующий этап - отправка контакта
    # чтобы у пользователя не было желания тыкать кнопки
    await message.answer(
        "Спасибо за контакт!",
        reply_markup=remove_markup  # Удаляем клавиатуру с кнопкой "Отправить контакт"
    )
    try:
        contact: Contact = message.contact
        print('Контакт: ', contact)
        logging.info(f"Контакт получен от пользователя {message.from_user.id}: {contact}")
        tg_true = (message.contact.user_id == message.from_user.id)  # проверяем, действительно ли юзер прислал свой контакт - или чужой


        # Добавляем в FSM дату контакт и сведения об его достоверности
        # Сохраняем данные контакта в контексте состояния
        await state.update_data(
            tg_phone_number=contact.phone_number,
            tg_first_name=contact.first_name,
            tg_last_name=contact.last_name,
            contact_true=tg_true  # флаг 0 в БД будет означать что перед нами хакер
        )


        await message.delete()

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

    except Exception as e:
        logging.error(f"Ошибка при обработке получения контакта: {e}")
        await message.answer(text=f'Произошла ошибка: {str(e)}')


# Этот хэндлер срабатывает на всё, что пришлют вместо контакта в состоянии ожидания контакта
@router.message(StateFilter(FSM_short_registration.fill_contact))
@log_handler_call
async def warning_get_contact_short_reg(message: Message):
    logging.warning(f"Некорректный ввод вместо контакта от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопкой "Отправить контакт"\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )

# Этот хэндлер будет срабатывать на выбор регистратора
@router.callback_query(StateFilter(FSM_short_registration
                                   .fill_registrator),
                      lambda x: x.data.isdigit() or x.data == 'stranger')
@log_handler_call
async def process_registrator_choise(callback: CallbackQuery, state: FSMContext, data: dict):
    try:
        logging.info(f"Выбран регистратор {callback.data} пользователем {callback.from_user.id}")

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
        await recording_user_data(tg_id, **user_param )

        member_id = data['member_id']
        member_param = {}
        member_param['resume'] = user_dict.get('resume')
        await recording_member_data(member_id, **member_param)




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
            logging.info(f"Пользователь {tg_id} выбрал 'Никого не знаю'.")
            success, result = await notify_super_registrator_short(tg_id, user_dict)
            if not success:
                await callback.message.answer(text=f'Ошибка при уведомлении супер-регистратора: {result}')
            # Здесь тоже нужна функция уведомления администрации
    except Exception as e:
        logging.error(f"Ошибка при выборе регистратора: {e}")
        await callback.message.answer(text=f'Произошла ошибка: {str(e)}')
        # Завершаем машину состояний
        await state.clear()

# Этот хэндлер будет срабатывать, если во время выбора регистратора
# будет введено/отправлено что-то некорректное
@router.message(StateFilter(FSM_short_registration.fill_registrator))
@log_handler_call
async def warning_not_registrator(message: Message):
    logging.warning(f"Некорректный ввод при выборе модератора от пользователя {message.from_user.id}")
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками при выборе модератора.\n\nЕсли вы хотите прервать заполнение анкеты - отправьте команду /cancel'
    )
