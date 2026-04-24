import asyncio
from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "session_name")

async def main():
    print(f"Создаю сессию для API_ID={API_ID}")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Успешно! Вы вошли как: {me.first_name} (@{me.username})")
        print(f"   ID аккаунта: {me.id}")
        
        # Проверим, есть ли доступ к каналу
        target = os.getenv("TARGET_GROUP_ID")
        if target:
            print(f"\nПроверяю доступ к каналу {target}...")
            try:
                entity = await client.get_entity(int(target))
                print(f"✅ Доступ есть! Канал: {entity.title}")
            except Exception as e:
                print(f"⚠️ Не могу найти канал: {e}")
                print("   Напишите любое сообщение от этого аккаунта в канал")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
