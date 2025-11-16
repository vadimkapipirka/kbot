import ast
import os
from pathlib import Path

def convert_old_module_to_new(file_path: Path) -> bool:
    """Конвертирует старый модуль в новый формат"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим модуль
        tree = ast.parse(content)
        
        # Ищем импорты и обработчики
        imports = []
        handlers = []
        module_doc = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                imports.append(ast.unparse(node))
            elif isinstance(node, ast.FunctionDef) and hasattr(node, 'decorator_list'):
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and
                        isinstance(decorator.func, ast.Attribute) and
                        decorator.func.attr == 'register'):
                        # Это старый обработчик
                        pattern = None
                        for arg in decorator.args:
                            if (isinstance(arg, ast.Call) and
                                isinstance(arg.func, ast.Attribute) and
                                arg.func.attr == 'NewMessage'):
                                for kw in arg.keywords:
                                    if kw.arg == 'pattern':
                                        if isinstance(kw.value, ast.Constant):
                                            pattern = kw.value.value
                        if pattern:
                            handlers.append({
                                'name': node.name,
                                'pattern': pattern,
                                'code': ast.get_source_segment(content, node)
                            })
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                # Это может быть docstring
                if module_doc is None:
                    module_doc = node.value.value
        
        if not handlers:
            return False
        
        # Создаем новый модуль
        new_content = '"""\n'
        if module_doc:
            new_content += module_doc + '\n'
        else:
            new_content += f'Автоматически сконвертированный модуль {file_path.stem}\n'
        new_content += '"""\n\n'
        
        # Добавляем импорты
        for imp in imports:
            if 'events.register' not in imp:  # Убираем старый импорт
                new_content += imp + '\n'
        new_content += '\n'
        
        # Добавляем функцию register
        new_content += 'async def register(bot):\n'
        
        for handler in handlers:
            new_content += f'    {handler["code"].replace("async def", "    async def", 1)}\n\n'
        
        # Добавляем функцию unregister
        new_content += 'async def unregister(bot):\n'
        new_content += '    """Выгрузка модуля"""\n'
        new_content += '    pass\n'
        
        # Создаем backup и записываем новый файл
        backup_path = file_path.with_suffix('.py.old')
        if not backup_path.exists():
            os.rename(file_path, backup_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
        
    except Exception as e:
        print(f"Ошибка конвертации {file_path}: {e}")
        return False

def convert_all_old_modules():
    """Конвертирует все старые модули в папке modules"""
    modules_path = Path("modules")
    converted = 0
    
    for file in modules_path.glob("*.py"):
        if file.name.startswith("_") or file.name in ['system_help.py', 'system_utils.py', 'stats.py']:
            continue
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Проверяем, это старый модуль (есть events.register) но нет async def register
            if 'events.register' in content and 'async def register' not in content:
                if convert_old_module_to_new(file):
                    print(f"✅ Сконвертирован: {file.name}")
                    converted += 1
        except Exception as e:
            print(f"❌ Ошибка проверки {file}: {e}")
    
    return converted
