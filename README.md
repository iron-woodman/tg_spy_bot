# 🕵️‍♂️ TG Spy Bot

Telegram бот для автоматического мониторинга сообщений в каналах/группах через Userbot (Telethon) и управления настройками через Bot API (Aiogram).

## ✨ Основные возможности
- **Мониторинг сообщений:** Пересылает сообщения в вашу группу, если они содержат определенное количество ключевых слов.
- **Фильтрация:** Исключает сообщения с "минус-словами".
- **Удобное управление:** Добавление/удаление слов и настройка порога срабатывания через Telegram-интерфейс.
- **Безопасность:** Доступ к панели управления защищен паролем.
- **Логирование:** Полная история работы с помощью `loguru`.

## 🛠 Установка и настройка

1. **Клонируйте проект** на ваш сервер.
2. **Создайте файл `.env`** на основе существующего или шаблона:
   ```env
   API_ID=ваш_id
   API_HASH=ваш_hash
   API_TOKEN=токен_бота
   BOT_PASSWORD=ваш_пароль
   TARGET_GROUP_ID=-100123456789
   ```
3. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Запуск на VPS (Ubuntu/Debian)

Для бесперебойной работы 24/7 рекомендуется использовать `systemd`.

1. **Создайте файл сервиса:**
   ```bash
   sudo nano /etc/systemd/system/tgspy.service
   ```
2. **Вставьте следующее содержимое** (замените пути на свои):
   ```ini
   [Unit]
   Description=Telegram Spy Bot
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/root/tg_spy_bot
   ExecStart=/usr/bin/python3 bot.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
3. **Запустите и включите автозапуск:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable tgspy
   sudo systemctl start tgspy
   ```

## 📈 Логирование
Логи хранятся в папке `logs/bot.log`. При достижении 5 МБ создается архив.

---
*Разработано для эффективного мониторинга.*
