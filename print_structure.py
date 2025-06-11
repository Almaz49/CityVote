# Скрипт делает дерево проекта и выводит его в файл, игнорируя служебные папки.

import os

# Папки и файлы, которые нужно исключить
IGNORE = {
    "venv", ".vscode", ".qodo", "__pycache__",
    ".git", ".env", "__pycache__", ".DS_Store"
}

def write_tree(startpath, file_handle):
    for root, dirs, files in os.walk(startpath):
        # Убираем папки, которые хотим игнорировать
        dirs[:] = [d for d in dirs if d not in IGNORE]

        level = root.replace(startpath, "").count(os.sep)
        indent = "│   " * (level) + "├── " if level > 0 else ""
        file_handle.write(f"{indent}{os.path.basename(root)}/\n")

        subindent = "│   " * (level + 1)
        for f in sorted(files):
            file_handle.write(f"{subindent}└── {f}\n")

# Записываем структуру в файл structure.txt
if __name__ == "__main__":
    with open("structure.txt", "w", encoding="utf-8") as f:
        write_tree(".", f)
    print("✅ Структура проекта сохранена в файл structure.txt")