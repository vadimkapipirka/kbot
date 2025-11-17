"""
Модуль показывает случайный факт. Полезно, когда хочется удивить собеседника чем-то интересным.
"""

import random
from telethon import events

FACTS = [
    "Honey never spoils — учёные находили мёд возрастом 3000 лет, и он был съедобен.",
    "У осьминогов три сердца, и кровь голубого цвета.",
    "Шахматных партий больше, чем атомов в известной Вселенной.",
    "99% всей массы Солнечной системы — это Солнце.",
    "У бабочек есть органы вкуса на ногах."
]

async def register(bot):
    @bot.client.on(events.NewMessage(pattern=r'\.fact'))
    async def send_fact(event):
        fact = random.choice(FACTS)
        await event.reply(fact)

async def unregister(bot):
    pass