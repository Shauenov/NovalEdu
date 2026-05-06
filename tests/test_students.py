import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.profile.models import StudentProfile
from app.core.security import hash_password, create_access_token
import uuid

@pytest.mark.asyncio
async def test_get_student_profile(async_client: AsyncClient, db_session: AsyncSession):
    # Setup user
    student_id = uuid.uuid4()
    student = User(
        id=student_id,
        email="student_profile@test.com",
        full_name="Profile Test",
        password_hash=hash_password("pass"),
        role="student",
        is_active=True
    )
    profile = StudentProfile(
        user_id=student_id,
        group_type="D",
        course_year=1,
        gpa=4.0
    )
    db_session.add(student)
    await db_session.flush()
    db_session.add(profile)
    await db_session.commit()

    # Create auth token
    token = create_access_token(user_id=student_id, role="student", email="student_profile@test.com")
    
    # Act
    response = await async_client.get(
        f"/api/v1/students/{student_id}/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["group_type"] == "D"
    assert data["course_year"] == 1
    assert float(data["gpa"]) == 4.0

@pytest.mark.asyncio
async def test_update_student_profile(async_client: AsyncClient, db_session: AsyncSession):
    # Setup user
    student_id = uuid.uuid4()
    student = User(
        id=student_id,
        email="student_profile2@test.com",
        full_name="Profile Test 2",
        password_hash=hash_password("pass"),
        role="student",
        is_active=True
    )
    profile = StudentProfile(
        user_id=student_id,
        group_type="D",
        course_year=2,
        gpa=3.5
    )
    db_session.add(student)
    await db_session.flush()
    db_session.add(profile)
    await db_session.commit()

    # Create auth token
    token = create_access_token(user_id=student_id, role="student", email="student_profile2@test.com")
    
    # Act
    response = await async_client.put(
        f"/api/v1/students/{student_id}/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"gpa": 3.8, "ielts_passed": True, "ielts_score": 7.0}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert float(data["gpa"]) == 3.8
    assert data["ielts_passed"] is True
    assert float(data["ielts_score"]) == 7.0
