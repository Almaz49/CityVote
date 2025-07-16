"""
Файл для запуска бота из VS Code.
Активирует виртуальное окружение (если есть) и запускает main.py
"""

import os
import sys
import subprocess

# Конфигурация
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = "main.py"
VENV_PATH = os.path.join(PROJECT_DIR, "venv")
VENV_PYTHON = os.path.join(VENV_PATH, "Scripts", "python.exe")

# Переменная окружения (уберите, если не используете несколько ботов)
BOT_INSTANCE = "bot01"  # или None, если не нужно


def activate_venv():
    """Добавляет путь к виртуальному окружению в PATH, если оно существует"""
    if os.path.exists(VENV_PATH):
        venv_scripts = os.path.join(VENV_PATH, "Scripts")
        os.environ["PATH"] = venv_scripts + os.pathsep + os.environ["PATH"]
        if hasattr(os, 'add_dll_directory'):
            dll_path = os.path.join(venv_scripts)
            if os.path.exists(dll_path):
                os.add_dll_directory(dll_path)
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
    result = subprocess.run(
        [python_executable, MAIN_SCRIPT],
        env=env,
        cwd=PROJECT_DIR
    )
    return result.returncode


if __name__ == "__main__":
    activate_venv()
    sys.exit(run_bot())