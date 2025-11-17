import importlib.util
import os
import sys
import inspect
import ast
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional

class ModuleManager:
    def __init__(self, bot):
        self.bot = bot
        self.modules: Dict[str, Any] = {}
        self.logger = logging.getLogger("ModuleManager")
        self.all_commands = {}
        
    async def load_all_modules(self):
        """Загружает все модули из папки modules"""
        modules_path = Path("modules")
        modules_path.mkdir(exist_ok=True)
        
        for file in modules_path.glob("*.py"):
            if file.name.startswith("_"):
                continue
            await self.load_module_from_file(file)
    
    async def check_module_conflicts(self, file_path, system_commands: set) -> List[str]:
        """Проверяет модуль на конфликты с системными командами"""
        conflicts = []
        try:
            file_path = Path(file_path)
            
            # Извлекаем команды из кода файла
            commands = self.extract_commands_from_code(file_path)
            
            # Проверяем каждую команду на конфликт
            for command in commands:
                clean_command = command.replace(r'\.', '.').replace(r'\s+', ' ').split()[0]
                if clean_command in system_commands:
                    conflicts.append(clean_command)
            
            return conflicts
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки конфликтов {file_path}: {e}")
            return [f"Ошибка проверки: {e}"]
    
    async def load_module_from_file(self, file_path) -> bool:
        """Загружает модуль из файла"""
        try:
            # Преобразуем в Path если это строка
            file_path = Path(file_path)
            module_name = file_path.stem
            
            # Проверяем безопасность модуля (кроме системных модулей)
            if module_name not in ['loader', 'system_utils', 'stats']:  # Белый список системных модулей
                if not await self.check_module_safety(file_path):
                    self.logger.warning(f"🚨 Модуль {module_name} не прошел проверку безопасности")
                    return False
            
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            
            # Извлекаем команды ДО выполнения модуля
            commands_before = self.extract_commands_from_code(file_path)
            
            spec.loader.exec_module(module)
            
            # Регистрируем модуль
            registered_commands = []
            if hasattr(module, "register"):
                # Новая система с функцией register
                await module.register(self.bot)
                self.logger.info(f"✅ Модуль {module_name} загружен (новая система)")
                # Для новых модулей извлекаем команды из register
                registered_commands = self.extract_commands_from_register(module)
            else:
                # Старая система - просто выполняем файл
                self.logger.info(f"✅ Модуль {module_name} загружен (старая система)")
                # Для старых модулей используем команды из кода
                registered_commands = commands_before
            
            # Получаем описание модуля
            module_description = self.get_module_description(module, file_path)
            
            self.modules[module_name] = {
                'module': module,
                'path': file_path,
                'loaded': True,
                'commands': registered_commands,
                'description': module_description
            }
            
            # Обновляем общий список команд
            self.update_all_commands()
            
            self.logger.info(f"✅ Модуль {module_name} загружен, найдено {len(registered_commands)} команд")
            return True
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки модуля {file_path}: {e}")
            return False
    
    def get_module_description(self, module, file_path: Path) -> str:
        """Получает описание модуля из docstring или создает автоматическое"""
        # Пробуем получить docstring модуля
        module_doc = getattr(module, '__doc__', '')

        if module_doc and module_doc.strip():
            # Очищаем docstring от лишних пробелов
            lines = [line.strip() for line in module_doc.split('\n') if line.strip()]
            if lines:
                return lines[0]  # Возвращаем первую строку docstring
        
        # Если docstring нет, пытаемся извлечь из файла
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Module):
                    for body_item in node.body:
                        if isinstance(body_item, ast.Expr) and isinstance(body_item.value, ast.Constant):
                            docstring = body_item.value.value
                            if isinstance(docstring, str) and docstring.strip():
                                lines = [line.strip() for line in docstring.split('\n') if line.strip()]
                                if lines:
                                    return lines[0]
                            break
                    break
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось извлечь описание из {file_path}: {e}")
        
        # Если ничего не нашли, возвращаем стандартное описание
        return "Модуль без описания"
    
    def extract_commands_from_code(self, file_path: Path) -> List[str]:
        """Извлекает команды из кода файла (для старых модулей)"""
        commands = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсим AST для поиска паттернов команд
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Ищем вызовы events.NewMessage
                    if (isinstance(node.func, ast.Attribute) and 
                        node.func.attr == 'NewMessage' and
                        isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'events'):
                        
                        # Ищем аргумент pattern
                        for keyword in node.keywords:
                            if keyword.arg == 'pattern':
                                if isinstance(keyword.value, ast.Constant):
                                    pattern = keyword.value.value
                                    if isinstance(pattern, str):
                                        # Убираем экранирование для отображения
                                        clean_pattern = pattern.replace(r'\.', '.')
                                        commands.append(clean_pattern)
                                elif isinstance(keyword.value, ast.JoinedStr):
                                    # f-строки, пропускаем сложные случаи
                                    pass
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось извлечь команды из кода {file_path}: {e}")
        
        return commands
    
    def extract_commands_from_register(self, module) -> List[str]:
        """Извлекает команды из функции register (для новых модулей)"""
        commands = []
        try:
            register_func = module.register
            source = inspect.getsource(register_func)
            
            # Парсим AST функции register
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Ищем декораторы @bot.client.on
                    if (isinstance(node.func, ast.Attribute) and
                        node.func.attr == 'on' and
                        isinstance(node.func.value, ast.Attribute) and
                        node.func.value.attr == 'client' and
                        isinstance(node.func.value.value, ast.Name) and
                        node.func.value.value.id == 'bot'):
                        
                        # Ищем аргументы events.NewMessage
                        for arg in node.args:
                            if (isinstance(arg, ast.Call) and
                                isinstance(arg.func, ast.Attribute) and
                                arg.func.attr == 'NewMessage' and
                                isinstance(arg.func.value, ast.Name) and
                                arg.func.value.id == 'events'):
                                
                                # Ищем pattern
                                for keyword in arg.keywords:
                                    if keyword.arg == 'pattern':
                                        if isinstance(keyword.value, ast.Constant):
                                            pattern = keyword.value.value
                                            if isinstance(pattern, str):
                                                # Убираем экранирование для отображения
                                                clean_pattern = pattern.replace(r'\.', '.')
                                                commands.append(clean_pattern)
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось извлечь команды из register: {e}")
        
        return commands
    
    async def check_module_safety(self, file_path: Path) -> bool:
        """Проверяет модуль на безопасность - УЛУЧШЕННАЯ ВЕРСИЯ"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Белый список системных модулей
            module_name = file_path.stem
            if module_name in ['loader', 'system_utils', 'stats']:
                return True  # Пропускаем проверку для системных модулей
            
            # Список опасных операций
            dangerous_patterns = [
                'os.system', 'subprocess.call', 'eval(', 'exec(',
                'shutil.rmtree', '__import__', 'delete_account', 'log_out'
            ]
            
            # Разрешаем os.remove но только в определенных случаях
            if 'os.remove' in content:
                # Проверяем контекст использования os.remove
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'os.remove' in line and not any(safe in line for safe in ['# safe', '# разрешено']):
                        self.logger.warning(f"🚨 Обнаружена опасная операция в {file_path}: os.remove")
                        return False
            
            for pattern in dangerous_patterns:
                if pattern in content:
                    self.logger.warning(f"🚨 Обнаружена опасная операция в {file_path}: {pattern}")
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки безопасности: {e}")
            return False
    
    async def unload_module(self, module_name: str) -> bool:
        """Выгружает модуль"""
        if module_name in self.modules:
            try:
                # Вызываем функцию unregister если она есть
                module = self.modules[module_name]['module']
                if hasattr(module, 'unregister'):
                    await module.unregister(self.bot)
                
                # Удаляем из системных модулей
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                del self.modules[module_name]
                
                # Обновляем список команд
                self.update_all_commands()
                
                self.logger.info(f"🗑️ Модуль {module_name} выгружен")
                return True
            except Exception as e:
                self.logger.error(f"❌ Ошибка выгрузки модуля {module_name}: {e}")
                return False
        return False
    
    def list_modules(self) -> Dict[str, Any]:
        """Возвращает список всех модулей"""
        return self.modules
    
    def get_module_commands(self, module_name: str) -> List[str]:
        """Возвращает команды модуля"""
        if module_name in self.modules:
            return self.modules[module_name].get('commands', [])
        return []
    
    def get_all_commands(self) -> Dict[str, Any]:
        """Возвращает все команды всех модулей"""
        return self.all_commands
    
    def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """Возвращает информацию о модуля"""
        if module_name in self.modules:
            return self.modules[module_name]
        return {}
    
    def update_all_commands(self):
        """Обновляет общий список всех команд"""
        self.all_commands = {}
        for module_name, module_info in self.modules.items():
            if module_info['loaded']:
                self.all_commands[module_name] = {
                    'commands': module_info['commands'],
                    'description': module_info['description']
                }
    
    def get_all_commands_count(self) -> int:
        """Возвращает общее количество команд"""
        count = 0
        for module_info in self.all_commands.values():
            count += len(module_info['commands'])
        return count
