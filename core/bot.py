import asyncio
import logging
import sys
import os
import importlib.util
import time
from telethon import TelegramClient, events
from .module_manager.manager import ModuleManager
from .security import init_security, security_manager

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class Kbot:
    def __init__(self):
        # Инициализируем логгер ПЕРВЫМ делом
        self.logger = logging.getLogger("Kbot")
        self.config = self.load_config()
        self.client = None
        self.module_manager = ModuleManager(self)
        self.me = None
        self.security = None
        self.system_commands = {
            '.modules', '.klm', '.kun', '.help', '.info', '.khelp',
            '.restart', '.update', '.ping', '.backup', '.settings',
            '.checkupdate', '.version', '.security'
        }
        self.start_time = time.time()
        # Системные модули, которые нельзя удалить и не показываются в списке
        self.system_modules = {'loader', 'system_utils', 'stats'}

    def load_config(self):
        """Загружает конфигурацию из config.py"""
        try:
            # Динамически импортируем config.py
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
            spec = importlib.util.spec_from_file_location("config", config_path)
            config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config)
            
            # Получаем значения из config
            api_id = getattr(config, 'api_id', None)
            api_hash = getattr(config, 'api_hash', None)
            session_name = getattr(config, 'session_name', 'session_kbot')
            session_string = getattr(config, 'session_string', None)
            admin_id = getattr(config, 'admin_id', None)
            chat_id = getattr(config, 'chat_id', None)
            user_name = getattr(config, 'user_name', 'User')
            command_prefix = getattr(config, 'command_prefix', '.')
            enable_backups = getattr(config, 'enable_backups', True)
            enable_startup_notification = getattr(config, 'enable_startup_notification', False)  # Новое поле
            enable_security_notifications = getattr(config, 'enable_security_notifications', False)  # Новое поле
            
            if not api_id or not api_hash:
                self.logger.error("❌ Не найдены api_id или api_hash")
                self.logger.info("💡 Запустите setup.py для настройки")
                raise ValueError("Отсутствуют api_id или api_hash")
                
            self.logger.info("✅ Конфигурация загружена")
            return {
                'api_id': int(api_id),
                'api_hash': api_hash,
                'session_name': session_name,
                'session_string': session_string,
                'admin_id': int(admin_id) if admin_id else None,
                'chat_id': int(chat_id) if chat_id else None,
                'user_name': user_name,
                'command_prefix': command_prefix,
                'enable_backups': enable_backups,
                'enable_startup_notification': enable_startup_notification,
                'enable_security_notifications': enable_security_notifications
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            self.logger.info("💡 Запустите setup.py для настройки")
            raise

    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        if not self.security:
            # Если безопасность не инициализирована, используем базовую проверку
            if not self.config.get('admin_id'):
                return user_id == getattr(self.me, 'id', None)
            return user_id == self.config['admin_id']
        return self.security.is_user_allowed(user_id)

    async def update_config_file(self):
        """Обновляет config.py с текущими данными"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Обновляем chat_id если его нет или он пустой
            if 'chat_id =' not in content or self.config.get('chat_id') is None:
                if 'chat_id =' in content:
                    # Заменяем существующий chat_id
                    import re
                    content = re.sub(r'chat_id\s*=\s*[^\n]+', f'chat_id = {self.me.id}', content)
                else:
                    # Добавляем chat_id после admin_id
                    if 'admin_id =' in content:
                        content = content.replace(
                            f"admin_id = {self.config.get('admin_id', self.me.id)}",
                            f"admin_id = {self.config.get('admin_id', self.me.id)}\nchat_id = {self.me.id}"
                        )
                
                # Записываем обновленный конфиг
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.logger.info(f"✅ Конфиг обновлен: chat_id = {self.me.id}")
            
            # Обновляем user_name если он изменился
            current_name = self.me.first_name or 'User'
            if f"user_name = '{self.config.get('user_name', 'User')}'" in content:
                content = content.replace(
                    f"user_name = '{self.config.get('user_name', 'User')}'",
                    f"user_name = '{current_name}'"
                )
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Добавляем новые настройки если их нет
            if 'enable_startup_notification =' not in content:
                content += "\n# Уведомления\nenable_startup_notification = False  # Уведомление о запуске бота\nenable_security_notifications = False  # Уведомления о попытках доступа\n"
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
            self.config['chat_id'] = self.me.id
            self.config['user_name'] = current_name
            self.config['enable_startup_notification'] = False  # По умолчанию выключено
            self.config['enable_security_notifications'] = False  # По умолчанию выключено
            
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось обновить config.py: {e}")

    async def start(self):
        """Запускает бота"""
        self.logger.info("🚀 Запуск Kbot 3.0...")
        
        # Используем session string если есть, иначе обычную сессию
        if self.config.get('session_string'):
            from telethon.sessions import StringSession
            self.client = TelegramClient(
                StringSession(self.config['session_string']),
                self.config['api_id'],
                self.config['api_hash']
            )
        else:
            self.client = TelegramClient(
                self.config['session_name'],
                self.config['api_id'],
                self.config['api_hash']
            )
            
        await self.client.start()
        self.me = await self.client.get_me()
        self.logger.info(f"✅ Авторизован как: {self.me.username or self.me.first_name} (ID: {self.me.id})")
        
        # Инициализируем систему безопасности ДО всего остального
        self.security = init_security(self)
        self.logger.info("🛡️ Инициализация системы безопасности...")
        
        # Обновляем конфигурационный файл с актуальными данными
        await self.update_config_file()
        
        # Активируем глобальную безопасность
        self.security.register_global_security()
        
        # Создаем бэкап модулей при первом запуске
        if self.config.get('enable_backups', True):
            await self.create_modules_backup()
            
        # Загружаем модули
        await self.module_manager.load_all_modules()
        
        # Защищаем все загруженные модули
        self.security.scan_and_secure_modules()
        
        # Регистрируем системные команды
        await self.register_system_commands()
        
        self.logger.info("✅ Kbot 3.0 успешно запущен!")
        self.logger.info(f"💻 Системные команды: {', '.join(sorted(self.system_commands))}")
        self.logger.info(f"👤 Админ: {self.me.first_name} (ID: {self.me.id})")
        self.logger.info("🛡️ Глобальная система безопасности активирована")
        self.logger.info("🔕 Уведомления о запуске и безопасности отключены")
        
        # Отправляем уведомление о запуске только если включено в конфиге
        if self.config.get('enable_startup_notification'):
            await self.send_startup_notification()
        
        await self.client.run_until_disconnected()

    async def send_startup_notification(self):
        """Отправляет уведомление о запуске бота (только если включено)"""
        try:
            if self.config.get('chat_id') and self.config.get('enable_startup_notification'):
                message = f"""
🤖 **Kbot 3.0 запущен!**

👤 Владелец: {self.me.first_name}
🆔 User ID: {self.me.id}
🛡️ Безопасность: Активна
📦 Модулей: {len([m for m in self.module_manager.list_modules().items() if m[0] not in self.system_modules])}
🚀 Статус: Работает

💡 Используйте `.help` для списка команд
🔒 Бот защищен от несанкционированного доступа
""".strip()
                await self.client.send_message(self.config['chat_id'], message)
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось отправить уведомление: {e}")

    async def create_modules_backup(self):
        """Создает бэкап модулей"""
        try:
            import shutil
            from datetime import datetime
            
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"modules_backup_{timestamp}")
            
            if os.path.exists("modules"):
                shutil.copytree("modules", backup_path)
                self.logger.info(f"📦 Создан бэкап модулей: {backup_path}")
                
            # Удаляем старые бэкапы (оставляем последние 5)
            backups = sorted([os.path.join(backup_dir, d) for d in os.listdir(backup_dir) if d.startswith("modules_backup_")])
            for old_backup in backups[:-5]:
                shutil.rmtree(old_backup)
                self.logger.info(f"🗑️ Удален старый бэкап: {old_backup}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось создать бэкап: {e}")

    async def safe_reply(self, event, message: str):
        """Безопасно отвечает на сообщение, заменяя команду"""
        try:
            # Пытаемся отредактировать исходное сообщение с командой
            if event.text and event.text.startswith('.'):  # Это команда
                await event.edit(message)
            else:
                await event.reply(message)
        except Exception as e:
            # Если редактирование не удалось, отправляем новое сообщение
            try:
                await event.reply(message)
            except Exception as e2:
                self.logger.error(f"❌ Не удалось отправить сообщение: {e2}")

    async def register_system_commands(self):
        """Регистрирует системные команды для управления модулями"""
        
        @self.client.on(events.NewMessage(pattern=r'\.modules'))
        async def list_modules_handler(event):
            """Показывает список всех пользовательских модулей (исключая системные)"""
            modules = self.module_manager.list_modules()
            user_modules = {name: info for name, info in modules.items() if name not in self.system_modules}
            
            if user_modules:
                loaded_count = len([m for m in user_modules.values() if m['loaded']])
                message = f"📦 **Пользовательские модули Kbot** ({loaded_count}/{len(user_modules)})\n\n"
                for name, info in user_modules.items():
                    status = "✅" if info['loaded'] else "❌"
                    message += f"{status} `{name}`\n"
                    if info['loaded'] and info['commands']:
                        message += f" └─ Команды: {', '.join(info['commands'])}\n"
            else:
                message = "📦 Нет установленных модулей\n💡 Используйте `.klm` для установки модулей"
            
            # Добавляем информацию о системных модулях
            system_loaded = len([m for m in modules.items() if m[0] in self.system_modules and m[1]['loaded']])
            message += f"\n🔧 **Системные модули:** {system_loaded}/{len(self.system_modules)} (скрыты)"
            
            await self.safe_reply(event, message)

        @self.client.on(events.NewMessage(pattern=r'\.klm'))
        async def install_module_handler(event):
            """Устанавливает модуль из файла .py в ответ на сообщение"""
            if not event.is_reply:
                await self.safe_reply(event, "❌ Ответьте на сообщение с файлом модуля (.py) командой `.klm`")
                return
            
            try:
                reply_msg = await event.get_reply_message()
                if not reply_msg.file or not reply_msg.file.name.endswith('.py'):
                    await self.safe_reply(event, "❌ Это не Python файл! Ответьте на сообщение с файлом .py")
                    return
                
                await self.safe_reply(event, "📥 Скачиваю модуль...")
                file_name = reply_msg.file.name
                file_path = f"modules/{file_name}"
                os.makedirs("modules", exist_ok=True)
                
                downloaded = await reply_msg.download_media(file=file_path)
                if downloaded:
                    # Проверяем модуль на конфликты
                    module_conflicts = await self.module_manager.check_module_conflicts(downloaded, self.system_commands)
                    if module_conflicts:
                        conflict_message = f"❌ Модуль `{file_name}` содержит конфликтующие команды:\n"
                        for conflict in module_conflicts:
                            conflict_message += f"• `{conflict}` - системная команда\n"
                        conflict_message += "\nИзмените команды в модуле и попробуйте снова."
                        await self.safe_reply(event, conflict_message)
                        if os.path.exists(downloaded):
                            os.remove(downloaded)
                        return
                    
                    success = await self.module_manager.load_module_from_file(downloaded)
                    if success:
                        module_name = file_name[:-3]
                        commands = self.module_manager.get_module_commands(module_name)
                        message = f"✅ Модуль `{module_name}` успешно установлен!"
                        if commands:
                            message += f"\n\n🛠 Доступные команды:\n" + "\n".join(f"• `{cmd}`" for cmd in commands)
                        
                        # Автоматически защищаем новый модуль
                        self.security.scan_and_secure_modules()
                        
                        await self.safe_reply(event, message)
                    else:
                        await self.safe_reply(event, f"❌ Ошибка загрузки модуля `{file_name}`")
                    
                    # НЕ удаляем файл - сохраняем его в папке modules для постоянного хранения
                else:
                    await self.safe_reply(event, "❌ Ошибка скачивания файла")
                    
            except Exception as e:
                await self.safe_reply(event, f"❌ Ошибка установки: {str(e)}")

        @self.client.on(events.NewMessage(pattern=r'\.kun\s+(\w+)'))
        async def uninstall_module_handler(event):
            """Удаляет модуль по имени"""
            module_name = event.pattern_match.group(1)
            
            # Запрещаем удаление системных модулей
            if module_name in self.system_modules:
                await self.safe_reply(event, f"❌ Модуль `{module_name}` является системным и не может быть удален!")
                return
            
            if await self.module_manager.unload_module(module_name):
                file_path = f"modules/{module_name}.py"
                if os.path.exists(file_path):
                    os.remove(file_path)
                await self.safe_reply(event, f"✅ Модуль `{module_name}` полностью удален!")
            else:
                await self.safe_reply(event, f"❌ Модуль `{module_name}` не найден!")

        @self.client.on(events.NewMessage(pattern=r'\.help(?:\s+(\w+))?'))
        async def help_handler(event):
            """Показывает справку по командам"""
            module_name = event.pattern_match.group(1)
            
            if module_name:
                # Запрещаем просмотр системных модулей
                if module_name in self.system_modules:
                    await self.safe_reply(event, f"❌ Модуль `{module_name}` является системным и скрыт")
                    return
                    
                module_info = self.module_manager.get_module_info(module_name)
                if module_info:
                    commands = module_info.get('commands', [])
                    description = module_info.get('description', 'Нет описания')
                    message = f"📚 **Модуль {module_name}**\n\n"
                    message += f"📖 Описание: {description}\n\n"
                    if commands:
                        message += "🛠 **Команды:**\n" + "\n".join(f"• `{cmd}`" for cmd in commands)
                    else:
                        message += "🛠 Команды не найдены"
                    await self.safe_reply(event, message)
                else:
                    await self.safe_reply(event, f"❌ Модуль `{module_name}` не найден!")
            else:
                all_commands = self.module_manager.get_all_commands()
                user_commands = {name: info for name, info in all_commands.items() if name not in self.system_modules}
                
                system_commands = [
                    ('.modules', 'Показать все модули'),
                    ('.klm', 'Установить модуль (ответ на .py файл)'),
                    ('.kun <название>', 'Удалить модуль'),
                    ('.help', 'Эта справка'),
                    ('.help <модуль>', 'Помощь по модулю'),
                    ('.info', 'Информация о боте'),
                    ('.ping', 'Проверить пинг бота'),
                    ('.restart', 'Перезапустить бота'),
                    ('.update', 'Обновить бота'),
                    ('.backup', 'Создать бэкап модулей'),
                    ('.settings', 'Настройки бота'),
                    ('.checkupdate', 'Проверить обновления'),
                    ('.version', 'Показать версию бота'),
                    ('.security', 'Информация о безопасности')
                ]
                
                message = "🛠 **Kbot 3.0 - Система помощи**\n\n"
                message += "⚙️ **Системные команды:**\n"
                for cmd, desc in system_commands:
                    message += f"• `{cmd}` - {desc}\n"
                
                message += "\n📦 **Пользовательские модули:**\n"
                if user_commands:
                    for module_name, info in user_commands.items():
                        command_count = len(info['commands'])
                        message += f"• `{module_name}` - {command_count} команд\n"
                else:
                    message += "• Нет установленных модулей\n"
                    message += "• Используйте `.klm` для установки\n"
                
                message += "\n🔧 **Системные модули:** 3 модуля (скрыты)\n"
                message += "\n💡 Используйте `.help <модуль>` для подробной информации"
                await self.safe_reply(event, message)

        @self.client.on(events.NewMessage(pattern=r'\.info'))
        async def info_handler(event):
            """Показывает информацию о боте"""
            user = self.me.username or self.me.first_name
            modules = self.module_manager.list_modules()
            user_modules = {name: info for name, info in modules.items() if name not in self.system_modules}
            loaded_user_modules = len([m for m in user_modules.values() if m['loaded']])
            total_commands = self.module_manager.get_all_commands_count()
            
            # Время работы
            uptime = time.time() - self.start_time
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            
            # Информация о безопасности
            security_report = self.security.get_security_report() if self.security else {}
            
            message = f"""
🤖 Kbot 3.0 - Информация

👤 Владелец: {user}
🆔 User ID: {self.me.id}
📞 Chat ID: {self.config.get('chat_id', 'Не установлен')}
📦 Модулей: {loaded_user_modules}/{len(user_modules)} (пользовательских)
🔧 Системных: {len([m for m in modules.items() if m[0] in self.system_modules and m[1]['loaded']])}/{len(self.system_modules)}
🛠 Команды: {total_commands}
⏱ Время работы: {hours}ч {minutes}м
🚀 Статус: Активен

🛡️ Безопасность:
• Защищенных команд: {security_report.get('protected_commands', 0)}
• Разрешенных пользователей: {security_report.get('allowed_users', 1)}
• Блокировок: {security_report.get('blocked_attempts', 0)}
• Глобальная защита: ✅ Активна

💻 Система: Python + Telethon
🎯 Версия: 3.0
""".strip()

            await self.safe_reply(event, message)

        @self.client.on(events.NewMessage(pattern=r'\.ping'))
        async def ping_handler(event):
            """Проверка пинга"""
            try:
                start = time.time()
                # Сразу редактируем сообщение с командой
                await event.edit('🏓 Измеряю пинг...')
                end = time.time()
                ping_time = round((end - start) * 1000, 2)
                await event.edit(f'🏓 Pong! `{ping_time}ms`')
            except Exception as e:
                # Если не удалось редактировать, отправляем новое сообщение
                start = time.time()
                msg = await event.reply('🏓 Измеряю пинг...')
                end = time.time()
                ping_time = round((end - start) * 1000, 2)
                await msg.edit(f'🏓 Pong! `{ping_time}ms`')

        @self.client.on(events.NewMessage(pattern=r'\.restart'))
        async def restart_handler(event):
            """Перезапуск бота"""
            await self.safe_reply(event, '🔄 Перезапуск Kbot 3.0...')
            os.execv(sys.executable, [sys.executable] + sys.argv)

        @self.client.on(events.NewMessage(pattern=r'\.update'))
        async def update_handler(event):
            """Обновление бота через Git"""
            try:
                await self.safe_reply(event, '🔄 Проверка обновлений...')
                import subprocess
                
                # Получаем корневую директорию проекта
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # Выполняем git pull из корневой директории
                result = subprocess.run(
                    ['git', 'pull', '--rebase'], 
                    capture_output=True, 
                    text=True, 
                    cwd=root_dir,
                    timeout=30
                )
                
                if result.returncode == 0:
                    if 'Already up to date' in result.stdout:
                        await self.safe_reply(event, '✅ Бот уже обновлен до последней версии!')
                    else:
                        # Показываем что обновилось
                        update_output = result.stdout.strip()
                        if not update_output:
                            update_output = result.stderr.strip()
                        
                        await self.safe_reply(event, f'✅ Бот успешно обновлен!\n\n```{update_output}```')
                        
                        # Перезагружаем зависимости если нужно
                        if 'requirements.txt' in update_output:
                            await self.safe_reply(event, '📦 Обновление зависимостей...')
                            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                                         cwd=root_dir)
                        
                        await self.safe_reply(event, '🔄 Перезапуск для применения обновлений...')
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    error_msg = result.stderr if result.stderr else result.stdout
                    await self.safe_reply(event, f'❌ Ошибка при обновлении:\n```{error_msg}```')
                    
            except subprocess.TimeoutExpired:
                await self.safe_reply(event, '❌ Таймаут при обновлении. Попробуйте позже.')
            except Exception as e:
                await self.safe_reply(event, f'❌ Ошибка при обновлении: {str(e)}')

        @self.client.on(events.NewMessage(pattern=r'\.backup'))
        async def backup_handler(event):
            """Создает бэкап модулей"""
            try:
                await self.create_modules_backup()
                await self.safe_reply(event, '✅ Бэкап модулей успешно создан!')
            except Exception as e:
                await self.safe_reply(event, f'❌ Ошибка создания бэкапа: {str(e)}')

        @self.client.on(events.NewMessage(pattern=r'\.settings'))
        async def settings_handler(event):
            """Показывает текущие настройки бота"""
            modules = self.module_manager.list_modules()
            user_modules = {name: info for name, info in modules.items() if name not in self.system_modules}
            
            message = f"""
⚙️ Kbot 3.0 - Настройки

🔧 Основные настройки:
• Префикс команд: {self.config.get('command_prefix', '.')}
• Бэкапы: {'✅ Включены' if self.config.get('enable_backups', True) else '❌ Выключены'}
• Уведомления о запуске: {'✅ Включены' if self.config.get('enable_startup_notification', False) else '❌ Выключены'}
• Уведомления безопасности: {'✅ Включены' if self.config.get('enable_security_notifications', False) else '❌ Выключены'}
• Админ ID: {self.config.get('admin_id', 'Не установлен')}
• Chat ID: {self.config.get('chat_id', 'Не установлен')}
• Имя пользователя: {self.config.get('user_name', 'Неизвестно')}

📊 Статистика:
• Модулей: {len(user_modules)} (пользовательских)
• Системных: {len(self.system_modules)} модулей
• Команды: {self.module_manager.get_all_commands_count()}
• Системных команд: {len(self.system_commands)}
• Время работы: {int(time.time() - self.start_time)} сек

🛡️ Безопасность:
• Глобальная защита: ✅ Активна
• Проверка прав: ✅ Включена
• Уведомления: {'✅ Включены' if self.config.get('enable_security_notifications', False) else '❌ Выключены'}
""".strip()

            await self.safe_reply(event, message)

        @self.client.on(events.NewMessage(pattern=r'\.checkupdate'))
        async def check_update_handler(event):
            """Проверяет наличие обновлений с улучшенным выводом"""
            try:
                from utils.updater import manual_update_check
                await manual_update_check(self, event)
            except ImportError:
                await self.safe_reply(event, "❌ Модуль проверки обновлений не установлен")

        @self.client.on(events.NewMessage(pattern=r'\.version'))
        async def version_handler(event):
            """Показывает текущую версию бота"""
            try:
                from utils.updater import update_checker
                version_info = f"""
🤖 Kbot 3.0 - Версия

Текущая версия: v{update_checker.current_version}
Репозиторий: {update_checker.update_url}

✨ **Что нового в 3.0:**
• Полная переработка системы безопасности
• Скрытые системные модули
• Улучшенная система уведомлений
• Оптимизация производительности
• Улучшенный интерфейс команд

💡 Используйте .checkupdate для проверки обновлений
🔧 Используйте .update для автоматического обновления
""".strip()
                await self.safe_reply(event, version_info)
            except ImportError:
                await self.safe_reply(event, "❌ Модуль проверки обновлений не установлен")

        @self.client.on(events.NewMessage(pattern=r'\.security'))
        async def security_handler(event):
            """Показывает информацию о системе безопасности"""
            if not self.security:
                await self.safe_reply(event, "❌ Система безопасности не инициализирована")
                return
            
            try:
                report = self.security.get_security_report()
                
                message = f"""
🛡️ Kbot 3.0 - Система безопасности

📊 Статистика:
• Всего обработчиков: {report['total_handlers']}
• Защищенных команд: {report['protected_commands']}
• Разрешенных пользователей: {report['allowed_users']}
• Админ ID: {report['admin_id']}
• Блокировок: {report['blocked_attempts']}

🔒 Функции:
• Глобальная защита: ✅ Активна
• Проверка прав доступа: ✅ Включена
• Защита модулей: ✅ Активна
• Уведомления о попытках доступа: {'✅ Включены' if self.config.get('enable_security_notifications', False) else '❌ Выключены'}

💡 Система автоматически блокирует:
• Все команды от неавторизованных пользователей
• Попытки выполнения системных команд
• Доступ к установленным модулям

🚫 Заблокированные попытки доступа логируются
""".strip()

                await self.safe_reply(event, message)
            except Exception as e:
                await self.safe_reply(event, f"❌ Ошибка при получении отчета безопасности: {str(e)}")
