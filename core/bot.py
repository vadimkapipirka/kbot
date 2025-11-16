import asyncio
import logging
import sys
import os
import importlib.util
import time
from telethon import TelegramClient, events
from .module_manager.manager import ModuleManager

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

class Kbot:
    def __init__(self):
        # Инициализируем логгер ПЕРВЫМ делом
        self.logger = logging.getLogger("Kbot")
        self.config = self.load_config()
        self.client = None
        self.module_manager = ModuleManager(self)
        self.me = None
        self.system_commands = {
            '.modules', '.klm', '.kun', '.help', '.info', '.khelp', 
            '.restart', '.update', '.ping', '.backup', '.settings'
        }
        self.start_time = time.time()
        
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
            command_prefix = getattr(config, 'command_prefix', '.')
            enable_backups = getattr(config, 'enable_backups', True)
            
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
                'command_prefix': command_prefix,
                'enable_backups': enable_backups
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            self.logger.info("💡 Запустите setup.py для настройки")
            raise
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        if not self.config.get('admin_id'):
            return True  # Если admin_id не указан, все пользователи админы
        return user_id == self.config['admin_id']
    
    async def start(self):
        """Запускает бота"""
        self.logger.info("🚀 Запуск Kbot...")
        
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
        
        self.logger.info(f"✅ Авторизован как: {self.me.username or self.me.first_name}")
        
        # Создаем бэкап модулей при первом запуске
        if self.config.get('enable_backups', True):
            await self.create_modules_backup()
        
        # Загружаем модули
        await self.module_manager.load_all_modules()
        
        # Регистрируем системные команды
        await self.register_system_commands()
        
        self.logger.info("✅ Kbot успешно запущен!")
        self.logger.info(f"💻 Системные команды: {', '.join(sorted(self.system_commands))}")
        
        await self.client.run_until_disconnected()
    
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
                backups = sorted([os.path.join(backup_dir, d) for d in os.listdir(backup_dir) 
                                if d.startswith("modules_backup_")])
                for old_backup in backups[:-5]:
                    shutil.rmtree(old_backup)
                    self.logger.info(f"🗑️ Удален старый бэкап: {old_backup}")
                    
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось создать бэкап: {e}")
    
    def is_system_command(self, command: str) -> bool:
        """Проверяет, является ли команда системной"""
        clean_command = command.replace(r'\.', '.').replace(r'\s+', ' ').split()[0]
        return clean_command in self.system_commands
    
    async def safe_reply(self, event, message: str):
        """Безопасно отвечает на сообщение, заменяя команду"""
        try:
            await event.edit(message)
        except Exception as e:
            await event.reply(message)
    
    async def register_system_commands(self):
        """Регистрирует системные команды для управления модулями"""
        
        @self.client.on(events.NewMessage(pattern=r'\.modules'))
        async def list_modules_handler(event):
            """Показывает список всех модулей"""
            if not self.is_admin(event.sender_id):
                await self.safe_reply(event, "❌ Недостаточно прав для выполнения этой команды")
                return
                
            modules = self.module_manager.list_modules()
            if modules:
                loaded_count = len([m for m in modules.values() if m['loaded']])
                message = f"📦 **Модули Kbot** ({loaded_count}/{len(modules)})\n\n"
                for name, info in modules.items():
                    status = "✅" if info['loaded'] else "❌"
                    message += f"{status} `{name}`\n"
                    if info['loaded'] and info['commands']:
                        message += f"   └─ Команды: {', '.join(info['commands'])}\n"
            else:
                message = "📦 Нет установленных модулей"
            await self.safe_reply(event, message)
        
        @self.client.on(events.NewMessage(pattern=r'\.klm'))
        async def install_module_handler(event):
            """Устанавливает модуль из файла .py в ответ на сообщение"""
            if not self.is_admin(event.sender_id):
                await self.safe_reply(event, "❌ Недостаточно прав для установки модулей")
                return
                
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
                        await self.safe_reply(event, message)
                    else:
                        await self.safe_reply(event, f"❌ Ошибка загрузки модуля `{file_name}`")
                        if os.path.exists(downloaded):
                            os.remove(downloaded)
                else:
                    await self.safe_reply(event, "❌ Ошибка скачивания файла")
                    
            except Exception as e:
                await self.safe_reply(event, f"❌ Ошибка установки: {str(e)}")
        
        @self.client.on(events.NewMessage(pattern=r'\.kun\s+(\w+)'))
        async def uninstall_module_handler(event):
            """Удаляет модуль по имени"""
            if not self.is_admin(event.sender_id):
                await self.safe_reply(event, "❌ Недостаточно прав для удаления модулей")
                return
                
            module_name = event.pattern_match.group(1)
            
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
                    ('.settings', 'Настройки бота')
                ]
                
                message = "🛠 **Kbot - Система помощи**\n\n"
                message += "⚙️ **Системные команды:**\n"
                for cmd, desc in system_commands:
                    message += f"• `{cmd}` - {desc}\n"
                
                message += "\n📦 **Установленные модули:**\n"
                for module_name, info in all_commands.items():
                    command_count = len(info['commands'])
                    message += f"• `{module_name}` - {command_count} команд\n"
                
                message += "\n💡 Используйте `.help <модуль>` для подробной информации"
                await self.safe_reply(event, message)
        
        @self.client.on(events.NewMessage(pattern=r'\.info'))
        async def info_handler(event):
            """Показывает информацию о боте"""
            user = self.me.username or self.me.first_name
            modules = self.module_manager.list_modules()
            loaded_modules = len([m for m in modules.values() if m['loaded']])
            total_commands = self.module_manager.get_all_commands_count()
            
            # Время работы
            uptime = time.time() - self.start_time
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            
            message = f"""
🤖 **Kbot Информация**

👤 Владелец: {user}
📦 Модулей: {loaded_modules}/{len(modules)}
🛠 Команды: {total_commands}
⏱ Время работы: {hours}ч {minutes}м
🚀 Статус: Активен

💻 Система: Python + Telethon
🎯 Версия: 2.0
🔒 Защищенных команд: {len(self.system_commands)}
        """.strip()
            
            await self.safe_reply(event, message)
        
        @self.client.on(events.NewMessage(pattern=r'\.ping'))
        async def ping_handler(event):
            """Проверка пинга - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
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
            if not self.is_admin(event.sender_id):
                await self.safe_reply(event, "❌ Недостаточно прав для перезапуска")
                return
                
            await self.safe_reply(event, '🔄 Перезапуск Kbot...')
            os.execv(sys.executable, [sys.executable] + sys.argv)
        
        @self.client.on(events.NewMessage(pattern=r'\.update'))
        async def update_handler(event):
            """Обновление бота через Git"""
            if not self.is_admin(event.sender_id):
                await self.safe_reply(event, "❌ Недостаточно прав для обновления")
                return
                
            try:
                await self.safe_reply(event, '🔄 Проверка обновлений...')
                
                import subprocess
                result = subprocess.run(['git', 'pull'], 
                                      capture_output=True, 
                                      text=True, 
                                      cwd=os.path.dirname(os.path.dirname(__file__)))
                
                if result.returncode == 0:
                    if 'Already up to date' in result.stdout:
                        await self.safe_reply(event, '✅ Бот уже обновлен до последней версии!')
                    else:
                        await self.safe_reply(event, f'✅ Бот успешно обновлен!\n\n```{result.stdout}```')
                        await self.safe_reply(event, '🔄 Перезапуск для применения обновлений...')
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    await self.safe_reply(event, f'❌ Ошибка при обновлении:\n```{result.stderr}```')
                    
            except Exception as e:
                await self.safe_reply(event, f'❌ Ошибка при обновлении: {str(e)}')
        
        @self.client.on(events.NewMessage(pattern=r'\.backup'))
        async def backup_handler(event):
            """Создает бэкап модулей"""
            if not self.is_admin(event.sender_id):
                await self.safe_reply(event, "❌ Недостаточно прав для создания бэкапов")
                return
                
            try:
                await self.create_modules_backup()
                await self.safe_reply(event, '✅ Бэкап модулей успешно создан!')
            except Exception as e:
                await self.safe_reply(event, f'❌ Ошибка создания бэкапа: {str(e)}')
        
        @self.client.on(events.NewMessage(pattern=r'\.settings'))
        async def settings_handler(event):
            """Показывает текущие настройки бота (без конфиденциальной информации)"""
            if not self.is_admin(event.sender_id):
                await self.safe_reply(event, "❌ Недостаточно прав для просмотра настроек")
                return
                
            message = f"""
⚙️ **Настройки Kbot**

🔧 Основные настройки:
• Префикс команд: `{self.config.get('command_prefix', '.')}`
• Бэкапы: {'✅ Включены' if self.config.get('enable_backups', True) else '❌ Выключены'}
• Админ ID: `{self.config.get('admin_id', 'Не установлен')}`
• Имя пользователя: `{self.config.get('user_name', 'Неизвестно')}`

📊 Статистика:
• Модулей: {len(self.module_manager.list_modules())}
• Команд: {self.module_manager.get_all_commands_count()}
• Системных команд: {len(self.system_commands)}
• Время работы: {int(time.time() - self.start_time)} сек
            """.strip()
            
            await self.safe_reply(event, message)
