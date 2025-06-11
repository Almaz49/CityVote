# Модуль data_base. Служит для сборки других модулей, работающих с базой данных.
from data_base.db_member import *
from data_base.db_vote import *
import logging

# Настройка логирования
logger = logging.getLogger(__name__)
