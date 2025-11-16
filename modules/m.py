"""
Описание вашего модуля
"""

from telethon import events

async def register(bot):
    @bot.client.on(events.NewMessage(pattern=r'\.ваша_команда'))
    async def your_handler(event):
        await event.reply('Привет!')

async def unregister(bot):
    pass
