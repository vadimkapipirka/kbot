from telethon import events
import time

async def register(bot):
    @bot.client.on(events.NewMessage(pattern='\.ping'))
    async def ping_handler(event):
        start_time = time.time()
        message = await event.reply('🏓 Pong!')
        end_time = time.time()
        ping_time = round((end_time - start_time) * 1000, 2)
        await message.edit(f'🏓 Pong! `{ping_time}ms`')
