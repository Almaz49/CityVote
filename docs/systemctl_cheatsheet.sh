#!/bin/bash
# Справочник команд для редактирования и управления системными файлами, такими как telegram-bot.service.

# Открыть файл telegram-bot.service для редактирования (используя nano)
sudo nano /etc/systemd/system/telegram-bot.service

# Проверить корректность конфигурации файла сервиса
sudo systemctl daemon-reload

# Запустить сервис telegram-bot.service
sudo systemctl start telegram-bot.service

# Остановить сервис telegram-bot.service
sudo systemctl stop telegram-bot.service

# Перезапустить сервис telegram-bot.service
sudo systemctl restart telegram-bot.service

# Включить автозапуск сервиса при загрузке системы
sudo systemctl enable telegram-bot.service

# Отключить автозапуск сервиса при загрузке системы
sudo systemctl disable telegram-bot.service

# Проверить статус сервиса (работает ли он, есть ли ошибки)
sudo systemctl status telegram-bot.service

# Просмотреть логи сервиса через journalctl
sudo journalctl -u telegram-bot.service

# Просмотреть последние 50 строк логов сервиса
sudo journalctl -u telegram-bot.service -n 50

# Просмотреть логи сервиса в реальном времени (следить за обновлениями)
sudo journalctl -u telegram-bot.service -f

# Удалить файл сервиса telegram-bot.service
sudo rm /etc/systemd/system/telegram-bot.service

# Создать новый файл сервиса (пустой)
sudo touch /etc/systemd/system/telegram-bot.service

# Сделать файл сервиса доступным только для чтения (защита от случайного изменения)
sudo chmod 444 /etc/systemd/system/telegram-bot.service

# Вернуть права на запись для файла сервиса
sudo chmod 644 /etc/systemd/system/telegram-bot.service

# Отобразить содержимое файла сервиса (без редактирования)
cat /etc/systemd/system/telegram-bot.service

# Скопировать файл сервиса в другую директорию (например, для резервной копии)
sudo cp /etc/systemd/system/telegram-bot.service /path/to/backup/telegram-bot.service.backup

# Переименовать файл сервиса
sudo mv /etc/systemd/system/telegram-bot.service /etc/systemd/system/new-telegram-bot.service

# Обновить systemd после изменений в файле сервиса
sudo systemctl daemon-reload