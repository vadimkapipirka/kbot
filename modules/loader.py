from telethon import events
import requests
import os

def setup(client, OWNER_ID):

    modules_path = os.path.join(os.getcwd(), "modules")

    # .klm URL — скачать модуль
    @client.on(events.NewMessage(from_users=OWNER_ID, pattern=r"\.klm (.+)"))
    async def download_module(event):
        url = event.pattern_match.group(1)
        name = url.split("/")[-1]

        try:
            data = requests.get(url).text
            with open(f"{modules_path}/{name}", "w") as f:
                f.write(data)

            await event.respond(f"✅ Модуль `{name}` скачан!")
        except Exception as e:
            await event.respond(f"❌ Ошибка: `{e}`")

    # .kun name — удалить модуль
    @client.on(events.NewMessage(from_users=OWNER_ID, pattern=r"\.kun (.+)"))
    async def delete_module(event):
        name = event.pattern_match.group(1)
        file = f"{modules_path}/{name}.py"

        try:
            os.remove(file)
            await event.respond(f"🗑 Модуль `{name}` удалён!")
        except:
            await event.respond("❌ Такого модуля нет!")

    # .reload — перезагрузить все модули
    @client.on(events.NewMessage(from_users=OWNER_ID, pattern=r"\.reload"))
    async def reload(event):
        await event.respond("♻ Модули перезагружены!")
        raise SystemExit
