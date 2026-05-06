import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.core.security import hash_password, create_access_token
import uuid
from datetime import datetime, timedelta, timezone

@pytest.mark.asyncio
async def test_appointment_lifecycle(async_client: AsyncClient, db_session: AsyncSession):
    # Setup users
    conductor_id = uuid.uuid4()
    conductor = User(
        id=conductor_id,
        email="conductor_appt@test.com",
        full_name="Conductor",
        password_hash=hash_password("pass"),
        role="conductor",
        is_active=True
    )
    student_id = uuid.uuid4()
    student = User(
        id=student_id,
        email="student_appt@test.com",
        full_name="Student",
        password_hash=hash_password("pass"),
        role="student",
        is_active=True
    )
    db_session.add_all([conductor, student])
    await db_session.commit()

    conductor_token = create_access_token(user_id=conductor_id, role="conductor", email="conductor_appt@test.com")
    student_token = create_access_token(user_id=student_id, role="student", email="student_appt@test.com")

    # 1. Conductor creates a slot
    start_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    end_time = (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()
    
    response = await async_client.post(
        "/api/v1/appointments/slots",
        headers={"Authorization": f"Bearer {conductor_token}"},
        json={"slots": [{"start_time": start_time, "end_time": end_time, "duration_min": 60}]}
    )
    assert response.status_code == 201
    slot_id = response.json()["data"][0]["id"]

    # 2. Student lists slots
    response = await async_client.get(
        "/api/v1/appointments/slots",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1

    # 3. Student books appointment
    response = await async_client.post(
        "/api/v1/appointments",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"slot_id": slot_id, "notes": "Need help"}
    )
    assert response.status_code == 201
    appt_id = response.json()["data"]["id"]

    # 4. Conductor completes appointment
    response = await async_client.patch(
        f"/api/v1/appointments/{appt_id}/complete",
        headers={"Authorization": f"Bearer {conductor_token}"}
    )
    assert response.status_code == 200
