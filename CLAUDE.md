# Nobal Education — Project Overview

## Architecture
- backend/ — FastAPI + PostgreSQL (async) + Docker
- frontend/ — (not included in this repository)
- mobile/ — separate team / separate client

## Backend stack (from the code)
- FastAPI: 0.111.0 (see `requirements.txt`)
- Pydantic: v2 (the repo uses `pydantic==2.7.1` and `Model.model_validate` API)
- SQLAlchemy: 2.x with asyncio (`sqlalchemy[asyncio]==2.0.30`) — async mode
- DB driver: `asyncpg` (async Postgres driver)
- Alembic: `alembic==1.13.1` for migrations
- Tests: `pytest` + `pytest-asyncio`

## 📁 Module Structure

Each module in `app/modules/<module_name>/` follows this pattern:

```
app/modules/auth/
├── models.py          # SQLAlchemy ORM models
├── schemas.py         # Pydantic v2 request/response DTOs
├── repository.py      # Async database queries
├── service.py         # Business logic
└── router.py          # FastAPI endpoints
```

**Application factory:** `app/main.py` (creates FastAPI app and mounts routers under `/api/v1`)

**Routers aggregator:** `app/routers.py` (includes module routers with `include_router`)

**DB layer:** `app/database.py` (uses `AsyncSession`, `create_async_engine`)

**Storage:** `app/storage/` (MinIO client, upload helpers)

**Background jobs:** `app/workers/` (Celery tasks)

Conclusion: the codebase follows a Repository + Service layer pattern (routers delegate to services; services use repositories).

## Key conventions / Style Guide
- Naming:
  - variables and functions: `snake_case`
  - classes and Pydantic models: `CamelCase`
  - constants: `UPPER_SNAKE_CASE` (see `app/core/constants.py`)
  - router paths: RESTful resources defined in `app/routers.py` (prefixes like `/auth`, `/messages`, `/appointments`)
- Types and annotations:
  - Function arguments and return types are annotated (including `AsyncSession`, `UUID`, etc.)
  - Pydantic v2 usage via `Model.model_validate(...)` and `model_dump()` is present
  - No explicit use of `Strict` types was found
- Docstrings / comments:
  - Minimal package/function docstrings are present for utilities (e.g. `app/storage`, `app/workers`)
  - Most endpoint functions do not include docstrings; they rely on type annotations and response models
- Idioms:
  - Asynchronous DB access throughout (async/await)
  - Service objects are instantiated with `db` and `redis` when needed (e.g. `AuthService(db, redis)`)
  - JWT auth via `python-jose` (`app/core/security.py`)

## Check commands
- Ensure your virtualenv is activated (example for PowerShell):
```powershell
& ".venv\Scripts\Activate.ps1"
```
- Run tests locally:
```bash
pytest -q
# or with filters
pytest -q -k "not slow"
```
- Run async tests / alternative flags:
```bash
pytest -q --maxfail=1 --disable-warnings
```
- Linters / formatting (recommendations):
  - ruff (fast):
```bash
pip install ruff
ruff check .
```
  - flake8 (optional):
```bash
pip install flake8
flake8 app tests
```
  - black (formatting):
```bash
pip install black
black .
```
- Alembic migrations (run from repository root):
```bash
alembic upgrade head
# To rollback one revision:
alembic downgrade -1
```
If `settings.database_url` is populated from env vars, export or set `DATABASE_URL` / `settings` before running Alembic.

## 🔗 API Response Format

All endpoints return wrapped responses (from `app/core/response.py`):

### Success Response Envelope
```📋 Module Implementation Template

When adding a new feature, follow this pattern:

### 1. Create `models.py` (SQLAlchemy ORM)
```python
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid

class Feature(Base):
    __tablename__ = "features"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 2. Create `schemas.py` (Pydantic v2)
```python
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class FeatureCreate(BaseModel):
    title: str

class FeatureResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

### 3. Create `repository.py` (Database Layer)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class FeatureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, feature_id: UUID) -> Feature | None:
        result = await self.db.execute(
            select(Feature).where(Feature.id == feature_id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, data: dict) -> Feature:
        feature = Feature(**data)
        self.db.add(feature)
        await self.db.commit()
        return feature
```

### 4. Create `service.py` (Business Logic)
```python
class FeatureService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = FeatureRepository(db)
    
    async def create(self, payload: FeatureCreate) -> FeatureResponse:
        feature = await self.repository.create(payload.model_dump())
        return FeatureResponse.model_validate(feature)
```

### 5. Create `router.py` (Endpoints)
```python
from fastapi import APIRouter, Depends
from app.database import get_db

router = APIRouter(prefix="/features", tags=["Features"])

@router.post("/", response_model=SuccessResponse)
async def create_feature(
    payload: FeatureCreate,
    db: AsyncSession = Depends(get_db)
):
    service = FeatureService(db)
    data = await service.create(payload)
    return SuccessResponse(data=data)
```

### 6. Register in `app/routers.py`
```python
from app.modules.features.router import router as features_router

api_router.include_router(features_router, prefix="/features", tags=["Features"])
```

### 7. Create migration
```bash
alembic revision --autogenerate -m "add features table"
alembic upgrade head
```

---

## python
class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    message: str | None = None
```

### Example: Authentication Response
```
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response 200:
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "message": null
}
```

### Pagination (List Endpoints)
```python
class PaginatedResponse(BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool
```

Example:
```
GET /api/v1/appointments?page=1&limit=20

Response 200:
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "Appointment 1",
        "scheduled_at": "2024-05-20T10:00:00Z",
        ...
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "has_more": true
  }
}
```

## 🔐 Auth Conventions
- API prefix: `/api/v1` (mounted in `app/main.py`)
- Auth: JWT Bearer (tokens in `app/core/security.py`)
- All authenticated endpoints require: `Authorization: Bearer <access_token>`
- Token refresh: `POST /api/v1/auth/refresh` returns new `access_token`
- Token stored in frontend localStorage (next session)

## 🔄 Migration & Deployment

**Latest migration:** `0009_mobile_gap_fix.py` 

**To apply:**
```bash
cd Backend
alembic upgrade head
```

**What this migration does:**
- Adds new columns to `tasks` table: `task_type`, `time_from`, `time_to`, `location`, `reminder_minutes`
- Adds new column to `appointments` table: `consultation_type`
- Adds new columns to `documents` table: `category`, `status`, `expires_at`
- Creates new `enrollments` table (student ↔ university many-to-many with progress)

**To rollback (if needed):**
```bash
alembic downgrade -1
```

## Current Tasks
1) ✅ **COMPLETED** — Mobile gap analysis (migration `0009_mobile_gap_fix.py`)
   - Tasks: added `task_type`, `time_from`, `time_to`, `location`, `reminder_minutes` + stats endpoint
   - Appointments: added `consultation_type` (video/audio/chat)
   - Documents: added `category`, `status`, `expires_at`
   - Notifications: added filtering by `type` query parameter
   - **NEW MODULE Enrollments:** student university enrollment management
   
2) Frontend implementation — build UI for new endpoints
   - Dashboard with Tasks stats
   - Appointments booking form with `consultation_type`
   - Enrollments flow (select university, track progress)
   - Documents upload with category/expiration

3) Missing endpoints (future priority)
   - `/courses/{id}/reviews` — course reviews module
   - `/users/{id}/stats` — overall user analytics

---

## 📊 All Modules & Key Endpoints

| Module | Endpoints | New/Updated |
|--------|-----------|-----------|
| `auth` | `/login`, `/register`, `/refresh`, `/logout` | — |
| `users` | `/me`, `/profile`, `/avatar` | — |
| `profile` | User profile management | — |
| `documents` | `/upload`, `/list`, `/delete` | ✅ `category`, `status`, `expires_at` |
| `tasks` | `/list`, `/create`, **/stats** | ✅ `task_type`, times, location, **stats endpoint** |
| `notifications` | `/list?type=<admission\|task\|system>` | ✅ filter by type |
| `messages` | `/chats`, `/send`, `/list` | — |
| `appointments` | `/list`, `/create`, `/update` | ✅ `consultation_type` |
| `universities` | `/list`, `/get/{id}` | — |
| **enrollments** | **/list**, **/enroll**, **/unenroll** | 🆕 **NEW MODULE** |
| `news` | `/list`, `/get/{id}` | — |
| `calendar` | `/events`, `/create`, `/delete` | — |
| `roadmaps` | `/list`, `/get/{id}` | — |
| `faq` | `/list` | — |
| `alumni` | `/stories`, `/get/{id}` | — |
| `reports` | `/stats` | — |

---

## 🆕 Enrollments Module — Example Usage

**New module structure:**
```
app/modules/enrollments/
├── models.py          # Enrollment ORM model
├── schemas.py         # EnrollmentCreate, EnrollmentResponse, etc.
├── repository.py      # get_by_student, get_by_student_and_university, create, update, delete
├── service.py         # enroll, unenroll, get_student_enrollments, update_progress
└── router.py          # POST/PATCH/DELETE /students/{id}/universities/{uni_id}/enroll
```

**Enrollment Object:**
```python
class Enrollment(Base):
    __tablename__ = "enrollments"
    
    id = Column(UUID, primary_key=True)
    student_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    university_id = Column(UUID, ForeignKey("universities.id"), nullable=False)
    status = Column(String)  # enrolled, completed, suspended
    progress = Column(Float)  # 0.0 - 1.0 (0-100%)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

**Endpoints:**
```
GET    /api/v1/students/{student_id}/enrollments
       → List all universities student is enrolled in with progress

POST   /api/v1/students/{student_id}/universities/{university_id}/enroll
       → Enroll student in university
       
PATCH  /api/v1/students/{student_id}/universities/{university_id}/enroll
       → Update enrollment status or progress (admin only)
       
DELETE /api/v1/students/{student_id}/universities/{university_id}/enroll
       → Unenroll student from university
```

**Example Request:**
```bash
# Enroll in a university
POST /api/v1/students/{student_id}/universities/{university_id}/enroll
{
  "status": "enrolled"
}

Response 201:
{
  "success": true,
  "data": {
    "id": "uuid",
    "student_id": "uuid",
    "university_id": "uuid",
    "status": "enrolled",
    "progress": 0.0,
    "enrolled_at": "2024-05-20T10:00:00Z"
  }
}

# Get all enrollments
GET /api/v1/students/{student_id}/enrollments

Response 200:
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "student_id": "uuid",
      "university_id": "uuid",
      "university": {
        "id": "uuid",
        "name": "MIT",
        "country": "USA"
      },
      "status": "enrolled",
      "progress": 0.35,
      "enrolled_at": "2024-05-20T10:00:00Z"
    }
  ]
}
```

---

## 🔄 Migration & Deployment

Current location: [CLAUDE.md](CLAUDE.md)
