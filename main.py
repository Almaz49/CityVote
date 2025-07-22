# Модуль main.py - основной цикл бота

import os
import asyncio
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config_data.config import Config, load_config
from handlers import (admin_handlers, chat_member_handlers, delegate_handlers,
                      last_handlers, member_handlers, oll_users_handlers,
                      owner_handlers, reg_process_handlers, candidate_handlers,
                      registrator_handlers, token_handlers, frozen_handlers, ban_handlers)
from manager.manager import check_votist_status_for_all_members, voting_task, check_token_for_oll_members
from middlewares import (LoggingAndErrorHandlingMiddleware, SafeEditMiddleware,
                         StatusMiddleware)
from utils import setup_logger, cleanup_old_logs

# Получаем имя экземпляра бота из переменной окружения
instance_name = os.getenv("BOT_INSTANCE")

# Загружаем конфиг
config: Config = load_config(instance_name=instance_name)

# Проверяем наличие обязательных параметров в конфигурации
if not config.tg_bot.token or not config.db.path_db or not config.tg_bot.club_id:
    raise ValueError("Необходимо указать все обязательные параметры в конфигурации")

path_db = config.db.path_db  # путь к базе данных
club_id = config.tg_bot.club_id  # id группы в БД (не телеграм)
admin_ids: list[int] = config.tg_bot.admin_ids  # Список ID админов из конфига

# PROJECT_DIR — директория, где находится main.py
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Инициализируем бот и диспетчер
bot = Bot(token=config.tg_bot.token)
dp = Dispatcher(storage=MemoryStorage())

# Записываем путь к базе данных и id группы в словарь-хранилище диспетчера для доступа в других модулях
dp["path_db"] = path_db
dp["club_id"] = club_id
dp["instance_name"] = instance_name


# Настройка логгирования
logger = setup_logger(
    debug_log_path=f"logs/{instance_name}_debug.log",
    info_log_path=f"logs/{instance_name}_info.log",
    warning_log_path=f"logs/{instance_name}_warning.log",
    error_log_path=f"logs/{instance_name}_error.log",
    console_level=logging.WARNING,  # Здесь менять уровень вывода логов в консоль
    file_encoding="utf-8",
)

# # Тестовое сообщение
# logger.info("Логгирование настроено в main.py")
# # Пример использования
# logger.debug("Это debug-сообщение")  # Не будет выведено в консоль
# logger.info("Это info-сообщение")
# logger.warning("Это warning-сообщение")
# logger.error("Это error-сообщение")
logger.warning(f"Бот {instance_name} версии 20.07.25 начал работу")
logger.info(f"[DEBUG] PROJECT_DIR = {PROJECT_DIR}")

# --- Инициализируем планировщик ---
scheduler = AsyncIOScheduler()


def schedule_jobs():
    logger.info("Запущен планировщик задач")
    tz_name = config.tg_bot.timezone  # <- получаем из конфига
    try:
        tz = ZoneInfo(tz_name)
    except Exception as e:
        tz = ZoneInfo("UTC")
        logger.warning(f"Неизвестный часовой пояс '{tz_name}'. Используется UTC.")

    # Проврка права голоса для всех пользователей
    scheduler.add_job(
        check_votist_status_for_all_members, "interval", hours=1, args=[club_id]
    )  # раз в час

    # Запуск голосований
    scheduler.add_job(
        voting_task,
        "cron",
        hour=0,
        minute=0,
        timezone=tz,
        id="voting_task",
        args=[bot, club_id, instance_name],
    ) # раз в сутки

    # Проверка токенов для всех польователей
    scheduler.add_job(
        check_token_for_oll_members,
        "cron",
        hour=1,
        minute=0,
        timezone=tz,
        id="check_token_for_oll_members",
        args=[bot, club_id, instance_name],
    ) # раз в сутки

    # Очистка старых логов
    scheduler.add_job(
        cleanup_old_logs,
        "cron",
        hour=2,  # Выполнять в 2:00 ночи
        timezone=tz,
        id="cleanup_old_logs",
        args=[os.path.join(PROJECT_DIR, "logs")],  # Путь к папке с логами
        kwargs={"days_to_keep": 7}  # Хранить 7 дней
    )

    # scheduler.add_job(voting_task, 'interval', seconds=60, args=[club_id])  # раз в 60 секунд


# --- Подключаем хуки старта и завершения работы ---
@dp.startup()
async def on_startup():
    logger.info(f"Бот запущен с часовым поясом: {config.tg_bot.timezone}")
    schedule_jobs()
    scheduler.start()


@dp.shutdown()
async def on_shutdown():
    logger.info("Бот остановлен")
    scheduler.shutdown()


# Регистрируем middleware
dp.update.middleware(LoggingAndErrorHandlingMiddleware())  # Первым идет логгирование
dp.update.middleware(StatusMiddleware())
dp.update.middleware(SafeEditMiddleware())  # Затем middleware для safe_edit

# Регистрируем роутеры
routers = [
    owner_handlers.router,
    candidate_handlers.router,
    frozen_handlers.router,  # Все хэндлеры ниже будут недоступны для пользователей с просроченным токеном
    oll_users_handlers.router,
    member_handlers.router,
    ban_handlers.router, # Все хэндлеры ниже будут недоступны для заблокированных пользователей
    delegate_handlers.router,
    registrator_handlers.router,
    admin_handlers.router,
    reg_process_handlers.router,
    chat_member_handlers.router,
    token_handlers.router,
    last_handlers.router # После него не ставить роутеров
]


for router in routers:
    if router is not None:
        dp.include_router(router)


async def main():
    try:
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "chat_member",
                "my_chat_member",
                "commands",
            ],
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
