#!/usr/bin/env python3
import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import getpass

def clear_screen():
    """Очищает экран терминала"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Печатает баннер Kbot"""
    banner = """
╦ ╦┌─┐┬  ┌─┐
║ ║├┤ │  ├┤ 
╚═╝└─┘┴─┘└─┘
🤖 Модульный Telegram Userbot
    """
    print(banner)

def setup_directories():
    """Создает необходимые директории"""
    directories = ['modules', 'backups', 'logs', 'configs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    print("✅ Созданы необходимые директории")

def get_api_credentials():
    """Получает API credentials от пользователя"""
    print("\n🔐 Получение API данных")
    print("=" * 40)
    print("1. Перейдите на https://my.telegram.org")
    print("2. Войдите в свой аккаунт")
    print("3. Перейдите в 'API Development Tools'")
    print("4. Создайте новое приложение")
    print("5. Скопируйте API ID и API Hash\n")
    
    while True:
        api_id = input("Введите API ID: ").strip()
        if api_id.isdigit():
            break
        print("❌ API ID должен быть числом! Попробуйте снова.")
    
    api_hash = input("Введите API Hash: ").strip()
    while not api_hash:
        print("❌ API Hash не может быть пустым!")
        api_hash = input("Введите API Hash: ").strip()
    
    return int(api_id), api_hash

async def setup_telegram_account(api_id, api_hash):
    """Настраивает Telegram аккаунт"""
    print("\n📱 Настройка Telegram аккаунта")
    print("=" * 40)
    
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    try:
        print("🔄 Подключаемся к Telegram...")
        await client.start()
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        
        print(f"\n✅ Успешная авторизация!")
        print(f"👤 Имя: {me.first_name}")
        if me.last_name:
            print(f"👤 Фамилия: {me.last_name}")
        if me.username:
            print(f"📱 Username: @{me.username}")
        print(f"🆔 ID: {me.id}")
        
        # Получаем строку сессии
        session_string = client.session.save()
        
        return me, session_string
        
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return None, None
    finally:
        await client.disconnect()

def create_config(api_id, api_hash, session_string, user_info):
    """Создает конфигурационный файл"""
    config_content = f'''# Конфигурация Kbot
# Автоматически сгенерировано setup.py

# Обязательные настройки
api_id = {api_id}
api_hash = '{api_hash}'
session_string = '{session_string}'
session_name = 'session_kbot'

# Настройки пользователя
admin_id = {user_info.id}  # Ваш Telegram ID
user_name = '{user_info.first_name}'  # Ваше имя

# Настройки бота
command_prefix = '.'  # Префикс команд
enable_backups = True  # Автоматические бэкапы модулей
backup_count = 5  # Количество хранимых бэкапов

# Настройки логирования
log_level = 'INFO'  # Уровень логирования: DEBUG, INFO, WARNING, ERROR
log_to_file = True  # Сохранять логи в файл

print("✅ Конфигурация создана!")
'''

    with open('config.py', 'w', encoding='utf-8') as f:
        f.write(config_content)

def create_env_example():
    """Создает пример .env файла"""
    env_example = '''# .env.example - пример конфигурации через переменные окружения
# Скопируйте этот файл в .env и заполните своими данными

# Обязательные настройки (получите на my.telegram.org)
KBOT_API_ID=your_api_id_here
KBOT_API_HASH=your_api_hash_here

# Опциональные настройки
KBOT_SESSION_STRING=your_session_string_here
KBOT_ADMIN_ID=your_telegram_id_here
KBOT_COMMAND_PREFIX=.
KBOT_ENABLE_BACKUPS=true
'''

    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_example)

def main():
    """Основная функция настройки"""
    try:
        clear_screen()
        print_banner()
        
        # Проверяем, существует ли уже конфигурация
        if os.path.exists('config.py'):
            response = input("📁 Конфигурация уже существует. Перезаписать? (y/N): ").strip().lower()
            if response != 'y':
                print("ℹ️ Настройка отменена.")
                return
        
        # Создаем директории
        setup_directories()
        
        # Получаем API credentials
        api_id, api_hash = get_api_credentials()
        
        # Настраиваем Telegram аккаунт
        print("\n🔄 Настраиваем подключение к Telegram...")
        user_info, session_string = asyncio.run(setup_telegram_account(api_id, api_hash))
        
        if not user_info or not session_string:
            print("❌ Не удалось настроить Telegram аккаунт")
            return
        
        # Создаем конфигурацию
        create_config(api_id, api_hash, session_string, user_info)
        
        # Создаем пример .env файла
        create_env_example()
        
        # Финальное сообщение
        print(f"\n🎉 Настройка Kbot завершена успешно!")
        print("=" * 50)
        print("📁 Созданные файлы:")
        print("   • config.py - основная конфигурация")
        print("   • .env.example - пример для продвинутой настройки")
        print("   • modules/ - папка для модулей")
        print("   • backups/ - папка для бэкапов")
        print("   • logs/ - папка для логов")
        
        print("\n🚀 Запуск бота:")
        print("   python main.py")
        
        print("\n📚 Основные команды:")
        print("   .help - список всех команд")
        print("   .modules - список модулей")
        print("   .klm - установить модуль (ответ на .py файл)")
        print("   .kun <имя> - удалить модуль")
        
        print("\n🔒 Безопасность:")
        print("   • API данные сохранены в config.py")
        print("   • config.py добавлен в .gitignore")
        print("   • Сессия зашифрована и хранится локально")
        
        print("\n💡 Следующие шаги:")
        print("   1. Запустите: python main.py")
        print("   2. Используйте .klm для установки модулей")
        print("   3. Создавайте свои модули в папке modules/")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Настройка прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        print("💡 Если проблема повторяется, создайте issue на GitHub")

if __name__ == "__main__":
    main()
