#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import ast
import sys
from typing import Any, List, Tuple
from LEXICON.RU.LEXICON_RU import LEXICON_RU

# Готово! LEXICON_RU — это ваш объединённый словарь.
# ----------------------------
# Настройки — укажите ваш файл для проверки
TARGET_FILE = "services/services.py"  # ← измените на нужный путь

# Путь к основному словарю локализации
LEXICON_PATH = "LEXICON/RU/LEXICON_RU.py"

# ----------------------------



def find_get_text_calls(lines: List[str]) -> List[Tuple[int, str]]:
    """
    Находит все вызовы get_text("ключ") в списке строк.
    Возвращает список кортежей: (номер_строки, ключ).
    Учитывает многострочные вызовы.
    """
    calls = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Ищем начало вызова get_text(
        match = re.search(r'\bget_text\s*\(', line)
        if match:
            start_col = match.end() - 1  # позиция '('
            # Извлекаем аргументы до закрывающей скобки
            args_str = extract_arguments(lines, i, start_col)
            if args_str is None:
                i += 1
                continue

            # Берём первый аргумент (должен быть строкой)
            try:
                # Парсим как Python-выражение, чтобы корректно извлечь строку
                parsed = ast.parse(f"dummy({args_str})", mode="eval")
                first_arg = parsed.body.args[0]  # type: ignore
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    key = first_arg.value
                    calls.append((i + 1, key))
                elif isinstance(first_arg, ast.Str):  # для старых версий Python
                    key = first_arg.s
                    calls.append((i + 1, key))
            except Exception:
                pass  # игнорируем некорректные вызовы
        i += 1
    return calls


def extract_arguments(lines: List[str], start_line: int, paren_col: int) -> str | None:
    """
    Извлекает содержимое аргументов функции, начиная с позиции '('.
    Возвращает строку аргументов (без внешних скобок) или None.
    """
    depth = 1
    i = start_line
    j = paren_col + 1
    start_i, start_j = i, j

    while i < len(lines):
        if j >= len(lines[i]):
            i += 1
            j = 0
            continue
        ch = lines[i][j]
        if ch == '#':
            j = len(lines[i])
            continue
        if ch in ('"', "'"):
            # Пропускаем строковые литералы
            quote = ch
            j += 1
            while i < len(lines):
                if j >= len(lines[i]):
                    i += 1
                    j = 0
                    continue
                if lines[i][j] == '\\':
                    j += 2
                    continue
                if lines[i][j] == quote:
                    j += 1
                    break
                j += 1
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                # Собираем аргументы
                if start_i == i:
                    return lines[start_i][start_j:j]
                else:
                    parts = [lines[start_i][start_j:]]
                    parts.extend(lines[start_i + 1:i])
                    parts.append(lines[i][:j])
                    return ''.join(parts)
        j += 1
    return None


def key_exists_in_dict( data: dict, key_path: str) -> bool:
    """
    Проверяет, существует ли путь key_path в словаре data.
    Поддерживает вложенность через точки: "admin.main_menu"
    """
    keys = key_path.split('.')
    current = data
    try:
        for k in keys:
            current = current[k]
        return True
    except (KeyError, TypeError):
        return False


def main():
    print(f"📥 Загружаем LEXICON_RU из {LEXICON_PATH}...")
    try:
        lexicon = LEXICON_RU
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return

    print(f"🔍 Читаем файл {TARGET_FILE}...")
    if not os.path.exists(TARGET_FILE):
        print(f"❌ Файл не найден: {TARGET_FILE}")
        return

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print("🔎 Ищем вызовы get_text()...")
    calls = find_get_text_calls(lines)

    print(f"✅ Найдено {len(calls)} вызовов get_text().")
    missing = []

    for line_num, key in calls:
        if not key_exists_in_dict(lexicon, key):
            missing.append((line_num, key))

    if missing:
        print(f"\n❌ НЕ НАЙДЕНО {len(missing)} КЛЮЧЕЙ:")
        for line_num, key in missing:
            print(f"  Строка {line_num}: ключ '{key}' отсутствует в LEXICON_RU")
    else:
        print("\n✅ Все ключи найдены! 🎉")

    print(f"\n📊 Всего проверено: {len(calls)} вызовов.")


if __name__ == "__main__":
    main()