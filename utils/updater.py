"""
Модуль проверки обновлений для Kbot
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
    def __init__(self, repo_owner: str, repo_name: str, current_version: str = "2.0"):
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
                'User-Agent': 'Kbot-Updater',
                'Accept': 'application/vnd.github.v3+json'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.latest_version = data.get('tag_name', '').lstrip('v')

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
                'User-Agent': 'Kbot-Updater',
                'Accept': 'application/vnd.github.v3+json'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        tags = await response.json()
                        if tags and len(tags) > 0:
                            self.latest_version = tags[0].get('name', '').lstrip('v')
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

💡 **Что нового:**
- Исправления ошибок
- Улучшение производительности
- Новые функции

🔒 **Рекомендация:** Перед обновлением сделайте бэкап важных данных командой `.backup`
"""

    async def get_changelog(self, latest_version: str) -> str:
        """Получает changelog для версии"""
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/tags/v{latest_version}"

            headers = {
                'User-Agent': 'Kbot-Updater',
                'Accept': 'application/vnd.github.v3+json'
            }

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        body = data.get('body', '')
                        if body:
                            return f"📋 **Changelog v{latest_version}:**\n\n{body}"
            return "📋 Информация об изменениях недоступна"
        except Exception as e:
            logger.error(f"❌ Ошибка получения changelog: {e}")
            return "📋 Не удалось загрузить информацию об изменениях"


# Глобальный экземпляр Updater
update_checker = UpdateChecker(
    repo_owner="vadimkapipirka",
    repo_name="kbot",
    current_version="2.0"
)


async def check_for_updates() -> Tuple[bool, Optional[str]]:
    """Проверяет наличие обновлений"""
    return await update_checker.check_for_updates()


async def notify_about_update(bot, chat_id: int):
    """Отправляет уведомление об обновлении в указанный чат"""
    try:
        update_available, latest_version = await check_for_updates()
        if update_available:
            message = update_checker.get_update_message(latest_version)
            await bot.client.send_message(chat_id, message)

            changelog = await update_checker.get_changelog(latest_version)
            await bot.client.send_message(chat_id, changelog)

            return True
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомления: {e}")
        return False


async def manual_update_check(bot, event):
    """Ручная проверка обновлений с отправкой результата"""
    try:
        await bot.safe_reply(event, "🔄 Проверяю обновления...")

        update_available, latest_version = await check_for_updates()
        if update_available:
            message = update_checker.get_update_message(latest_version)
            changelog = await update_checker.get_changelog(latest_version)

            await bot.safe_reply(event, message)
            await bot.client.send_message(event.chat_id, changelog)
        else:
            if latest_version:
                await bot.safe_reply(event, f"✅ У вас актуальная версия Kbot `v{update_checker.current_version}` (последняя: `v{latest_version}`)")
            else:
                await bot.safe_reply(event, f"✅ У вас актуальная версия Kbot `v{update_checker.current_version}`")

    except Exception as e:
        await bot.safe_reply(event, f"❌ Ошибка при проверке обновлений: {str(e)}")
