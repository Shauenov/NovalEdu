import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.core.security import hash_password, create_access_token
import uuid

@pytest.mark.asyncio
async def test_create_and_list_tasks(async_client: AsyncClient, db_session: AsyncSession):
    # Setup student
    student_id = uuid.uuid4()
    student = User(
        id=student_id,
        email="student_task@test.com",
        full_name="Task Student",
        password_hash=hash_password("pass"),
        role="student",
        is_active=True
    )
    db_session.add(student)
    await db_session.commit()

    token = create_access_token(user_id=student_id, role="student", email="student_task@test.com")
    
    # Create personal task
    response = await async_client.post(
        "/api/v1/tasks/personal",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "My Personal Task", "description": "Needs to be done", "deadline": "2026-12-31T00:00:00Z"}
    )
    assert response.status_code == 201
    task_id = response.json()["data"]["id"]

    # List tasks
    response = await async_client.get(
        f"/api/v1/students/{student_id}/tasks",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    tasks = response.json()["data"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "My Personal Task"

    # Patch task status
    response = await async_client.patch(
        f"/api/v1/tasks/{task_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "done"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "done"

@pytest.mark.asyncio
async def test_create_conductor_task(async_client: AsyncClient, db_session: AsyncSession):
    # Setup conductor and student
    conductor_id = uuid.uuid4()
    conductor = User(
        id=conductor_id,
        email="conductor_task@test.com",
        full_name="Conductor",
        password_hash=hash_password("pass"),
        role="conductor",
        is_active=True
    )
    student_id = uuid.uuid4()
    student = User(
        id=student_id,
        email="student_conductor_task@test.com",
        full_name="Student",
        password_hash=hash_password("pass"),
        role="student",
        is_active=True
    )
    db_session.add_all([conductor, student])
    await db_session.commit()

    token = create_access_token(user_id=conductor_id, role="conductor", email="conductor_task@test.com")
    
    # Create conductor task for student
    response = await async_client.post(
        f"/api/v1/students/{student_id}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Upload Document", "deadline": "2026-11-30T00:00:00Z", "is_conductor_task": True}
    )
    assert response.status_code == 201
    assert response.json()["data"]["is_conductor_task"] is True
