#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Этот скрипт автоматически заменяет прямые обращения к словарю LEXICON
# в файле services/services.py на вызовы функции get_text(...),
# обеспечивая поддержку динамической локализации.
#
# Поддерживаемые шаблоны:
#   1. LEXICON["ключ"] → get_text("ключ", lang=lang)
#   2. LEXICON.get("ключ", ...) → get_text("ключ", lang=lang)
#
# Особенности:
#   - Для однострочных обращений (типа LEXICON["..."]) замена происходит в той же строке.
#   - Для многострочных вызовов LEXICON.get(...) скрипт корректно находит
#     закрывающую скобку с учётом вложенных скобок, строк и комментариев.
#   - Все исходные строки комментируются (с префиксом #), чтобы сохранить
#     возможность отката или сравнения.
#   - Создаётся резервная копия исходного файла с расширением .bak.
#
# Требования к контексту:
#   - В функциях, где используется замена, должен быть доступен параметр `lang`.
#
# Цель: унифицировать доступ к локализованным сообщениям через единую функцию get_text,
# что упрощает дальнейшую поддержку нескольких языков и централизованное управление переводами.

# This script automatically replaces direct accesses to the LEXICON dictionary
# in the file services/services.py with calls to the get_text(...) function,
# enabling dynamic localization support.
#
# Supported patterns:
#   1. LEXICON["key"] → get_text("key", lang=lang)
#   2. LEXICON.get("key", ...) → get_text("key", lang=lang)
#
# Key features:
#   - Single-line accesses (e.g., LEXICON["..."]) are replaced in place.
#   - Multi-line LEXICON.get(...) calls are handled correctly: the script
#     locates the matching closing parenthesis while respecting nested parentheses,
#     string literals, and comments.
#   - Original lines are preserved as comments (prefixed with #) for reference
#     or easy rollback.
#   - A backup of the original file is saved with a .bak extension.
#
# Context requirement:
#   - The `lang` variable must be available in the scope where the replacement occurs.
#
# Purpose: to unify all localized message lookups through a single get_text interface,
# simplifying multi-language support and centralized translation management.

import os
import re
import shutil
from typing import List, Optional

INPUT_FILE = "services/services.py"
BACKUP_FILE = INPUT_FILE + ".bak"

def find_closing_paren(lines: List[str], start_line: int, start_col: int) -> Optional[tuple[int, int]]:
    """
    Находит позицию закрывающей скобки ')', соответствующей открывающей в (start_line, start_col).
    Возвращает (line_index, char_index) или None.
    """
    depth = 1  # уже находимся внутри первой '('
    i = start_line
    j = start_col + 1  # начинаем со следующего символа после '('

    while i < len(lines):
        if j >= len(lines[i]):
            i += 1
            j = 0
            continue

        ch = lines[i][j]

        # Игнорируем комментарии
        if ch == '#':
            j = len(lines[i])
            continue

        # Обработка строковых литералов
        if ch in ('"', "'"):
            quote = ch
            j += 1
            while i < len(lines) and j < len(lines[i]):
                if lines[i][j] == '\\':
                    j += 2  # пропускаем экранированный символ
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
                return (i, j)
        j += 1

    return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Файл {INPUT_FILE} не найден.")
        return

    shutil.copy2(INPUT_FILE, BACKUP_FILE)
    print(f"✅ Бэкап сохранён: {BACKUP_FILE}")

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    count = 0

    while i < len(lines):
        line = lines[i]

        # === 1. Обработка LEXICON["key"] (всегда однострочная) ===
        if 'LEXICON[' in line:
            match = re.search(r'LEXICON\s*\[\s*([\'"])([^\'"]+)\1\s*\]', line)
            if match:
                key = match.group(2)
                new_part = f'get_text("{key}", lang=lang)'
                new_line = line[:match.start()] + new_part + line[match.end():]
                # Комментируем
                orig = line.rstrip('\n\r')
                commented = "# " + orig + "\n" if orig.strip() and not orig.lstrip().startswith('#') else orig + "\n"
                new_lines.append(commented)
                new_lines.append(new_line)
                count += 1
                i += 1
                continue

        # === 2. Обработка LEXICON.get(...) (может быть многострочной) ===
        get_match = re.search(r'\bLEXICON\s*\.get\s*\(', line)
        if get_match:
            get_start = get_match.start()
            paren_start_col = get_match.end() - 1  # позиция '('

            # Найдём закрывающую скобку во всём файле
            result = find_closing_paren(lines, i, paren_start_col)
            if result is None:
                # Не смогли найти — пропускаем
                new_lines.append(line)
                i += 1
                continue

            end_line, end_col = result

            # Извлекаем содержимое между скобками (без внешних скобок)
            if i == end_line:
                inner = lines[i][paren_start_col + 1:end_col]
            else:
                first = lines[i][paren_start_col + 1:]
                middle = lines[i + 1:end_line]
                last = lines[end_line][:end_col]
                inner = first + ''.join(middle) + last

            # Ищем первый строковый литерал в inner
            inner_no_comments = re.sub(r'#.*', '', inner)
            key_match = re.search(r'(["\'])((?:(?!\1).)*)\1', inner_no_comments)
            if not key_match:
                new_lines.append(line)
                i += 1
                continue

            key = key_match.group(2)
            new_call = f'get_text("{key}", lang=lang)'

            # Голова — всё до LEXICON.get
            head = lines[i][:get_start]
            # Хвост — всё после закрывающей скобки в последней строке
            tail = lines[end_line][end_col + 1:]

            new_line = head + new_call + tail

            # Комментируем все строки от i до end_line
            for k in range(i, end_line + 1):
                orig_line = lines[k].rstrip('\n\r')
                if orig_line.strip() and not orig_line.lstrip().startswith('#'):
                    new_lines.append("# " + orig_line + "\n")
                else:
                    new_lines.append(orig_line + "\n")

            new_lines.append(new_line)
            count += 1
            i = end_line + 1
        else:
            new_lines.append(line)
            i += 1

    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"✅ Заменено {count} вызовов LEXICON.")

if __name__ == "__main__":
    main()