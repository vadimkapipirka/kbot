"""
Модуль спама для юзербота.
Команда: .спам <кол-во> <текст>
Пример: .спам 10 привет
"""

import asyncio
from telethon import events

async def register(bot):
    @bot.client.on(events.NewMessage(pattern=r'\.спам(?: |$)(.*)'))
    async def spam_handler(event):
        args = event.raw_text.split(maxsplit=2)

        # .спам <кол-во> <текст>
        if len(args) < 3:
            await event.reply("❗ Использование: .спам <кол-во> <текст>")
            return

        try:
            count = int(args[1])
        except ValueError:
            await event.reply("❗ Количество должно быть числом")
            return

        text = args[2]

        # Удаляем команду из чата
        try:
            await event.delete()
        except:
            pass

        # Выполняем спам
        for _ in range(count):
            await bot.client.send_message(event.chat_id, text)
            await asyncio.sleep(0.1)

async def unregister(bot):
    pass