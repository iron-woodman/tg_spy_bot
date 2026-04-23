"""Тестовый скрипт для диагностики инфраструктуры бота."""
import asyncio
import os
import sys

# Force UTF-8 output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
API_TOKEN = os.getenv("API_TOKEN")
TARGET_GROUP = os.getenv("TARGET_GROUP_ID")
SESSION_NAME = os.getenv("SESSION_NAME", "session_name")


def check_network():
    """Быстрая проверка сети до Telegram."""
    print("\n[0/4] Проверка сети...")
    import socket
    try:
        socket.create_connection(("api.telegram.org", 443), timeout=10)
        print("    [OK] api.telegram.org:443 reachable")
        return True
    except Exception as e:
        print(f"    [FAIL] Cannot connect to api.telegram.org:443")
        print(f"    -> {e}")
        print(f"    -> Check VPN/proxy or firewall!")
        return False


async def check_bot_api():
    """Проверка Bot API токена."""
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    
    print("\n[1/4] Проверка Bot API...")
    try:
        bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
        me = await bot.get_me()
        print(f"    [OK] Бот авторизован: @{me.username} (ID: {me.id})")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"    [FAIL] Ошибка: {e}")
        return False


async def check_telethon_connection():
    """Проверка подключения Telethon."""
    from telethon import TelegramClient
    
    print("\n[2/4] Проверка Telethon подключения...")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH, timeout=10)
    try:
        await client.start()
        me = await client.get_me()
        print(f"    [OK] Telethon авторизован: {me.username} (ID: {me.id})")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"    [FAIL] Ошибка: {e}")
        return False


async def check_target_group():
    """Проверка доступа к целевой группе."""
    from telethon import TelegramClient
    
    print("\n[3/4] Проверка целевой группы...")
    if not TARGET_GROUP:
        print("    [FAIL] TARGET_GROUP_ID не задан в .env")
        return False
    
    print(f"    Проверяем группу: {TARGET_GROUP}")
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    try:
        await client.connect()
        
        try:
            entity = await client.get_entity(TARGET_GROUP)
            print(f"    [OK] Группа найдена: {entity.title} (ID: {entity.id})")
            await client.disconnect()
            return True
        except ValueError as e:
            print(f"    [FAIL] Группа не найдена: {e}")
            print(f"    -> Бот не имеет доступа к группе {TARGET_GROUP}")
            print(f"    -> Возможные причины:")
            print(f"       1. Группа удалена или заблокирована")
            print(f"       2. Бот исключен из группы")
            print(f"       3. Бот не добавлен в группу")
            print(f"       4. Неверный ID группы")
            await client.disconnect()
            return False
    except Exception as e:
        print(f"    [FAIL] Ошибка подключения: {e}")
        return False


async def check_keywords():
    """Проверка файлов слов."""
    print("\n[4/4] Проверка файлов слов...")
    
    files_to_check = [
        os.getenv("SLOVAR_FILE", "slovar1.txt"),
        os.getenv("MINSLOVAR_FILE", "minslovar1.txt"),
        os.getenv("KOLSLOV_FILE", "kolslov.txt"),
    ]
    
    all_ok = True
    for fpath in files_to_check:
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                count = len(f.readlines())
            print(f"    [OK] {fpath}: {count} строк")
        else:
            print(f"    [FAIL] {fpath}: файл не найден")
            all_ok = False
    
    return all_ok


async def main():
    print("=" * 50)
    print("ДИАГНОСТИКА ИНФРАСТРУКТУРЫ БОТА")
    print("=" * 50)
    
    # Network check (sync)
    results = []
    results.append(check_network())
    
    # Async checks
    results.append(await check_bot_api())
    results.append(await check_telethon_connection())
    results.append(await check_target_group())
    results.append(await check_keywords())
    
    print("\n" + "=" * 50)
    if all(results):
        print("[OK] ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    else:
        print("[FAIL] ЕСТЬ ПРОБЛЕМЫ - см. выше")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())