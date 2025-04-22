# Просмотреть последние 50 строк системного лога
sudo tail -n 50 /var/log/syslog

# Просмотреть логи в реальном времени (следить за обновлениями)
sudo tail -f /var/log/syslog

# Найти ошибки в системных логах
sudo grep "error" /var/log/syslog

# Просмотреть логи конкретного сервиса через journalctl
sudo journalctl -u service-name.service

# Просмотреть последние 50 строк логов сервиса
sudo journalctl -u service-name.service -n 50

# Просмотреть логи сервиса в реальном времени
sudo journalctl -u service-name.service -f

# Очистить логи journalctl (удалить старые записи)
sudo journalctl --vacuum-time=2weeks

# Просмотреть логи ядра системы
dmesg

# Сохранить логи в файл для анализа
sudo journalctl > system_logs.txt

# Просмотреть логи авторизации (например, входы в систему)
sudo cat /var/log/auth.log