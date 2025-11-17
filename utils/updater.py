"""
Модуль проверки обновлений для Kbot 3.0
Проверяет наличие новых версий на GitHub и уведомляет пользователя
"""

import aiohttp
import asyncio
import os
import logging
from typing import Optional, Tuple
import json

logger = logging.getLogger("Updater")


class UpdateChecker:
    def __init__(self, repo_owner: str, repo_name: str, current_version: str = "3.0"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.latest_version = None
        self.update_url = f"https://github.com/{repo_owner}/{repo_name}"
        self.last_check = None

    async def check_for_updates(self) -> Tuple[bool, Optional[str]]:
        """
        Проверяет наличие обновлений на GitHub
        Возвращает (is_update_available, latest_version)
        """
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"

            headers = {
                'User-Agent': 'Kbot-Updater-3.0',
                'Accept': 'application/vnd.github.v3+json'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.latest_version = data.get('tag_name', '').lstrip('v')

                        # Исправление: если тег называется "release", считаем что это последняя версия
                        if self.latest_version.lower() == 'release':
                            self.latest_version = '3.0'
                            
                        if self.latest_version and self.is_newer_version(self.latest_version):
                            logger.info(f"🔔 Доступно обновление: {self.latest_version}")
                            return True, self.latest_version
                        else:
                            logger.info("✅ Бот обновлен до последней версии")
                            return False, self.latest_version
                    else:
                        return await self.check_via_tags()

        except asyncio.TimeoutError:
            logger.warning("⚠️ Таймаут при проверке обновлений")
            return False, None
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке обновлений: {e}")
            return False, None

    async def check_via_tags(self) -> Tuple[bool, Optional[str]]:
        """Альтернативная проверка через список тегов"""
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/tags"

            headers = {
                'User-Agent': 'Kbot-Updater-3.0',
                'Accept': 'application/vnd.github.v3+json'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        tags = await response.json()
                        if tags and len(tags) > 0:
                            self.latest_version = tags[0].get('name', '').lstrip('v')
                            # Исправление для тега "release"
                            if self.latest_version.lower() == 'release':
                                self.latest_version = '3.0'
                            if self.is_newer_version(self.latest_version):
                                return True, self.latest_version
            return False, None
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке тегов: {e}")
            return False, None

    def is_newer_version(self, latest_version: str) -> bool:
        """Сравнивает версии и определяет, является ли удаленная версия более новой"""
        if not latest_version:
            return False

        try:
            current_parts = self.current_version.split('.')
            latest_parts = latest_version.split('.')

            for i in range(max(len(current_parts), len(latest_parts))):
                current_part = int(current_parts[i]) if i < len(current_parts) else 0
                latest_part = int(latest_parts[i]) if i < len(latest_parts) else 0

                if latest_part > current_part:
                    return True
                elif latest_part < current_part:
                    return False

            return False

        except (ValueError, IndexError):
            # Если версии не в числовом формате, сравниваем как строки
            return latest_version > self.current_version

    def get_update_message(self, latest_version: str) -> str:
        """Возвращает сообщение о доступном обновлении"""
        return f"""
🔄 **Доступно обновление Kbot!**

Текущая версия: `v{self.current_version}`
Новая версия: `v{latest_version}`

📥 **Как обновить:**
1. Используйте команду `.update` в боте
2. Или скачайте вручную:
{self.update_url}

💡 **Рекомендация:** Перед обновлением сделайте бэкап важных данных командой `.backup`
"""

    async def get_changelog(self, latest_version: str) -> str:
        """Получает changelog для версии с улучшенным форматированием"""
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/tags/v{latest_version}"

            headers = {
                'User-Agent': 'Kbot-Updater-3.0',
                'Accept': 'application/vnd.github.v3+json'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        body = data.get('body', '')
                        if body:
                            # Форматируем changelog для лучшего отображения
                            formatted_body = body.replace('##', '**').replace('-', '•')
                            return f"📋 **Changelog v{latest_version}:**\n\n{formatted_body}"
            return "📋 Информация об изменениях недоступна"
        except Exception as e:
            logger.error(f"❌ Ошибка получения changelog: {e}")
            return "📋 Не удалось загрузить информацию об изменениях"

    async def get_detailed_update_info(self, latest_version: str) -> str:
        """Возвращает подробную информацию об обновлении"""
        changelog = await self.get_changelog(latest_version)
        
        message = f"""
🔄 **Доступно обновление Kbot!**

**Версии:**
• Текущая: `v{self.current_version}`
• Новая: `v{latest_version}`

{changelog}

📥 **Способы обновления:**
1. **Автоматически:** Используйте команду `.update`
2. **Вручную:** {self.update_url}

🔒 **Рекомендации:**
• Сделайте бэкап командой `.backup`
• Обновите зависимости если нужно
""".strip()
        
        return message


# Глобальный экземпляр Updater
update_checker = UpdateChecker(
    repo_owner="vadimkapipirka",
    repo_name="kbot",
    current_version="3.0"
)


async def check_for_updates() -> Tuple[bool, Optional[str]]:
    """Проверяет наличие обновлений"""
    return await update_checker.check_for_updates()


async def notify_about_update(bot, chat_id: int):
    """Отправляет уведомление об обновлении в указанный чат"""
    try:
        update_available, latest_version = await check_for_updates()
        if update_available:
            message = await update_checker.get_detailed_update_info(latest_version)
            await bot.client.send_message(chat_id, message)
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомления: {e}")
        return False


async def manual_update_check(bot, event):
    """Ручная проверка обновлений с улучшенным выводом"""
    try:
        await bot.safe_reply(event, "🔄 Проверяю обновления...")

        update_available, latest_version = await check_for_updates()
        if update_available:
            message = await update_checker.get_detailed_update_info(latest_version)
            await bot.safe_reply(event, message)
        else:
            if latest_version:
                await bot.safe_reply(event, f"✅ **Kbot обновлен!**\n\nТекущая версия: `v{update_checker.current_version}`\nПоследняя версия: `v{latest_version}`\n\nВаш бот работает на актуальной версии! 🎉")
            else:
                await bot.safe_reply(event, f"✅ **Kbot обновлен!**\n\nТекущая версия: `v{update_checker.current_version}`\n\nНе удалось проверить последнюю версию, но ваш бот работает! 🚀")

    except Exception as e:
        await bot.safe_reply(event, f"❌ Ошибка при проверке обновлений: {str(e)}")
