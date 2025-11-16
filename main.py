#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
import time
from datetime import datetime

# Добавляем путь для импорта core
sys.path.append(os.path.dirname(__file__))

def setup_logging():
    """Настройка логирования"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"kbot_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_config():
    """Проверяет наличие конфигурации"""
    if not os.path.exists("config.py"):
        print("❌ Файл config.py не найден!")
        print("💡 Запустите setup.py для настройки:")
        print("   python setup.py")
        return False
    return True

async def check_updates_on_start():
    """Проверяет обновления при запуске бота"""
    try:
        from utils.updater import check_for_updates
        update_available, latest_version = await check_for_updates()
        if update_available:
            logger = logging.getLogger("KbotLauncher")
            logger.info(f"🔔 Доступно обновление: v{latest_version}")
            logger.info("💡 Используйте .update для установки или .checkupdate для информации")
            return True
        return False
    except ImportError as e:
        logging.getLogger("KbotLauncher").warning(f"⚠️ Модуль проверки обновлений не найден: {e}")
        return False

async def main():
    try:
        setup_logging()
        logger = logging.getLogger("KbotLauncher")
        
        if not check_config():
            sys.exit(1)
        
        # Создаем необходимые директории
        os.makedirs("modules", exist_ok=True)
        os.makedirs("backups", exist_ok=True)
        
        # Конвертируем старые модули
        try:
            from utils.module_converter import convert_all_old_modules
            converted = convert_all_old_modules()
            if converted > 0:
                logger.info(f"🔄 Автоматически сконвертировано {converted} модулей")
        except ImportError as e:
            logger.warning(f"⚠️ Модуль конвертации не найден: {e}")
        
        # Проверяем обновления при запуске
        await check_updates_on_start()
        
        from core.bot import Kbot
        bot = Kbot()
        bot.start_time = time.time()
        
        logger.info("🚀 Запуск Kbot...")
        await bot.start()
        
    except KeyboardInterrupt:
        logging.info("⏹️ Остановка Kbot по запросу пользователя")
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
