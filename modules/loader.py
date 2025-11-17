"""
Системный модуль для загрузки модулей
Безопасная версия с проверкой прав
"""

from telethon import events
import requests
import os

async def register(bot):
    """Регистрация модуля загрузчика"""

    modules_path = os.path.join(os.getcwd(), "modules")

    # .klm URL — скачать модуль (только для админа)
    @bot.client.on(events.NewMessage(pattern=r"\.klm (.+)"))
    async def download_module(event):
        """Скачать модуль по URL"""
        # Проверка прав доступа
        if not bot.is_admin(event.sender_id):
            return
        
        url = event.pattern_match.group(1)
        name = url.split("/")[-1]

        try:
            data = requests.get(url).text
            with open(f"{modules_path}/{name}", "w") as f:
                f.write(data)

            await event.respond(f"✅ Модуль `{name}` скачан!")
        except Exception as e:
            await event.respond(f"❌ Ошибка: `{e}`")

    # .kun name — удалить модуль (только для админа)
    @bot.client.on(events.NewMessage(pattern=r"\.kun (.+)"))
    async def delete_module(event):
        """Удалить модуль по имени"""
        # Проверка прав доступа
        if not bot.is_admin(event.sender_id):
            return
            
        name = event.pattern_match.group(1)
        file = f"{modules_path}/{name}.py"

        try:
            os.remove(file)  # safe: системная операция
            await event.respond(f"🗑 Модуль `{name}` удалён!")
        except:
            await event.respond("❌ Такого модуля нет!")

    # .reload — перезагрузить все модули (только для админа)
    @bot.client.on(events.NewMessage(pattern=r"\.reload"))
    async def reload(event):
        """Перезагрузить все модули"""
        # Проверка прав доступа
        if not bot.is_admin(event.sender_id):
            return
            
        await event.respond("♻ Модули перезагружены!")
        raise SystemExit

async def unregister(bot):
    """Выгрузка модуля"""
    pass
