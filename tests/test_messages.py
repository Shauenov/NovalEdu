import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.core.security import hash_password, create_access_token
from app.config import settings
import uuid

@pytest.mark.asyncio
async def test_messages_flow(async_client: AsyncClient, db_session: AsyncSession):
    student_id = uuid.uuid4()
    student = User(
        id=student_id,
        email="student_msg@test.com",
        full_name="Student",
        password_hash=hash_password("pass"),
        role="student",
        is_active=True
    )
    conductor = User(
        id=uuid.uuid4(),
        email=settings.conductor_email,
        full_name="System Conductor",
        password_hash=hash_password("pass"),
        role="conductor",
        is_active=True
    )
    db_session.add(student)
    db_session.add(conductor)
    await db_session.commit()

    token = create_access_token(user_id=student_id, role="student", email="student_msg@test.com")

    # 1. Get/Create my conversation
    response = await async_client.get(
        "/api/v1/messages/conversations/my",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    convo_id = response.json()["data"]["id"]

    # 2. Send message
    response = await async_client.post(
        f"/api/v1/messages/conversations/{convo_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": "Hello world!"}
    )
    assert response.status_code == 201
    
    # 3. List messages
    response = await async_client.get(
        f"/api/v1/messages/conversations/{convo_id}/messages",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    msgs = response.json()["data"]
    assert len(msgs) == 1
    assert msgs[0]["body"] == "Hello world!"
