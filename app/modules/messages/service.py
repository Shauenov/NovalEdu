import io
import uuid
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import BUCKET_MESSAGES
from app.core.exceptions import ForbiddenException, NotFoundException
from app.modules.messages.repository import MessagesRepository
from app.modules.users.repository import UsersRepository
from app.storage.file_validator import validate_image
from app.storage.minio_client import upload_file


class MessagesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MessagesRepository(db)

    def _serialize_message(self, msg, sender) -> dict:
        from app.storage.minio_client import get_public_url
        image_url = get_public_url(BUCKET_MESSAGES, msg.image_object_key) if msg.image_object_key else None
        return {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "sender_name": sender.full_name if sender else None,
            "sender_role": sender.role if sender else None,
            "body": msg.body,
            "image_url": image_url,
            "image_content_type": msg.image_content_type,
            "image_size": msg.image_size,
            "is_read": msg.is_read,
            "read_at": msg.read_at,
            "created_at": msg.created_at,
        }

    async def get_or_create_conversation(self, student_id: UUID, adviser_id: UUID):
        return await self.repo.get_or_create_conversation(student_id, adviser_id)

    async def get_or_create_my_conversation(self, student_id: UUID):
        user_repo = UsersRepository(self.db)
        adviser = await user_repo.get_by_email(settings.ADVISER_email)
        if not adviser:
            raise NotFoundException("Adviser not found")
        return await self.repo.get_or_create_conversation(student_id, adviser.id)

    async def list_conversations_for_user(self, user_id: UUID, is_adviser: bool):
        return await self.repo.list_conversations_for_user(user_id, is_adviser)

    async def list_messages(self, convo_id: UUID, limit: int = 50, offset: int = 0) -> list[dict]:
        rows = await self.repo.list_messages_with_sender(convo_id, limit=limit, offset=offset)
        return [self._serialize_message(msg, sender) for msg, sender in rows]

    async def mark_conversation_read(self, convo_id: UUID, reader_id: UUID) -> None:
        convo = await self.repo.get_conversation(convo_id)
        if not convo:
            raise NotFoundException("Conversation not found")
        if reader_id not in (convo.student_id, convo.adviser_id):
            raise ForbiddenException("Access denied")
        await self.repo.mark_conversation_read(convo_id, reader_id)
        await self.db.commit()

    async def list_conversation_ids_for_broadcast(
        self,
        adviser_id: UUID,
        group_type: str | None = None,
        ielts_passed: bool | None = None,
    ) -> list[UUID]:
        return await self.repo.list_conversation_ids_by_filters(
            adviser_id=adviser_id,
            group_type=group_type,
            ielts_passed=ielts_passed,
        )

    async def send_message(self, conversation_id: UUID, sender_id: UUID, body: str):
        msg = await self.repo.create_message(conversation_id, sender_id, body)
        await self.db.commit()
        sender = await UsersRepository(self.db).get_by_id(sender_id)
        await self._notify_message(conversation_id, sender_id, body)
        return self._serialize_message(msg, sender)

    async def send_message_with_image(
        self,
        conversation_id: UUID,
        sender_id: UUID,
        image: UploadFile,
        body: str | None = None,
    ):
        image_bytes = await image.read()
        mime = validate_image(image_bytes, settings.max_image_size_bytes)
        image_key = f"{conversation_id}/{sender_id}/{uuid.uuid4().hex}"
        upload_file(BUCKET_MESSAGES, image_key, io.BytesIO(image_bytes), len(image_bytes), mime)

        text = (body or "").strip() or "[Image]"
        msg = await self.repo.create_message(
            conversation_id,
            sender_id,
            text,
            image_object_key=image_key,
            image_content_type=mime,
            image_size=len(image_bytes),
        )
        await self.db.commit()

        sender = await UsersRepository(self.db).get_by_id(sender_id)
        await self._notify_message(conversation_id, sender_id, text)
        return self._serialize_message(msg, sender)

    async def _notify_message(self, conversation_id: UUID, sender_id: UUID, body: str) -> None:
        preview = (body or "").strip() or "[Image]"

        try:
            convo = await self.repo.get_conversation(conversation_id)
            if not convo:
                raise NotFoundException("Conversation not found")

            recipient_id = convo.adviser_id if sender_id == convo.student_id else convo.student_id
            from app.modules.notifications.service import NotificationsService
            from app.workers.email_tasks import send_email_task

            user_repo = UsersRepository(self.db)
            recipient = await user_repo.get_by_id(recipient_id)
            sender = await user_repo.get_by_id(sender_id)
            if recipient:
                notifier = NotificationsService(self.db)
                await notifier.create_notification(
                    user_id=recipient.id,
                    notification_type="new_message",
                    title="New message",
                    body=preview[:200],
                    source_id=conversation_id,
                    source_type="conversation",
                )
                await self.db.commit()

                if recipient.email:
                    send_email_task.delay(
                        to=recipient.email,
                        subject="New message",
                        template="new_message.html",
                        context={
                            "full_name": recipient.full_name,
                            "sender_name": sender.full_name if sender else "Someone",
                            "message_preview": preview[:200],
                        },
                    )
        except Exception:
            pass

    async def broadcast(
        self,
        body: str,
        conversation_ids: list[UUID],
        sender_id: UUID,
        image_object_key: str | None = None,
        image_content_type: str | None = None,
        image_size: int | None = None,
    ):
        """Create a message in each conversation from the sender."""
        preview = (body or "").strip() or "[Image]"
        msgs = []
        for convo_id in conversation_ids:
            m = await self.repo.create_message(
                convo_id,
                sender_id,
                preview,
                image_object_key=image_object_key,
                image_content_type=image_content_type,
                image_size=image_size,
            )
            msgs.append(m)
        await self.db.commit()

        try:
            from app.modules.notifications.service import NotificationsService
            from app.modules.users.repository import UsersRepository
            from app.workers.email_tasks import send_email_task

            user_repo = UsersRepository(self.db)
            notifier = NotificationsService(self.db)
            sender = await user_repo.get_by_id(sender_id)

            for convo_id in conversation_ids:
                convo = await self.repo.get_conversation(convo_id)
                if not convo:
                    continue
                recipient_id = (
                    convo.adviser_id if sender_id == convo.student_id else convo.student_id
                )
                recipient = await user_repo.get_by_id(recipient_id)
                if not recipient:
                    continue

                await notifier.create_notification(
                    user_id=recipient.id,
                    notification_type="new_message",
                    title="New message",
                    body=preview[:200],
                    source_id=convo_id,
                    source_type="conversation",
                )

                if recipient.email:
                    send_email_task.delay(
                        to=recipient.email,
                        subject="New message",
                        template="new_message.html",
                        context={
                            "full_name": recipient.full_name,
                            "sender_name": sender.full_name if sender else "Someone",
                            "message_preview": preview[:200],
                        },
                    )

            await self.db.commit()
        except Exception:
            pass
        return msgs

    async def broadcast_with_image(
        self,
        body: str | None,
        conversation_ids: list[UUID],
        sender_id: UUID,
        image: UploadFile,
    ):
        image_bytes = await image.read()
        mime = validate_image(image_bytes, settings.max_image_size_bytes)
        image_key = f"broadcast/{sender_id}/{uuid.uuid4().hex}"
        upload_file(BUCKET_MESSAGES, image_key, io.BytesIO(image_bytes), len(image_bytes), mime)

        text = (body or "").strip() or "[Image]"
        return await self.broadcast(
            text,
            conversation_ids,
            sender_id,
            image_object_key=image_key,
            image_content_type=mime,
            image_size=len(image_bytes),
        )
