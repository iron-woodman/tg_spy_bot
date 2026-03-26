import asyncio
import os
import re
from typing import List

import aiofiles
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from loguru import logger
from telethon import TelegramClient, events

# Загрузка переменных окружения
load_dotenv()

# Автоматическое создание папки для логов
os.makedirs("logs", exist_ok=True)

# Настройка логирования
logger.add("logs/bot.log", rotation="5 MB", level="INFO", encoding="utf-8")

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
API_TOKEN = os.getenv("API_TOKEN")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "123")
TARGET_GROUP = os.getenv("TARGET_GROUP_ID")
SESSION_NAME = os.getenv("SESSION_NAME", "session_name")

SLOVAR_FILE = os.getenv("SLOVAR_FILE", "slovar1.txt")
MINSLOVAR_FILE = os.getenv("MINSLOVAR_FILE", "minslovar1.txt")
KOLSLOV_FILE = os.getenv("KOLSLOV_FILE", "kolslov.txt")

# FSM Состояния
class BotStates(StatesGroup):
    auth = State()
    add_keyword = State()
    add_minword = State()
    set_threshold = State()


class KeywordManager:
    """Класс для управления списками слов и настройками."""
    def __init__(self):
        self.keywords: List[str] = []
        self.minwords: List[str] = []
        self.threshold: int = 1

    async def load_all(self):
        """Асинхронная загрузка данных из файлов."""
        try:
            if os.path.exists(SLOVAR_FILE):
                async with aiofiles.open(SLOVAR_FILE, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    self.keywords = [line.strip() for line in content.splitlines() if line.strip()]
            
            if os.path.exists(MINSLOVAR_FILE):
                async with aiofiles.open(MINSLOVAR_FILE, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    self.minwords = [line.strip() for line in content.splitlines() if line.strip()]

            if os.path.exists(KOLSLOV_FILE):
                async with aiofiles.open(KOLSLOV_FILE, mode='r', encoding='utf-8') as f:
                    line = await f.read()
                    self.threshold = int(line.strip()) if line.strip() else 1
            
            logger.info(f"Данные загружены: {len(self.keywords)} кл. слов, {len(self.minwords)} мин. слов, порог: {self.threshold}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")

    async def save_keywords(self):
        async with aiofiles.open(SLOVAR_FILE, mode='w', encoding='utf-8') as f:
            await f.write("\n".join(self.keywords))

    async def save_minwords(self):
        async with aiofiles.open(MINSLOVAR_FILE, mode='w', encoding='utf-8') as f:
            await f.write("\n".join(self.minwords))

    async def save_threshold(self):
        async with aiofiles.open(KOLSLOV_FILE, mode='w', encoding='utf-8') as f:
            await f.write(str(self.threshold))

    def check_message(self, text: str) -> bool:
        """Проверка сообщения на соответствие фильтрам."""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Проверка на минус-слова (сразу выходим, если нашли)
        for mw in self.minwords:
            if mw.lower() in text_lower:
                return False

        # Подсчет вхождений ключевых слов
        count = sum(1 for kw in self.keywords if kw.lower() in text_lower)
        return count >= self.threshold

# Инициализация
manager = KeywordManager()
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

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

# ================== CALLBACKS ==================

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

# ================== FSM INPUTS ==================

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

# ================== TELETHON EVENTS ==================

@client.on(events.NewMessage())
async def event_handler(event):
    if not event.message or not event.message.message:
        return
        
    text = event.message.message
    if manager.check_message(text):
        try:
            # Пересылаем сообщение в целевую группу
            await client.forward_messages(TARGET_GROUP, event.message)
            logger.info(f"Найдено совпадение! Сообщение переслано в {TARGET_GROUP}")
        except Exception as e:
            logger.error(f"Ошибка при пересылке: {e}")

# ================== MAIN ==================

async def main():
    logger.info("Запуск бота...")
    
    # Загружаем данные
    await manager.load_all()

    # Запускаем Telethon
    try:
        await client.start()
        logger.info("Telethon клиент авторизован")
    except Exception as e:
        logger.critical(f"Ошибка авторизации Telethon: {e}")
        return

    # Запускаем polling aiogram
    logger.info("Запуск Telegram Bot API...")
    polling_task = asyncio.create_task(dp.start_polling(bot))

    # Работаем, пока Telethon не отключится
    try:
        await client.run_until_disconnected()
    finally:
        await polling_task

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
