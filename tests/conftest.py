import sys
from unittest.mock import MagicMock
# Mock magic module before any app imports due to windows libmagic issues
sys.modules['magic'] = MagicMock()

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport
from collections.abc import AsyncGenerator

from app.main import app
from app.database import Base, get_db
from app.config import settings
from sqlalchemy.pool import NullPool

# Override database URL to use test database
db_name = settings.database_url.split("/")[-1]
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + f"/{db_name}_test"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create test database tables before tests, drop them after."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine_test.dispose()

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional scope around each test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback() # rollback any changes made during the test

@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client that uses the overridden db session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Manually setup redis for tests since ASGITransport doesn't trigger lifespan
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
        
    app.dependency_overrides.clear()
    await app.state.redis.aclose()
