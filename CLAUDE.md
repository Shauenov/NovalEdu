# Nobal Education Backend — CLAUDE Guide

## What this file is for
Use this as the fast reference for backend architecture, recent changes, and migration workflow.
This file reflects the current `Backend` repository state.

## Stack
- FastAPI 0.111.0
- SQLAlchemy 2.x (async) + asyncpg
- Pydantic v2
- Alembic migrations
- PostgreSQL
- Celery + Redis
- MinIO

## Project layout
```
Backend/
├── app/
│   ├── main.py                # FastAPI app
│   ├── routers.py             # API router aggregation (/api/v1)
│   ├── database.py            # Async engine/session
│   ├── core/                  # constants, exceptions, permissions, response
│   └── modules/
│       └── <module>/
│           ├── models.py
│           ├── schemas.py
│           ├── repository.py
│           ├── service.py
│           └── router.py
├── migrations/
│   ├── env.py
│   └── versions/
└── docker-compose.yml
```

## Core conventions
- Architecture: Router -> Service -> Repository.
- API prefix: `/api/v1`.
- Response envelope: `success`, `data`, optional `message`.
- Auth and roles are enforced via dependencies in `app/core/permissions.py`.
- Pagination convention: `page`, `page_size`, `total` in `meta`.

## Recent backend changes (current working tree)

### 1) Tasks module: audit history
Updated files:
- `app/modules/tasks/models.py`
- `app/modules/tasks/repository.py`
- `app/modules/tasks/service.py`
- `app/modules/tasks/schemas.py`
- `app/modules/tasks/router.py`

What changed:
- Added `TaskHistory` model (`task_history` table) to store task audit events.
- Added history writes on:
  - task creation (`created`)
  - task update (`updated`)
  - status change (`status_changed`)
- Added API endpoint:
  - `GET /api/v1/tasks/{task_id}/history`
- Added response schemas:
  - `TaskHistoryOut`
  - `TaskHistoryResponse`

New migration file in working tree:
- `migrations/versions/0011_task_history.py`

### 2) Enrollments module: university-centric list endpoint
Updated files:
- `app/modules/enrollments/repository.py`
- `app/modules/enrollments/service.py`
- `app/modules/enrollments/schemas.py`
- `app/modules/enrollments/router.py`

What changed:
- Added paginated listing of enrollments by university with joined student info.
- Added status filter support.
- Added API endpoint:
  - `GET /api/v1/universities/{university_id}/enrollments`
- Added schemas:
  - `StudentBriefForEnrollment`
  - `EnrollmentWithStudentOut`
  - `PaginatedMeta`
  - `PaginatedUniversityEnrollments`

Accepted status filter values:
- `selected`
- `applying`
- `submitted`
- `accepted`
- `rejected`

### 3) Reports module: overview budget metric
Updated files:
- `app/modules/reports/repository.py`
- `app/modules/reports/schemas.py`

What changed:
- Added `total_budget_usd` to overview report.
- Value is computed as sum of active students' `student_profiles.budget_max`.
- Returned via existing endpoint:
  - `GET /api/v1/reports/overview`

## Migration status notes
Existing migration chain in repository includes:
- `0009_mobile_gap_fix.py`
- `0010_profile_settings_sessions.py`
- `2dad676f4020_autogen_detect_changes.py`

Current new migration file (not yet committed):
- `0011_task_history.py`

## Migration workflow
Run from `Backend`:
```bash
alembic upgrade head
```

Create migration:
```bash
alembic revision --autogenerate -m "your message"
```

Rollback one step:
```bash
alembic downgrade -1
```

Docker-based migration (when local DB host is Docker-only):
```bash
docker run --rm --network nobal_ec_network --env-file "Backend/.env" -e DATABASE_URL=postgresql+asyncpg://<user>:<pass>@postgres:5432/<db> -v "<ABS_PATH_TO_BACKEND>:/app" -w /app backend-api:latest alembic upgrade head
```

## Quick verification commands
```bash
pytest -q
```

```bash
docker exec ec_postgres psql -U nobal -d nobal -c "select version_num from alembic_version;"
```

## Admin module (new)
- `GET /api/v1/admin/stats` — user counts, by-role breakdown, growth chart (admin only)
- `GET /api/v1/admin/users` — list all users with search/role/status filters + pagination (admin only)
- `POST /api/v1/admin/users` — create any-role user (admin only)
- `GET /api/v1/admin/users/{id}` — get single user (admin only)
- `PATCH /api/v1/admin/users/{id}` — update user fields: full_name, email, role, is_active (admin only)
- `POST /api/v1/admin/users/{id}/reset-password` — set new password (admin only)
- `DELETE /api/v1/admin/users/{id}` — hard-delete user, cannot self-delete (admin only)
- `GET /api/v1/admin/advisers` — list advisers with profile + review aggregates (admin only)

Files: `app/modules/admin/{__init__,schemas,repository,service,router}.py`
Registered in: `app/routers.py` → `api_router.include_router(admin_router, tags=["Admin"])`

## API highlights to keep in sync with frontend/mobile
- Tasks:
  - `GET /students/{student_id}/tasks`
  - `GET /students/{student_id}/tasks/stats?month=YYYY-MM`
  - `GET /tasks/{task_id}/history`
- Enrollments:
  - `GET /students/{student_id}/enrollments`
  - `GET /universities/{university_id}/enrollments`
  - `POST/PATCH/DELETE /students/{student_id}/universities/{university_id}/enroll`
- Reports:
  - `GET /reports/overview` (includes `total_budget_usd`)

## Implementation rule for new modules
For any new backend feature, keep this file synchronized with:
- new/changed endpoints
- added migration files
- schema field additions
- role/permission changes
