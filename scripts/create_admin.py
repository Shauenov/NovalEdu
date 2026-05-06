import asyncio
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.modules.users.models import User
from app.core.security import hash_password
from app.config import settings

async def create_admin():
    async with AsyncSessionLocal() as session:
        # Check if conductor exists
        stmt = select(User).where(User.email == settings.conductor_email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            print(f"Conductor with email {settings.conductor_email} already exists.")
            return

        new_user = User(
            email=settings.conductor_email,
            full_name="Nobal Conductor",
            password_hash=hash_password(settings.conductor_initial_password),
            role="conductor",
            is_active=True
        )
        session.add(new_user)
        await session.commit()
        print(f"Successfully created conductor with email: {settings.conductor_email}")

if __name__ == "__main__":
    print("Creating admin user...")
    asyncio.run(create_admin())
