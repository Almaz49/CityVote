# Экспорт всех логов сервиса
sudo journalctl -u telegram-bot.service > /CityVote/all_logs.txt

# Логи за последний день
sudo journalctl -u telegram-bot.service --since "1 day ago" > /CityVote/last_day_logs.txt

# Логи за последнюю неделю
sudo journalctl -u telegram-bot.service --since "1 week ago" > /CityVote/last_week_logs.txt

# Логи за последний месяц
sudo journalctl -u telegram-bot.service --since "1 month ago" > /CityVote/last_month_logs.txt

# Логи за конкретный период (например, с 1 апреля по 20 апреля)
sudo journalctl -u telegram-bot.service --since "2023-04-01" --until "2023-04-20" > /CityVote/specific_period_logs.txt

# Логи только с ошибками
sudo journalctl -u telegram-bot.service -p err > /CityVote/error_logs.txt

# Логи с предупреждениями и выше
sudo journalctl -u telegram-bot.service -p warning > /CityVote/warning_logs.txt

# Логи с фильтрацией по ключевым словам (например, только строки с "ERROR")
sudo journalctl -u telegram-bot.service | grep "ERROR" > /CityVote/filtered_logs.txt

# Логи в реальном времени (запись продолжается до остановки Ctrl+C)
sudo journalctl -u telegram-bot.service -f > /CityVote/realtime_logs.txt

# Сжатие логов в архив
sudo journalctl -u telegram-bot.service | gzip > /CityVote/logs.gz

# Логи с ограничением количества строк (например, последние 1000 строк)
sudo journalctl -u telegram-bot.service -n 1000 > /CityVote/recent_logs.txt

# Логи с метками времени (точное время)
sudo journalctl -u telegram-bot.service --output=short-precise > /CityVote/timestamped_logs.txt

# Логи с указанием PID (идентификаторы процессов)
sudo journalctl -u telegram-bot.service --output=with-unit > /CityVote/pid_logs.txt

# Логи без обрезки длинных строк
sudo journalctl -u telegram-bot.service --no-pager > /CityVote/full_logs.txt

# Логи, связанные с конкретным пользователем (например, root)
sudo journalctl -u telegram-bot.service _UID=0 > /CityVote/user_logs.txt