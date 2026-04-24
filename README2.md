# 🕵️‍♂️ TG Spy Bot

Telegram бот для автоматического мониторинга сообщений в каналах/группах через Userbot (Telethon) и управления настройками через Bot API (Aiogram).

## ✨ Основные возможности
- **Мониторинг сообщений:** Пересылает сообщения в вашу группу/канал, если они содержат определенное количество ключевых слов.
- **Фильтрация:** Исключает сообщения с "минус-словами" (стоп-словами).
- **Удобное управление:** Добавление/удаление слов и настройка порога срабатывания через Telegram-интерфейс (кнопки).
- **Безопасность:** Доступ к панели управления защищен паролем.
- **Логирование:** Полная история работы с помощью `loguru` (ротация файлов каждые 5 МБ).
- **Прокси:** Поддержка SOCKS5 прокси для обхода блокировок (опционально).

## 🛠 Установка и настройка

### 1. Требования
- Python 3.8+
- VPS (рекомендуется вне РФ для избежания блокировок, либо с настроенным прокси)
- Аккаунт Telegram (Userbot) для мониторинга
- Бот Telegram (для панели управления)

### 2. Установка
Клонируйте репозиторий и установите зависимости:

```bash
git clone <your-repo-url>
cd tg_spy_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настройка `.env`
Создайте файл `.env` в корне проекта:

```env
# Обязательные параметры
API_ID=ваш_id                # из my.telegram.org/apps
API_HASH=ваш_hash            # из my.telegram.org/apps
API_TOKEN=токен_бота         # от @BotFather
SESSION_NAME=session_name    # имя файла сессии user-бота

# Куда пересылать сообщения
TARGET_GROUP_ID=-100123456789   # или username канала (например: cloning_channel)

# Пароль для входа в панель бота
BOT_PASSWORD=ваш_секретный_пароль

# Прокси (опционально, для VPS с блокировками)
USE_PROXY=false
PROXY_URL=socks5://хост:порт   # например socks5://45.95.233.45:4153
```

#### ☝️ Важные замечания:
- **`TARGET_GROUP_ID`** можно указать как числовой ID (с минусом) или как username канала (без `@`).
- Для мониторинга используется **Userbot** (авторизация по номеру телефона). При первом запуске Telethon запросит номер телефона и код подтверждения.

### 4. Файлы словарей
В папке с ботом должны лежать текстовые файлы (по одному слову на строку):
- `slovar1.txt` — список ключевых слов.
- `minslovar1.txt` — список стоп-слов (исключают сообщение при любом совпадении).
- `kolslov.txt` — порог срабатывания (целое число, например `1`).

Пример:
```bash
echo -e "скидка\nакция\nкупить" > slovar1.txt
echo -e "спам\nреклама" > minslovar1.txt
echo "2" > kolslov.txt   # нужно минимум 2 ключевых слова для срабатывания
```

### 5. Исправление проблемы: "Server closed the connection"
Если на вашем VPS блокируется протокол MTProto (ошибка при подключении Telethon), обязательно добавьте в код правильное подключение:

```python
from telethon import TelegramClient
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged

client = TelegramClient(
    SESSION_NAME, API_ID, API_HASH,
    connection=ConnectionTcpAbridged  # критически важно!
)
```

Или настройте прокси (см. `.env`).

## 🚀 Запуск на VPS (Ubuntu/Debian)

### Ручной запуск (тестирование)
```bash
python3 bot_final.py
```

### Автоматический запуск через systemd (рекомендуется)

1. **Создайте файл сервиса:**
   ```bash
   sudo nano /etc/systemd/system/tgspy.service
   ```

2. **Вставьте следующее (замените пути на свои):**
   ```ini
   [Unit]
   Description=Telegram Spy Bot
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/bot/tg_spy_bot   # <-- ваш путь
   ExecStart=/root/bot/tg_spy_bot/venv/bin/python3 /root/bot/tg_spy_bot/bot_final.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Запустите и включите автозагрузку:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable tgspy
   sudo systemctl start tgspy
   sudo systemctl status tgspy   # проверить, что всё OK
   ```

4. **Просмотр логов сервиса:**
   ```bash
   sudo journalctl -u tgspy -f
   ```

## 🎮 Управление ботом

1. Найдите в Telegram вашего бота (токен которого в `.env`).
2. Отправьте `/start`.
3. Введите пароль (`BOT_PASSWORD`).
4. Используйте кнопки:
   - **Ключевые слова** — добавить/удалить.
   - **Минус слова** — стоп-слова.
   - **Настройки** — изменить порог срабатывания.

## 📁 Структура проекта
```
tg_spy_bot/
├── bot_final.py          # основной скрипт
├── test_bot.py           # диагностика подключения
├── show_dialogs.py       # просмотр доступных чатов
├── .env                  # конфигурация (не в git)
├── slovar1.txt
├── minslovar1.txt
├── kolslov.txt
├── logs/
│   └── bot.log           # логи работы
├── session_name.session  # файл сессии user-бота
├── requirements.txt
└── README.md
```

## 🛠 Диагностика проблем

Если бот не видит ваш канал, выполните:
```bash
python3 show_dialogs.py
```

Это покажет все чаты, доступные user-боту, и их реальные ID.

### Типичные ошибки и решения:

| Ошибка | Решение |
|--------|---------|
| `Server closed the connection` | VPS блокирует MTProto — используйте `ConnectionTcpAbridged` или прокси |
| `Cannot find any entity` | Userbot не добавлен в канал → отправьте сообщение от user-бота в канал |
| `Неверный пароль` | Проверьте `BOT_PASSWORD` в `.env` |
| `Файлы slovar1.txt не найдены` | Создайте их с нужными словами |

## 📈 Логирование
Логи хранятся в папке `logs/bot.log`. При достижении 5 МБ создается архив с ротацией.

## 📜 Лицензия
MIT

---
*Разработано для эффективного мониторинга. Работает на любом VPS с корректным подключением к Telegram.*
