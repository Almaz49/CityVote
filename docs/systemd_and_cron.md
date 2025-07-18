# 🛠 Настройка systemd и cron для Telegram-бота CityVote

## 📌 Описание

Этот документ описывает, как настроить автоматический запуск и обновление Telegram-ботов на удалённом сервере с использованием:
- `systemd` — для управления процессами и автозапуска ботов
- `cron` — для автоматического обновления кода из репозитория и перезапуска ботов

---

## 🧰 Предварительные требования

Перед началом убедитесь, что на сервере установлены:
- `git`
- `python3` и `venv`
- Репозиторий `CityVote` находится в директории `/CityVote/`
- Конфигурации ботов находятся в `/CityVote/configs/*.env`

---

## ⚙️ 1. Настройка systemd для многоботового режима

### 1.1. Создание шаблонного сервиса

Создайте файл шаблона systemd:

```bash
sudo nano /etc/systemd/system/telegram-bot@.service
```

#### Вставьте следующее содержимое:
```
[Unit]
Description=Telegram Bot Service for %i
After=network.target

[Service]
User=root
WorkingDirectory=/CityVote/
ExecStart=/CityVote/venv/bin/python -u /CityVote/run_Linux.py --bot-name=%i
Restart=always
RestartSec=5
Environment="BOT_INSTANCE=%i"
StandardOutput=append:/var/log/telegram-bot-%i.log
StandardError=append:/var/log/telegram-bot-%i.log

[Install]
WantedBy=multi-user.target
```

> %i — это переменная, которая заменяется на имя бота, например: bot01, bot02.

### 1.2. Перезагрузите systemd
```
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
```

## ▶️ 2. Запуск и управление ботами

### Запуск бота
```
sudo systemctl start telegram-bot@bot01.service
```
### Автозапуск бота при старте системы
```
sudo systemctl start telegram-bot@bot01.service
```
### Проверка состояния бота
```
sudo systemctl status telegram-bot@bot01.service
```
### Просмотр логов
```
journalctl -u telegram-bot@bot01.service --since "5 minutes ago"
```
### или
```
tail -f /var/log/telegram-bot-bot01.log
```
## 🔄 3. Настройка cron для автоматического обновления и перезапуска ботов

### 3.1. Откройте редактор crontab
```
crontab -e
```
### 3.2. Добавьте новую задачу
```
*/5 * * * * cd /CityVote/ && git pull origin baza | grep -q "Already up to date" || { echo "[$(date)] Перезапуск всех ботов..." >> /var/log/bot-restart.log; systemctl list-units --type=service | grep 'telegram-bot@.*\.service' | awk '{print $1}' | xargs -r systemctl restart; }
```
#### Сохраните и выйдите из редактора

Эта задача:

- Каждые 5 минут проверяет обновления в репозитории
- Если изменения найдены:
- Логирует факт перезапуска
- Перезапускает все активные боты, запущенные через telegram-bot@*.service

### 3.3. Перезапустите службу cron
```
sudo systemctl restart cron
```
## 📋 4. Полезные команды
#### Просмотр всех запущенных ботов
```
systemctl list-units --type=service | grep telegram
```
#### Остановка бота
```
systemctl stop telegram-bot@bot01.service
```
#### Отключение автозапуска
```
systemctl disable telegram-bot@bot01.service
```
#### Просмотр логов
```
journalctl -u telegram-bot@bot01.service --since "5 minutes ago"
```
#### Проверка логов файла
```
tail -f /var/log/telegram-bot-bot01.log
```
#### Перезапуск cron
```
systemctl restart cron
```

## 🧼 5. Очистка старых сервисов и процессов

#### Если вы переходите с одноботового режима (telegram-bot.service):
```
sudo systemctl stop telegram-bot.service
sudo systemctl disable telegram-bot.service
sudo rm /etc/systemd/system/telegram-bot.service
sudo systemctl daemon-reload
```
#### Также убейте оставшиеся процессы:
```
ps aux | grep python | grep main.py
kill <PID>
```
## ✅ 6. Преимущества такой настройки

* Поддержка нескольких ботов с разными конфигами
* Автоматическое обновление кода и перезапуск
* Логирование каждого бота отдельно
* Стабильность и контроль через systemd
* Простота масштабирования — добавление новых ботов

## 📌 7. Возможные проблемы и решения

#### TelegramConflictError
Убедитесь, что бот запущен только один раз

#### Бот не запускается
Проверьте права на файлы и наличие .env

#### Cron не работает
Проверьте вывод journalctl -u systemd-timers

#### Ошибка BOT_INSTANCE
Убедитесь, что имя .env совпадает с именем сервиса


📌 Автор: @Almaz49
📅 Дата: 2025-07-18
📦 Проект: CityVote https://github.com/Almaz49/CityVote