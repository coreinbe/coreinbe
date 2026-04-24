import asyncio
import logging
import os
import threading
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from monitor import CoreInBeMonitor

# Настройки (ПРОПИШИТЕ ВАШИ ДАННЫЕ ЗДЕСЬ)
BOT_TOKEN = "8642621259:AAHpsekjW3WSGr6FZ6Zt3nsGb-VFpJFkQbo"
ADMIN_ID = "8075875058"

# Отключаем лишние логи
logging.basicConfig(level=logging.ERROR)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализируем монитор СРАЗУ при запуске программы
print("[SYSTEM] Инициализация ИИ...")
monitor_stop_event = threading.Event()
monitor_instance = CoreInBeMonitor(stop_event=monitor_stop_event)

monitor_thread = None
monitor_running = False

def is_admin(user_id):
    return str(user_id) == ADMIN_ID

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    if not is_admin(message.from_user.id): return 
    await message.answer("🚀 CoreInBe NextGen АКТИВИРОВАНА!\n\nКамера уже работает. Нарушения будут приходить сюда.")

async def send_violation_alert(image_path: str, violation_type: str, timestamp: datetime):
    try:
        photo = FSInputFile(image_path)
        await bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=photo, 
            caption=f"🚨 {violation_type}\nВремя: {timestamp.strftime('%H:%M:%S')}"
        )
    except Exception as e:
        print(f"[ERROR] Ошибка отправки: {e}")

async def start_camera_instantly():
    """Мгновенный запуск камеры в отдельном потоке"""
    global monitor_thread, monitor_running
    print("[SYSTEM] МГНОВЕННЫЙ ЗАПУСК КАМЕРЫ...")
    monitor_stop_event.clear()
    monitor_instance.set_alert_function(send_violation_alert, asyncio.get_event_loop())
    
    monitor_thread = threading.Thread(target=monitor_instance.run, args=(0,))
    monitor_thread.daemon = True
    monitor_thread.start()
    monitor_running = True

async def main() -> None:
    # СБРОС ВСЕХ ПРЕДЫДУЩИХ СЕССИЙ
    print("[SYSTEM] Очистка старых сессий Telegram...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    # МГНОВЕННЫЙ ЗАПУСК КАМЕРЫ ПРИ СТАРТЕ
    await start_camera_instantly()
    
    print("[SYSTEM] Бот в сети. Камера работает. Жду нарушений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if not BOT_TOKEN or not ADMIN_ID:
        print("[ERROR] Проверьте токен и ID в main.py")
        exit(1)
    asyncio.run(main())
