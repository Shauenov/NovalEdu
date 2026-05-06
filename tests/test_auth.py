import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.core.security import hash_password

@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "full_name": "New User",
            "group_type": "D",
            "course_year": 2
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "data" in data
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, db_session: AsyncSession):
    # Setup
    user = User(
        email="login_test@example.com",
        full_name="Login Test",
        password_hash=hash_password("securepass"),
        role="student",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()

    # Act
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "login_test@example.com", "password": "securepass"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]

@pytest.mark.asyncio
async def test_login_failure(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
