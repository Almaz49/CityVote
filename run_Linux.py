"""
Файл для запуска Telegram-бота в Linux/macOS
"""

import os
import sys
import subprocess

# Конфигурация
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(PROJECT_DIR, "main.py")
VENV_PATH = os.path.join(PROJECT_DIR, "venv")
VENV_PYTHON = os.path.join(VENV_PATH, "bin", "python")

# Переменная окружения — измените, если хотите запускать разные ботов
BOT_INSTANCE = "bot01"  # или None, если не нужно


def activate_venv():
    """Добавляет пути виртуального окружения в os.environ, если оно существует"""
    if os.path.exists(VENV_PATH):
        venv_bin = os.path.join(VENV_PATH, "bin")
        os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"
        os.environ["VIRTUAL_ENV"] = VENV_PATH
        print(f"[INFO] Используется виртуальное окружение: {VENV_PATH}")
    else:
        print(f"[WARNING] Виртуальное окружение не найдено: {VENV_PATH}")


def run_bot():
    """Запуск бота с переменной BOT_INSTANCE"""
    env = os.environ.copy()
    if BOT_INSTANCE:
        env["BOT_INSTANCE"] = BOT_INSTANCE
        print(f"[INFO] Запуск бота с BOT_INSTANCE={BOT_INSTANCE}")
    else:
        print("[INFO] Запуск бота с .env из корня проекта")

    # Выбор интерпретатора: текущий или из venv
    python_executable = sys.executable
    if os.path.exists(VENV_PYTHON):
        python_executable = VENV_PYTHON

    # Запуск бота
    print(f"[INFO] Запуск бота через: {python_executable} {MAIN_SCRIPT}")
    result = subprocess.run(
        [python_executable, MAIN_SCRIPT],
        env=env,
        cwd=PROJECT_DIR,
        check=False
    )
    return result.returncode


if __name__ == "__main__":
    activate_venv()
    sys.exit(run_bot())