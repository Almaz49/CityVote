from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonPollType, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import CallbackQuery
from aiogram.methods import GetChatMember
from aiogram.filters.callback_data import CallbackData
import logging
import sqlite3
import asyncio
import re
from config_data.config import Config, load_config
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message, PhotoSize)

markup = InlineKeyboardMarkup()
markup.add(InlineKeyboardButton('Назначить администратором', 'admin'))
print(markup)