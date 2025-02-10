# Модуль delegate_handlers
# В нем хэндлеры пользователей, обладающих правами делегатов
from aiogram import Bot, Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from filters.filters import filter_isDelegate
from FSMs.FSMs import FSMNewVoting, FSMNewVariant
from keyboards.keyboards import confirm_markup, variant_markup, create_inline_kb, user_menu
from config_data.config import Config, load_config
from data_base.telegram_bot_logic import new_vote_tg, new_variant_tg, list_of_votes_tg
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()

# Навешиваем на роутер фильтр, проверяющий, является ли пользователь Делегатом
router.message.filter(filter_isDelegate)

"""
СОЗДАНИЕ ГОЛОСОВАНИЯ
"""

# Этот хэндлер будет срабатывать на команду /new_vote
# и переводить бота в состояние ожидания ввода названия голосования
@router.message(Command(commands='new_vote'), StateFilter(default_state))
async def process_new_voting_start(message: Message, state: FSMContext):
    """
    Обработчик команды /new_vote.
    Запускает процесс создания нового голосования.
    """
    logging.info(f"Пользователь {message.from_user.id} начал создание голосования.")
    await message.answer(text='Пожалуйста, введите название голосования.')
    await state.set_state(FSMNewVoting.fill_vote_title)

# Этот хэндлер будет срабатывать на нажатие кнопки "создать голосование"
# и переводить бота в состояние ожидания ввода названия голосования
@router.callback_query(StateFilter(default_state), F.data == 'new_vote')
async def process_new_voting_start(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик команды /new_vote.
    Запускает процесс создания нового голосования.
    """
    logging.info(f"Пользователь {callback.from_user.id} начал создание голосования.")
    await callback.message.answer(text='Пожалуйста, введите название голосования.')
    await state.set_state(FSMNewVoting.fill_vote_title)


# Этот хэндлер будет срабатывать на ввод названия
# и переводить бота в состояние ожидания ввода описания голосования
@router.message(StateFilter(FSMNewVoting.fill_vote_title))
async def process_new_voting_title_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода названия голосования.
    Сохраняет название и запрашивает описание.
    """
    logging.info(f"Пользователь {message.from_user.id} ввел название голосования: {message.text}.")
    if len(message.text) > 40:
        await message.answer("Название не должно быть длиннее 40 символов. Попробуйте снова.")
        return
    await state.update_data(title=message.text)
    await message.answer(text='Пожалуйста, введите описание голосования.')
    await state.set_state(FSMNewVoting.fill_vote_description)


# Этот хэндлер будет срабатывать после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVoting.fill_vote_description))
async def process_new_voting_description_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода описания голосования.
    Запрашивает подтверждение данных.
    """
    logging.info(f"Пользователь {message.from_user.id} ввел описание голосования: {message.text}.")
    await state.update_data(description=message.text)
    data = await state.get_data()
    title = data['title']
    description = data['description']

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
async def process_new_voting_yes_confirm_press(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик подтверждения создания голосования.
    Создает новое голосование в базе данных.
    """
    logging.info(f"Пользователь {callback.from_user.id} подтвердил создание голосования.")
    try:
        data = await state.get_data()
        title = data['title']
        description = data['description']
        tg_id = callback.from_user.id

        # Создаем новое голосование
        flag, comment = await new_vote_tg(creator_tg_id=tg_id, title=title, text=description, vote_status='add_variants')
        if flag:
            await state.clear()
            await callback.message.edit_text(text='Спасибо! Голосование создано! Вы вышли из машины состояний.')
        else:
            await callback.message.edit_text(text=f'Ошибка: {comment}')
    except Exception as e:
        logging.error(f"Ошибка при создании голосования: {e}")
        await callback.message.edit_text(
            text=f"Произошла ошибка: {str(e)}",
            reply_markup=user_menu(callback.from_user.id)
            )
        await state.clear()


# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK), F.data == 'ConfirmNotOK')
async def process_new_voting_no_confirm_press(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик отмены создания голосования.
    Завершает машину состояний.
    """
    logging.info(f"Пользователь {callback.from_user.id} отменил создание голосования.")
    await state.clear()
    await callback.message.edit_text(text='Голосование не создано! Попробуйте еще раз. Вы вышли из машины состояний.')


"""
Добавление варианта
"""

# Этот хэндлер будет срабатывать на команду /new_variant
# и переводить бота в состояние ожидания выбора голосования
@router.message(Command(commands='new_variant'), StateFilter(default_state))
async def process_new_variant_start(message: Message, state: FSMContext):
    """
    Обработчик команды /new_variant.
    Запрашивает выбор голосования для добавления варианта.
    """
    logging.info(f"Пользователь {message.from_user.id} начал добавление варианта.")
    try:
        list_of_votes = await list_of_votes_tg('add_variants')
        if not list_of_votes:
            await message.answer(text='Сейчас нет активных голосований, вы не можете добавить вариант.')
            return

        # Создаем клавиатуру с активными голосованиями
        keyboards = {str(item[0]): item[1] for item in list_of_votes}
        markup = create_inline_kb(1, **keyboards)

        await message.answer(text='Пожалуйста, выберите, к какому голосованию вы хотите добавить вариант:', reply_markup=markup)
        await state.set_state(FSMNewVariant.fill_vote_choise)
    except Exception as e:
        logging.error(f"Ошибка при получении списка голосований: {e}")
        await message.answer(
            text=f"Произошла ошибка: {str(e)}",
            reply_markup=user_menu(message.from_user.id)
            )
        await state.clear()


# Этот хэндлер будет срабатывать на нажатие кнопки с названием голосования
@router.callback_query(StateFilter(FSMNewVariant.fill_vote_choise), F.data)
async def process_variant_title_sent(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора голосования.
    Запрашивает ввод названия варианта.
    """
    logging.info(f"Пользователь {callback.from_user.id} выбрал голосование ID={callback.data}.")
    await state.update_data(vote_id=int(callback.data))
    await callback.message.edit_text(text='Пожалуйста, введите название варианта.', reply_markup=None)
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на ввод названия варианта
# и переводить бота в состояние ожидания ввода описания
@router.message(StateFilter(FSMNewVariant.fill_variant_title))
async def process_variant_description_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода названия варианта.
    Запрашивает ввод описания.
    """
    logging.info(f"Пользователь {message.from_user.id} ввел название варианта: {message.text}.")
    if len(message.text) > 40:
        await message.answer("Название не должно быть длиннее 40 символов. Попробуйте снова.")
        return
    await state.update_data(title=message.text)
    await message.answer(text='Пожалуйста, введите описание варианта.')
    await state.set_state(FSMNewVariant.fill_variant_description)


# Этот хэндлер будет срабатывать после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVariant.fill_variant_description))
async def process_new_variant_description_sent(message: Message, state: FSMContext):
    """
    Обработчик ввода описания варианта.
    Запрашивает подтверждение данных.
    """
    logging.info(f"Пользователь {message.from_user.id} ввел описание варианта: {message.text}.")
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
async def process_new_variant_yes_confirm_press(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик подтверждения добавления варианта.
    Создает новый вариант в базе данных.
    """
    logging.info(f"Пользователь {callback.from_user.id} подтвердил добавление варианта.")
    try:
        data = await state.get_data()
        vote_id = data['vote_id']
        title = data['title']
        description = data['description']
        tg_id = callback.from_user.id

        # Создаем новый вариант
        result, comment = await new_variant_tg(vote_id=vote_id, creator_tg_id=tg_id, title=title, text=description)
        if result:
            await callback.message.edit_text(
                text='Спасибо! Вариант создан!\nХотите ли добавить ещё вариант?',
                reply_markup=variant_markup
            )
            await state.set_state(FSMNewVariant.fill_more_variant)
        else:
            await callback.message.edit_text(text=f'Ошибка: {comment}')
    except Exception as e:
        logging.error(f"Ошибка при добавлении варианта: {e}")
        await callback.message.edit_text(
            text=f"Произошла ошибка: {str(e)}",
            reply_markup=user_menu(callback.from_user.id))
        await state.clear()


# Этот хэндлер будет срабатывать на нажатие кнопки "Добавить ещё вариант"
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant), F.data == 'NewVariant')
async def process_more_variant(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик добавления ещё одного варианта.
    Возвращает пользователя к вводу названия варианта.
    """
    logging.info(f"Пользователь {callback.from_user.id} решил добавить ещё один вариант.")
    await callback.message.edit_text(text='Пожалуйста, введите название варианта.')
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на нажатие кнопки "Завершить добавление вариантов"
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant), F.data == 'Finish_Variant')
async def process_finish_variant(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик завершения добавления вариантов.
    Завершает машину состояний.
    """
    logging.info(f"Пользователь {callback.from_user.id} завершил добавление вариантов.")
    await state.clear()
    await callback.message.edit_text(text='Спасибо! Все варианты добавлены! Вы вышли из машины состояний.')

"""
Добавление варианта
"""

# Этот хэндлер будет срабатывать на команду /new_variant
# и переводить бота в состояние ожидания выбора голосования
# к которому добавляется вариант
@router.message(Command(commands='new_variant'), StateFilter(default_state))
async def process_new_variant_start(message: Message, state: FSMContext):
    list_of_votes = list_of_votes_tg('add_variants')
    if list_of_votes:
        keyboards = {}
        for item in list_of_votes:
            keyboards[str(item[0])] = item[1]
        markup = create_inline_kb(1,**keyboards)
    else:
        await message.answer(text = 'Сейчас нет активных голосований,'
        'вы не можете добавить вариант')
        return()


    # Устанавливаем состояние ожидания ввода названия
    await message.answer(text='''Пожалуйста, выберите, к какому голосованию
    вы хотите добавить вариант''',
    reply_markup = markup
    )
    await state.set_state(FSMNewVariant.fill_vote_choise)

#Этот хэндлер будет срабатывать на нажатие кнопки с названием голосования
@router.callback_query(StateFilter(FSMNewVariant.fill_vote_choise), F.data)
async def process_variant_title_sent(callback: CallbackQuery, state: FSMContext):
    # Cохраняем ID голосования по ключу vote_id
    await state.update_data(vote_id=int(callback.data))
    # Удаляем сообщение с кнопками
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.edit_text(text='Пожалуйста, введите название варианта',
        reply_markup=None)
    await state.set_state(FSMNewVariant.fill_variant_title)



# Этот хэндлер будет срабатывать на ввод названия варианта
# и переводить бота в состояние ожидания ввода описания голосования
@router.message(StateFilter(FSMNewVariant.fill_variant_title))
async def process_variant_description_sent(message: Message, state: FSMContext):
    # Cохраняем название в хранилище по ключу "title"
    await state.update_data(title = message.text)
    await message.answer(text='Пожалуйста, введите описание варианта')
    # Устанавливаем состояние ожидания ввода названия
    await state.set_state(FSMNewVariant.fill_variant_description)



# Этот хэндлер будет срабатывать, после ввода описания
# и переводить в состояние ожидания подтверждения
@router.message(StateFilter(FSMNewVariant.fill_variant_description))
async def process_new_variant_description_sent(message: Message, state: FSMContext):
    # Cохраняем название в хранилище по ключу "description"
    await state.update_data(description = message.text)
    data = await state.get_data()
    title = data['title']
    description = message.text
#здесь создание кнопок, если надо
    await message.answer(text=f'''Пожалуйста, подтвердите, правильно ли введены
                         название и описание варианта?
                         Название:
                         {title}
                         Текст:
                         {description}

                         ''',
                         reply_markup=confirm_markup
                         )

    # Устанавливаем состояние ожидания ввода подтверждения
    await state.set_state(FSMNewVariant.fill_OK)



# Этот хэндлер будет срабатывать на нажатие кнопки "ВСЁ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVariant.fill_OK),
                   F.data == 'ConfirmOK')
async def process_new_variant_yes_confirm_press(callback: CallbackQuery, state: FSMContext):
    # Заносим в базу данных голосование
    # по ключу tg_id пользователя b tg_id регистратора (админа в данном случае)
    data = await state.get_data()
    vote_id = data['vote_id']
    title = data['title']
    description = data['description']
    tg_id = callback.from_user.id
#     Записываем новое голосование в базу данных
    new_variant_tg(vote_id=vote_id, creator_tg_id=tg_id, title=title, text=description)


    await callback.message.edit_text(
        text='Спасибо! Вариант создано!\n'
             'Хотите ли добавить ещё вариант?',
        reply_markup = variant_markup
        )
    await state.set_state(FSMNewVariant.fill_more_variant)

# Этот хэндлер будет срабатывать на нажатие кнопки "НЕ ВЕРНО"
@router.callback_query(StateFilter(FSMNewVoting.fill_OK),
                   F.data == 'ConfirmNotOK')
async def process_new_variant_no_confirm_press(callback: CallbackQuery, state: FSMContext):
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Вариант не создан!'
             'Хотите ли добавить другой вариант?',
        reply_markup = variant_markup
        )
    await state.set_state(FSMNewVariant.fill_more_variant)

# Этот хэндлер будет срабатывать на нажатие кнопки "Добавить ещё вараинт"
# Откатываем машину состояния в точку ввода названия варианта
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant),
                   F.data == 'NewVariant')
async def process_more_variant(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text='Пожалуйста, введите название варианта')
    await state.set_state(FSMNewVariant.fill_variant_title)


# Этот хэндлер будет срабатывать на нажатие кнопки "Завершить добавление вариантов"
@router.callback_query(StateFilter(FSMNewVariant.fill_more_variant),
                   F.data == 'Finish_Variant')
async def process_finish_variant(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await callback.message.edit_text(
        text='Спасибо! Голосование создано!\n'
             'Вы вышли из машины состояний'
        )