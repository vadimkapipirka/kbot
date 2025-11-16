"""
Системные утилиты Kbot
Пинг, перезапуск и другие системные команды
"""

from telethon import events
import time
import os
import sys
import subprocess

async def register(bot):
    @bot.client.on(events.NewMessage(pattern=r'\.pingq'))
    async def pingq_handler(event):
        """Альтернативная команда пинга (без конфликта с системной)"""
        start = time.time()
        message = await event.reply('🏓')
        end = time.time()
        ping_time = round((end - start) * 1000, 2)
        await message.edit(f'🏓 Pong! `{ping_time}ms` (альтернативная команда)')

async def unregister(bot):
    """Выгрузка модуля"""
    pass
