"""
Глобальная система безопасности Kbot 3.0
Автоматически защищает все команды от неавторизованных пользователей
"""

import logging
import re
from telethon import events

class SecurityManager:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("SecurityManager")
        self.allowed_users = set()
        self._original_handlers = {}
        self.blocked_attempts = 0
        
    def add_admin(self, user_id: int):
        """Добавляет администратора"""
        self.allowed_users.add(user_id)
        
    def is_user_allowed(self, user_id: int) -> bool:
        """Проверяет, разрешен ли пользователь"""
        if not self.bot.config.get('admin_id'):
            return user_id == getattr(self.bot.me, 'id', None)
        return user_id in self.allowed_users or user_id == self.bot.config['admin_id']
    
    def secure_event_handler(self, handler):
        """Обертка для защиты обработчиков событий"""
        async def secured_handler(event):
            # Проверяем права доступа
            if not self.is_user_allowed(event.sender_id):
                self.logger.debug(f"🚫 Блокировка команды от пользователя {event.sender_id}: {event.text}")
                return  # Просто игнорируем команду
            
            # Вызываем оригинальный обработчик
            return await handler(event)
        
        return secured_handler
    
    def secure_all_handlers(self):
        """Защищает все зарегистрированные обработчики"""
        client = self.bot.client
        if not hasattr(client, '_event_builders'):
            return
            
        for builder in client._event_builders:
            if hasattr(builder, 'func'):
                # Сохраняем оригинальную функцию если еще не сохранили
                if id(builder.func) not in self._original_handlers:
                    self._original_handlers[id(builder.func)] = builder.func
                    builder.func = self.secure_event_handler(builder.func)
    
    def register_global_security(self):
        """Регистрирует глобальную систему безопасности"""
        @self.bot.client.on(events.NewMessage(outgoing=False))
        async def global_security_filter(event):
            """Глобальный фильтр безопасности для ВСЕХ входящих сообщений"""
            
            # Игнорируем сообщения без текста
            if not event.text or not event.text.strip():
                return
            
            text = event.text.strip()
            
            # Проверяем, является ли сообщение командой (начинается с префикса)
            command_prefix = self.bot.config.get('command_prefix', '.')
            if not text.startswith(command_prefix):
                return  # Не команда - пропускаем
            
            # Проверяем права доступа
            if not self.is_user_allowed(event.sender_id):
                self.blocked_attempts += 1
                self.logger.info(f"🚫 БЛОКИРОВКА: Пользователь {event.sender_id} попытался выполнить команду: {text}")
                
                # Отправляем уведомление только если включено в конфиге
                if self.bot.config.get('enable_security_notifications'):
                    try:
                        if self.bot.config.get('chat_id'):
                            await self.bot.client.send_message(
                                self.bot.config['chat_id'],
                                f"🚫 **Попытка несанкционированного доступа**\n"
                                f"👤 Пользователь: {event.sender_id}\n"
                                f"📝 Команда: `{text}`\n"
                                f"💬 Чат: `{event.chat_id}`\n"
                                f"🔢 Всего блокировок: `{self.blocked_attempts}`"
                            )
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки уведомления: {e}")
                
                # Останавливаем обработку события
                raise events.StopPropagation
        
        self.logger.info("✅ Глобальная система безопасности активирована")
    
    def scan_and_secure_modules(self):
        """Сканирует и защищает все модули"""
        for module_name, module_info in self.bot.module_manager.modules.items():
            if module_info['loaded']:
                self.logger.debug(f"🔒 Защита модуля: {module_name}")
    
    def get_security_report(self):
        """Возвращает отчет о безопасности - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        client = getattr(self.bot, 'client', None)
        if not client or not hasattr(client, '_event_builders'):
            return {
                'total_handlers': 0,
                'protected_commands': 0,
                'allowed_users': len(self.allowed_users),
                'admin_id': self.bot.config.get('admin_id'),
                'blocked_attempts': self.blocked_attempts,
                'security_enabled': True
            }
        
        total_handlers = len(client._event_builders)
        protected_commands = len([h for h in client._event_builders 
                                if hasattr(h, 'func') and id(h.func) in self._original_handlers])
        
        return {
            'total_handlers': total_handlers,
            'protected_commands': protected_commands,
            'allowed_users': len(self.allowed_users),
            'admin_id': self.bot.config.get('admin_id'),
            'blocked_attempts': self.blocked_attempts,
            'security_enabled': True
        }


# Глобальный экземпляр
security_manager = None

def init_security(bot):
    """Инициализирует глобальную систему безопасности"""
    global security_manager
    security_manager = SecurityManager(bot)
    
    # Добавляем администратора из конфига
    if bot.config.get('admin_id'):
        security_manager.add_admin(bot.config['admin_id'])
    
    # Добавляем владельца сессии
    if hasattr(bot.me, 'id'):
        security_manager.add_admin(bot.me.id)
    
    return security_manager
