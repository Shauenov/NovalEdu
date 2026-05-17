#!/usr/bin/env python
import asyncio
import sys
sys.path.insert(0, "/app")

from app.database import AsyncSessionLocal
from app.modules.messages.repository import MessagesRepository

async def get_image():
    async with AsyncSessionLocal() as session:
        repo = MessagesRepository(session)
        msg = await repo.get_messages_with_pagination(None, 0, 1)
        if msg:
            first_msg = msg[0]
            if first_msg.image_object_key:
                print(f"Found image: {first_msg.image_object_key}")
                from app.storage.minio_client import get_public_url
                from app.core.constants import BUCKET_MESSAGES
                url = get_public_url(BUCKET_MESSAGES, first_msg.image_object_key)
                print(f"URL: {url}")
            else:
                print("No image in first message")
        else:
            print("No messages found")

asyncio.run(get_image())
