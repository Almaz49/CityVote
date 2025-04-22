# Модуль data_base. Служит для сборки других модулей, работающих с базой данных.
import random
import time
from data_base.db_member import *
from data_base.db_vote import *
from utils import log_function_call
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

@log_function_call
async def votist(member_id):
    async with AsyncDatabase(path_db) as cursor:
        try:
            # Проверяем статусы участника
            await cursor.execute('''
                SELECT status FROM Status
                WHERE member_id = ?
            ''', (member_id,))
            result = await cursor.fetchall()
            logger.info(f"Проверка статусов для member_id={member_id}: {result}")

            # Проверяем, является ли участник членом
            if ('member',) not in result:
                logger.info(f"Участник с member_id={member_id} не является членом")
                await cursor.execute('''
                    DELETE FROM Status WHERE member_id = ? AND status = 'votist'
                ''', (member_id,))
                logger.info(f"Отобран статус 'votist' для member_id={member_id}")
                return

            # Проверяем, является ли участник представителем
            if ('proxy',) in result:
                logger.info(f"Участник с member_id={member_id} является представителем")
                await cursor.execute('''
                    INSERT OR IGNORE INTO Status(member_id, status) VALUES (?, 'votist')
                ''', (member_id,))
                logger.info(f"Присвоен статус 'votist' для member_id={member_id}")
                return

            # Проверяем, есть ли у участника представитель
            await cursor.execute('''
                SELECT status FROM Status WHERE member_id IN
                (SELECT proxy FROM Members WHERE id = ?)
            ''', (member_id,))
            st_pr = await cursor.fetchall()
            logger.info(f"Статус представителя для member_id={member_id}: {st_pr}")

            if ('proxy',) in st_pr:
                logger.info(f"У участника с member_id={member_id} есть представитель")
                await cursor.execute('''
                    INSERT OR IGNORE INTO Status(member_id, status) VALUES (?, 'votist')
                ''', (member_id,))
                logger.info(f"Присвоен статус 'votist' для member_id={member_id}")
            else:
                logger.info(f"У участника с member_id={member_id} нет представителя")
                await cursor.execute('''
                    DELETE FROM Status WHERE member_id = ? AND status = 'votist'
                ''', (member_id,))
                logger.info(f"Отобран статус 'votist' для member_id={member_id}")

        except aiosqlite.Error as e:
            logger.error(f"Ошибка при работе с правом голоса: {e}", exc_info=True)
            raise

# # Пример использования функции для тестирования
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(votist(10))
