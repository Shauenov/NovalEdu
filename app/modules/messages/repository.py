from uuid import UUID

from sqlalchemy import delete, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messages.models import Conversation, Message
from app.modules.profile.models import StudentProfile
from app.modules.users.models import User


class MessagesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_conversation(self, convo_id: UUID) -> Conversation | None:
        result = await self.db.execute(select(Conversation).where(Conversation.id == convo_id))
        return result.scalar_one_or_none()

    async def get_or_create_conversation(self, student_id: UUID, conductor_id: UUID) -> Conversation:
        result = await self.db.execute(
            select(Conversation).where(Conversation.student_id == student_id, Conversation.conductor_id == conductor_id)
        )
        convo = result.scalar_one_or_none()
        if convo:
            return convo
        convo = Conversation(student_id=student_id, conductor_id=conductor_id)
        self.db.add(convo)
        await self.db.flush()
        await self.db.refresh(convo)
        return convo

    async def list_conversations_for_user(self, user_id: UUID, is_conductor: bool) -> list[Conversation]:
        if is_conductor:
            result = await self.db.execute(select(Conversation).where(Conversation.conductor_id == user_id))
        else:
            result = await self.db.execute(select(Conversation).where(Conversation.student_id == user_id))
        return result.scalars().all()

    async def list_messages(self, convo_id: UUID, limit: int = 50, offset: int = 0) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == convo_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_messages_with_sender(
        self, convo_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[tuple[Message, User]]:
        result = await self.db.execute(
            select(Message, User)
            .join(User, User.id == Message.sender_id)
            .where(Message.conversation_id == convo_id)
            .order_by(Message.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.all()

    async def create_message(
        self,
        conversation_id: UUID,
        sender_id: UUID,
        body: str,
        image_object_key: str | None = None,
        image_content_type: str | None = None,
        image_size: int | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            body=body,
            image_object_key=image_object_key,
            image_content_type=image_content_type,
            image_size=image_size,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=msg.created_at)
        )
        await self.db.flush()
        return msg

    async def mark_conversation_read(self, convo_id: UUID, reader_id: UUID) -> int:
        result = await self.db.execute(
            update(Message)
            .where(
                Message.conversation_id == convo_id,
                Message.sender_id != reader_id,
                Message.is_read == False,
            )
            .values(is_read=True, read_at=func.now())
        )
        await self.db.flush()
        return result.rowcount or 0

    async def list_conversation_ids_by_filters(
        self,
        conductor_id: UUID,
        group_type: str | None = None,
        ielts_passed: bool | None = None,
    ) -> list[UUID]:
        stmt = (
            select(Conversation.id)
            .join(User, User.id == Conversation.student_id)
            .join(StudentProfile, StudentProfile.user_id == User.id, isouter=True)
            .where(Conversation.conductor_id == conductor_id)
        )

        if group_type:
            stmt = stmt.where(StudentProfile.group_type == group_type)
        if ielts_passed is not None:
            stmt = stmt.where(StudentProfile.ielts_passed == ielts_passed)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_conversation(self, convo: Conversation) -> None:
        await self.db.delete(convo)
        await self.db.flush()
