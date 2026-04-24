import asyncio
import os
import signal
import sys
from typing import List
from dotenv import load_dotenv
from loguru import logger
import aiofiles
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient, events
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged

load_dotenv()

os.makedirs("logs", exist_ok=True)
logger.add("logs/bot.log", rotation="5 MB", level="INFO", encoding="utf-8")

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
API_TOKEN = os.getenv("API_TOKEN")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "123")
TARGET_GROUP = os.getenv("TARGET_GROUP_ID")
SESSION_NAME = os.getenv("SESSION_NAME", "session_name")

SLOVAR_FILE = os.getenv("SLOVAR_FILE", "slovar1.txt")
MINSLOVAR_FILE = os.getenv("MINSLOVAR_FILE", "minslovar1.txt")
KOLSLOV_FILE = os.getenv("KOLSLOV_FILE", "kolslov.txt")

# Глобальные переменные для graceful shutdown
shutdown_event = asyncio.Event()
polling_task = None
telethon_task = None

def get_target():
    if TARGET_GROUP is None:
        return None
    try:
        return int(TARGET_GROUP)
    except ValueError:
        return TARGET_GROUP

client = TelegramClient(
    SESSION_NAME, 
    API_ID, 
    API_HASH,
    connection=ConnectionTcpAbridged
)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

class BotStates(StatesGroup):
    auth = State()
    add_keyword = State()
    add_minword = State()
    set_threshold = State()

class KeywordManager:
    def __init__(self):
        self.keywords: List[str] = []
        self.minwords: List[str] = []
        self.threshold: int = 1

    async def load_all(self):
        try:
            if os.path.exists(SLOVAR_FILE):
                async with aiofiles.open(SLOVAR_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.keywords = [line.strip() for line in content.splitlines() if line.strip()]
            
            if os.path.exists(MINSLOVAR_FILE):
                async with aiofiles.open(MINSLOVAR_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.minwords = [line.strip() for line in content.splitlines() if line.strip()]

            if os.path.exists(KOLSLOV_FILE):
                async with aiofiles.open(KOLSLOV_FILE, 'r', encoding='utf-8') as f:
                    line = await f.read()
                    self.threshold = int(line.strip()) if line.strip() else 1
            
            logger.info(f"Данные загружены: {len(self.keywords)} кл. слов, {len(self.minwords)} мин. слов, порог: {self.threshold}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")

    async def save_keywords(self):
        async with aiofiles.open(SLOVAR_FILE, 'w', encoding='utf-8') as f:
            await f.write("\n".join(self.keywords))

    async def save_minwords(self):
        async with aiofiles.open(MINSLOVAR_FILE, 'w', encoding='utf-8') as f:
            await f.write("\n".join(self.minwords))

    async def save_threshold(self):
        async with aiofiles.open(KOLSLOV_FILE, 'w', encoding='utf-8') as f:
            await f.write(str(self.threshold))

    def check_message(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        for mw in self.minwords:
            if mw.lower() in text_lower:
                return False
        count = sum(1 for kw in self.keywords if kw.lower() in text_lower)
        return count >= self.threshold

manager = KeywordManager()

# ================== AIOGRAM HANDLERS ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.auth)
    await message.answer("🔐 Введите пароль для доступа к панели управления:")

@dp.message(StateFilter(BotStates.auth))
async def check_pass(message: types.Message, state: FSMContext):
    if message.text == BOT_PASSWORD:
        kb = [
            [types.KeyboardButton(text="Ключевые слова"), types.KeyboardButton(text="Минус слова")],
            [types.KeyboardButton(text="Настройки")]
        ]
        markup = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer("✅ Доступ разрешен. Выберите раздел:", reply_markup=markup)
        await state.clear()
        logger.info(f"Успешная авторизация пользователя {message.from_user.id}")
    else:
        await message.answer("❌ Неверный пароль. Попробуйте снова.")

@dp.message(F.text == "Ключевые слова")
async def show_keywords(message: types.Message):
    builder = InlineKeyboardBuilder()
    for i, kw in enumerate(manager.keywords):
        builder.row(
            types.InlineKeyboardButton(text=kw, callback_data=f"noop"),
            types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_kw_{i}")
        )
    builder.row(types.InlineKeyboardButton(text="➕ Добавить", callback_data="add_kw"))
    await message.answer("📝 <b>Список ключевых слов:</b>" if manager.keywords else "Список пуст", reply_markup=builder.as_markup())

@dp.message(F.text == "Минус слова")
async def show_minwords(message: types.Message):
    builder = InlineKeyboardBuilder()
    for i, mw in enumerate(manager.minwords):
        builder.row(
            types.InlineKeyboardButton(text=mw, callback_data=f"noop"),
            types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_mw_{i}")
        )
    builder.row(types.InlineKeyboardButton(text="➕ Добавить", callback_data="add_mw"))
    await message.answer("🚫 <b>Список минус-слов:</b>" if manager.minwords else "Список пуст", reply_markup=builder.as_markup())

@dp.message(F.text == "Настройки")
async def show_settings(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="⚙️ Изменить порог слов", callback_data="set_thr"))
    await message.answer(f"📊 <b>Текущие настройки:</b>\n\nПорог срабатывания: {manager.threshold} слов(а)", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("del_kw_"))
async def del_keyword(call: types.CallbackQuery):
    idx = int(call.data.split("_")[-1])
    if 0 <= idx < len(manager.keywords):
        removed = manager.keywords.pop(idx)
        await manager.save_keywords()
        logger.info(f"Удалено кл. слово: {removed}")
        await call.answer("Удалено")
        await show_keywords(call.message)

@dp.callback_query(F.data.startswith("del_mw_"))
async def del_minword(call: types.CallbackQuery):
    idx = int(call.data.split("_")[-1])
    if 0 <= idx < len(manager.minwords):
        removed = manager.minwords.pop(idx)
        await manager.save_minwords()
        logger.info(f"Удалено минус-слово: {removed}")
        await call.answer("Удалено")
        await show_minwords(call.message)

@dp.callback_query(F.data == "add_kw")
async def prompt_add_kw(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.add_keyword)
    await call.message.answer("Введите новое ключевое слово:")
    await call.answer()

@dp.callback_query(F.data == "add_mw")
async def prompt_add_mw(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.add_minword)
    await call.message.answer("Введите новое минус-слово:")
    await call.answer()

@dp.callback_query(F.data == "set_thr")
async def prompt_set_thr(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.set_threshold)
    await call.message.answer("Введите число (сколько слов должно совпасть):")
    await call.answer()

@dp.message(StateFilter(BotStates.add_keyword))
async def process_add_kw(message: types.Message, state: FSMContext):
    manager.keywords.append(message.text)
    await manager.save_keywords()
    logger.info(f"Добавлено кл. слово: {message.text}")
    await message.answer(f"✅ Слово '{message.text}' добавлено.")
    await state.clear()

@dp.message(StateFilter(BotStates.add_minword))
async def process_add_mw(message: types.Message, state: FSMContext):
    manager.minwords.append(message.text)
    await manager.save_minwords()
    logger.info(f"Добавлено минус-слово: {message.text}")
    await message.answer(f"✅ Минус-слово '{message.text}' добавлено.")
    await state.clear()

@dp.message(StateFilter(BotStates.set_threshold))
async def process_set_thr(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        manager.threshold = int(message.text)
        await manager.save_threshold()
        logger.info(f"Порог изменен на: {manager.threshold}")
        await message.answer(f"✅ Порог срабатывания изменен на {manager.threshold}.")
        await state.clear()
    else:
        await message.answer("⚠ Пожалуйста, введите число.")

# ================== TELETHON HANDLER ==================
@client.on(events.NewMessage)
async def event_handler(event):
    if not event.message or not event.message.message:
        return
    
    # Не обрабатываем сообщения из самого целевого канала
    if str(event.message.chat_id) == str(get_target()):
        return
        
    text = event.message.message
    
    if manager.check_message(text):
        try:
            target = get_target()
            if target:
                await client.forward_messages(target, event.message)
                logger.info(f"✅ Переслано сообщение из {event.chat_id} в {target}")
                logger.debug(f"   Текст: {text[:100]}...")
            else:
                logger.error("❌ TARGET_GROUP не задан")
        except Exception as e:
            logger.error(f"❌ Ошибка при пересылке: {e}")

# ================== GRACEFUL SHUTDOWN ==================
async def shutdown(signum=None, frame=None):
    """Корректное завершение работы бота"""
    global polling_task, telethon_task
    
    if shutdown_event.is_set():
        return
        
    logger.info(f"\n🛑 Получен сигнал остановки. Завершаем работу...")
    shutdown_event.set()
    
    # Останавливаем polling Aiogram, если он запущен
    if polling_task and not polling_task.done():
        logger.info("   ⏹️ Останавливаем Aiogram...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    # Отключаем Telethon клиент, если он запущен
    if telethon_task and not telethon_task.done():
        logger.info("   ⏹️ Отключаем Telethon...")
        telethon_task.cancel()
        try:
            await telethon_task
        except asyncio.CancelledError:
            pass
    
    # Дополнительная очистка
    try:
        await client.disconnect()
        logger.info("   ✅ Telethon отключён")
    except:
        pass
    
    try:
        await bot.session.close()
        logger.info("   ✅ Сессия бота закрыта")
    except:
        pass
    
    logger.info("✅ Бот успешно остановлен")
    
    # Останавливаем event loop
    loop = asyncio.get_running_loop()
    loop.stop()

def setup_signal_handlers():
    """Настройка обработчиков сигналов"""
    loop = asyncio.get_running_loop()
    
    for sig in [signal.SIGINT, signal.SIGTERM]:
        loop.add_signal_handler(
            sig, 
            lambda s=sig: asyncio.create_task(shutdown(s))
        )

# ================== MAIN ==================
async def main():
    global polling_task, telethon_task
    
    logger.info("🚀 Запуск бота...")
    
    # Настраиваем обработчики сигналов
    setup_signal_handlers()
    logger.info("✅ Обработчики сигналов настроены (SIGTERM, SIGINT)")
    
    # Загружаем словари
    await manager.load_all()
    
    # Подключаем Telethon
    try:
        await client.start()
        me = await client.get_me()
        logger.info(f"✅ Telethon подключен: {me.first_name} (@{me.username})")
        
        target = get_target()
        if target:
            try:
                entity = await client.get_entity(target)
                logger.info(f"✅ Целевая группа: {entity.title}")
            except Exception as e:
                logger.error(f"⚠️ Группа {target} не найдена: {e}")
        else:
            logger.warning("⚠️ TARGET_GROUP не задан в .env")
            
    except Exception as e:
        logger.critical(f"❌ Ошибка подключения Telethon: {e}")
        return
    
    logger.info("🤖 Запуск Aiogram...")
    logger.info("💡 Для остановки нажмите Ctrl+C или выполните systemctl stop tg-spy-bot")
    
    # Запускаем задачи
    polling_task = asyncio.create_task(dp.start_polling(bot))
    telethon_task = asyncio.create_task(client.run_until_disconnected())
    
    # Ждём сигнала остановки
    try:
        await shutdown_event.wait()
    except KeyboardInterrupt:
        pass
    
    # Завершаем задачи
    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    if telethon_task and not telethon_task.done():
        telethon_task.cancel()
        try:
            await telethon_task
        except asyncio.CancelledError:
            pass
    
    logger.info("👋 Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"❌ Непредвиденная ошибка: {e}")
        sys.exit(1)