#!/usr/bin/env python3
import sys
from pathlib import Path
try:
    import aiogram
    import yt_dlp
except ImportError:
    print("❌ Ошибка: Не установлены необходимые пакеты!")
    print("Установите: pip install -r requirements.txt")
    sys.exit(1)
if not Path(".env").exists() and not Path(".env.local").exists():
    print("⚠️ Примечание: Используется BOT_TOKEN из bot.py")
try:
    from bot import main, BOT_TOKEN
except ImportError as e:
    print(f"❌ Ошибка при импорте: {e}")
    sys.exit(1)
if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ Ошибка: BOT_TOKEN не установлен!")
    print("1. Откройте bot.py")
    print("2. Найдите BOT_TOKEN = \"YOUR_BOT_TOKEN_HERE\"")
    print("3. Замените на ваш токен от @BotFather")
    sys.exit(1)
if __name__ == "__main__":
    print("=" * 60)
    print("🎬 Video Downloader Bot")
    print("=" * 60)
    print("✅ Конфигурация загружена")
    print("📱 Бот запускается...")
    print("=" * 60)
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
