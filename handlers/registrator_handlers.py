from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)
from filters.filters import filter_isRegistrator
from keyboards.keyboards import reg_keyboard, contact_keyboard, remove_keyboard
from config_data.config import Config, load_config

#инициализируем бота
# Загружаем конфиг в переменную config
config: Config = load_config('.env')
bot = Bot(token=config.tg_bot.token)

# Инициализируем роутер уровня модуля
router = Router()
router.message.filter(filter_isRegistrator)

#Хэндлер на команду старт
@router.message(Command(commands=["start"]),filter_isRegistrator)
async def process_start_command2(message: Message):
    await bot.send_message(message.from_user.id,
        'Привет, Регистратор!\nМеня зовут Эхо-бот!\nНапиши мне что-нибудь')


'''
Подтверждение или нет членства участника регистратором после заполнения анкеты
'''


#Этот хэндлер срабатывает при нажатии регистратором кнопки "подтверждаю"
#при регистрации участника
@router.callback_query(F.data.split(':')[0]=='yes_confirm')
async def process_registrator_yes_press(callback: CallbackQuery):
    #удаляем кнопки у сообщения
    await callback.message.delete_reply_markup()
    #Меняем в бд статус пользователя с User на Member
    tg_id = int(callback.data.split(':',)[1]) #Выделяем телеграм ID полльзователя из коллбэкдаты
    cv = {'status':'member'}
    db_update('Members','tg_id',tg_id, **cv)
    await callback.message.answer(text = f"Спасибо!\n"
                    f'Пользоватль {tg_id} получил статус "Участник"\n'
                         )    
    
#Этот хэндлер срабатывает при нажатии регистратором кнопки "Не подтверждаю"
#при регистрации участника
@router.callback_query(F.data.split(':')[0]=='no_confirm'
                   )
async def process_registrator_no_press(callback: CallbackQuery):
    #удаляем кнопками у сообщения
    await callback.message.delete_reply_markup()
    #Меняем в  бд в строке пользователя поле "familiar" - вместо ID регистраторва ставим "stranger"
    tg_id = int(callback.data.split(':',)[1]) #Выделяем телеграм ID полльзователя из коллбэкдаты
    cv = {'familiar','stranger'}
    db_update('Members','tg_id',tg_id, **cv)
    await callback.message.answer(text = f"Спасибо!\n"
                    f'Пользоватль {tg_id} не получил статус "Участник"\n'
                         )    
