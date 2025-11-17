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
🤖 Kbot 3.0 - Модульный Telegram Userbot
🛡️  С встроенной системой безопасности
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
    """Создает конфигурационный файл с полной информацией"""
    config_content = f'''# Конфигурация Kbot 3.0
# Автоматически сгенерировано setup.py

# Обязательные настройки
api_id = {api_id}
api_hash = '{api_hash}'
session_string = '{session_string}'
session_name = 'session_kbot'

# Настройки пользователя
admin_id = {user_info.id}  # Ваш Telegram ID
chat_id = {user_info.id}   # ID чата для уведомлений (автоматически)
user_name = '{user_info.first_name}'  # Ваше имя

# Настройки бота
command_prefix = '.'  # Префикс команд
enable_backups = True  # Автоматические бэкапы модулей
backup_count = 5  # Количество хранимых бэкапов

# Уведомления
enable_startup_notification = False  # Уведомление о запуске бота
enable_security_notifications = False  # Уведомления о попытках доступа

# Настройки безопасности
enable_security = True  # Глобальная система безопасности

# Настройки логирования
log_level = 'INFO'  # Уровень логирования: DEBUG, INFO, WARNING, ERROR
log_to_file = True  # Сохранять логи в файл

print("✅ Конфигурация Kbot 3.0 создана!")
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
KBOT_CHAT_ID=your_chat_id_here
KBOT_COMMAND_PREFIX=.
KBOT_ENABLE_BACKUPS=true
KBOT_ENABLE_SECURITY=true
KBOT_ENABLE_STARTUP_NOTIFICATION=false
KBOT_ENABLE_SECURITY_NOTIFICATIONS=false
'''

    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_example)

def update_existing_config():
    """Обновляет существующий config.py добавляя недостающие поля"""
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated = False
        
        # Добавляем chat_id если его нет
        if 'chat_id =' not in content:
            # Ищем admin_id и добавляем chat_id после него
            if 'admin_id =' in content:
                import re
                admin_id_match = re.search(r'admin_id\s*=\s*(\d+)', content)
                if admin_id_match:
                    admin_id = admin_id_match.group(1)
                    content = content.replace(
                        f"admin_id = {admin_id}",
                        f"admin_id = {admin_id}\nchat_id = {admin_id}  # ID чата для уведомлений (автоматически)"
                    )
                    updated = True
                    print("✅ Добавлен chat_id в существующий конфиг")
        
        # Добавляем настройки уведомлений если их нет
        if 'enable_startup_notification =' not in content:
            notification_settings = '''
# Уведомления
enable_startup_notification = False  # Уведомление о запуске бота
enable_security_notifications = False  # Уведомления о попытках доступа
'''
            # Добавляем после настроек бота
            if '# Настройки бота' in content:
                content = content.replace(
                    '# Настройки бота',
                    '# Настройки бота' + notification_settings
                )
                updated = True
                print("✅ Добавлены настройки уведомлений")
        
        if updated:
            with open('config.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ Существующий config.py обновлен до версии 3.0!")
        
        return updated
        
    except Exception as e:
        print(f"⚠️ Не удалось обновить существующий config.py: {e}")
        return False

def main():
    """Основная функция настройки"""
    try:
        clear_screen()
        print_banner()
        
        # Проверяем, существует ли уже конфигурация
        if os.path.exists('config.py'):
            response = input("📁 Конфигурация уже существует. Обновить до версии 3.0? (y/N): ").strip().lower()
            if response == 'y':
                print("ℹ️ Обновляем существующую конфигурацию...")
                if update_existing_config():
                    print("🎉 Настройка завершена!")
                    print("\n🛡️ Ваш бот обновлен до Kbot 3.0!")
                else:
                    print("ℹ️ Конфигурация уже актуальна.")
                return
            else:
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
        print(f"\n🎉 Настройка Kbot 3.0 завершена успешно!")
        print("=" * 50)
        print("📁 Созданные файлы:")
        print("   • config.py - основная конфигурация")
        print("   • .env.example - пример для продвинутой настройки")
        print("   • modules/ - папка для модулей")
        print("   • backups/ - папка для бэкапов")
        print("   • logs/ - папка для логов")
        
        print("\n👤 Ваши данные:")
        print(f"   • ID: {user_info.id}")
        print(f"   • Имя: {user_info.first_name}")
        if user_info.username:
            print(f"   • Username: @{user_info.username}")
        print(f"   • Chat ID: {user_info.id} (автоматически установлен)")
        
        print("\n🛡️ Система безопасности:")
        print("   • Глобальная защита команд: ✅ Включена")
        print("   • Проверка прав доступа: ✅ Активна")
        print("   • Защита модулей: ✅ Автоматическая")
        print("   • Уведомления о попытках доступа: ❌ Выключены")
        print("   • Уведомление о запуске: ❌ Выключено")
        
        print("\n🔧 Особенности версии 3.0:")
        print("   • Скрытые системные модули")
        print("   • Улучшенный интерфейс команд")
        print("   • Оптимизированная производительность")
        print("   • Расширенные настройки уведомлений")
        
        print("\n🚀 Запуск бота:")
        print("   python main.py")
        
        print("\n📚 Основные команды:")
        print("   .help - список всех команд")
        print("   .modules - список модулей")
        print("   .klm - установить модуль (ответ на .py файл)")
        print("   .kun <имя> - удалить модуль")
        print("   .security - информация о безопасности")
        print("   .settings - настройки уведомлений")
        
        print("\n🔒 Безопасность:")
        print("   • Бот реагирует ТОЛЬКО на ваши команды")
        print("   • Все модули автоматически защищены")
        print("   • Попытки доступа логируются и блокируются")
        print("   • Уведомления ВЫКЛЮЧЕНЫ по умолчанию")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Настройка прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        print("💡 Если проблема повторяется, создайте issue на GitHub")

if __name__ == "__main__":
    main()
