from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from dotenv import load_dotenv
import os
import asyncio
import re

load_dotenv()
api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")
client = TelegramClient('session', api_id, api_hash)

async def fetch_messages(channel, limit=10):
    messages = []
    try:
        await client.start()
        print(f"Попытка подключения к каналу: {channel}")
        entity = await client.get_entity(channel)
        print(f"Канал найден: {entity.title}")
        async for message in client.iter_messages(channel, limit=limit):
            text = message.text or ""
            # Extract coordinates
            coords = re.search(r'(\d+\.\d+)\s*,\s*(\d+\.\d+)', text)
            location = f"POINT({coords.group(2)} {coords.group(1)})" if coords else None
            # Determine event type
            event_type = (
                'артобстрел' if 'артобстрел' in text.lower() else
                'эвакуация' if 'эвакуация' in text.lower() else
                'другое'
            )
            messages.append({
                "text": text,
                "channel": channel,
                "created_at": message.date,
                "location": location,
                "event_type": event_type
            })
        if not messages:
            print(f"Сообщения в канале {channel} не найдены.")
    except SessionPasswordNeededError:
        print("Требуется двухфакторная аутентификация.")
    except FloodWaitError as e:
        print(f"Слишком много запросов. Ждите {e.seconds} секунд.")
        await asyncio.sleep(e.seconds)
        return await fetch_messages(channel, limit)
    except Exception as e:
        print(f"Ошибка при получении сообщений: {e}")
    finally:
        await client.disconnect()
    return messages

if __name__ == "__main__":
    channel = "@Emerg_System"
    try:
        messages = asyncio.run(fetch_messages(channel, limit=5))
        if messages:
            for msg in messages:
                print(f"Сообщение: {msg['text']}\nКанал: {msg['channel']}\nВремя: {msg['created_at']}\n")
        else:
            print("Сообщений нет.")
    except Exception as e:
        print(f"Ошибка при запуске: {e}")