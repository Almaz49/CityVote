# Проверить версию Python
python3 --version

# Проверить установленные пакеты Python
pip list

# Установить пакет Python
pip install package_name

# Удалить пакет Python
pip uninstall package_name

# Создать виртуальное окружение Python
python3 -m venv venv_name

# Активировать виртуальное окружение
source venv_name/bin/activate

# Деактивировать виртуальное окружение
deactivate

# Проверить, какие порты заняты
sudo netstat -tuln

# Проверить, какая программа использует конкретный порт
sudo lsof -i :port_number

# Найти файл по содержимому (например, тексту внутри файла)
grep -r "search_text" /path/to/search