# core/loader.py
import importlib
import os
from pathlib import Path

class ModuleLoader:
    def __init__(self, bot):
        self.bot = bot
        self.modules = {}
        
    async def load_modules(self):
        modules_path = Path("modules")
        for file in modules_path.glob("*.py"):
            if file.name.startswith("_"):
                continue
                
            module_name = file.stem
            try:
                spec = importlib.util.spec_from_file_location(module_name, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, "register"):
                    await module.register(self.bot)
                    self.modules[module_name] = module
                    
            except Exception as e:
                logging.error(f"Ошибка загрузки модуля {module_name}: {e}")
