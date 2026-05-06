# Nobal Education Backend — Development Plan

## Architecture Override: Modular Structure

TZ proposes a layered structure (`models/`, `schemas/`, `routers/`, `services/`). **Replaced** with a module-per-feature structure.

---

## Project Structure

```
nobal-backend/
├── app/
│   ├── main.py                   # FastAPI app factory, middleware, lifespan
│   ├── routers.py                # Aggregates all module routers
│   ├── config.py                 # pydantic-settings
│   ├── database.py               # Async SQLAlchemy engine + session factory
│   ├── dependencies.py           # Shared deps: get_db, get_current_user, require_role
│   │
│   ├── core/
│   │   ├── security.py           # JWT create/verify, bcrypt hash/verify
│   │   ├── exceptions.py         # AppException + ErrorCode enum
│   │   ├── permissions.py        # RBAC: require_student(), require_conductor_or_admin()
│   │   └── constants.py          # ALMATY_TZ, pagination defaults, etc.
│   │
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # RefreshToken ORM
│   │   │   ├── schemas.py        # LoginRequest, RegisterRequest, TokenResponse
│   │   │   ├── repository.py     # save/get/delete refresh_tokens
│   │   │   ├── service.py        # register, login, refresh, logout, OTP flow
│   │   │   └── router.py         # POST /auth/*
│   │   │
│   │   ├── users/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # User ORM
│   │   │   ├── schemas.py        # UserOut, UserUpdate, StudentListItem
│   │   │   ├── repository.py     # get_by_id, get_by_email, list_students
│   │   │   ├── service.py        # get_me, update_me, list/get/delete students
│   │   │   └── router.py         # GET/PUT /users/me, GET/PUT/DELETE /students/*
│   │   │
│   │   ├── profile/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # StudentProfile ORM
│   │   │   ├── schemas.py        # ProfileOut, ProfileUpdate
│   │   │   ├── repository.py     # get_by_user_id, upsert
│   │   │   ├── service.py        # get_profile, update_profile
│   │   │   └── router.py         # GET/PUT /students/{id}/profile
│   │   │
│   │   ├── documents/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # StudentDocument ORM
│   │   │   ├── schemas.py        # DocumentOut, DocumentUploadResponse
│   │   │   ├── repository.py     # list, get, upsert, delete
│   │   │   ├── service.py        # upload (MinIO), download signed URL, delete
│   │   │   └── router.py         # GET/POST/DELETE /students/{id}/documents/*
│   │   │
│   │   ├── universities/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # University + UniversityProgram ORM
│   │   │   ├── schemas.py        # UniversityOut, ProgramOut, create/update schemas
│   │   │   ├── repository.py     # list (filtered), get_with_programs, CRUD
│   │   │   ├── service.py        # CRUD + soft delete + staleness check trigger
│   │   │   └── router.py         # GET/POST/PUT/DELETE /universities/*
│   │   │
│   │   ├── news/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # News ORM
│   │   │   ├── schemas.py        # NewsOut, NewsCreate, NewsUpdate
│   │   │   ├── repository.py     # list (filtered), get, CRUD, increment_views
│   │   │   ├── service.py        # CRUD + add_to_calendar integration
│   │   │   └── router.py         # GET/POST/PUT/DELETE /news/* + /news/{id}/add-to-calendar
│   │   │
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # Task ORM
│   │   │   ├── schemas.py        # TaskOut, TaskCreate, TaskStatusUpdate
│   │   │   ├── repository.py     # list (filtered), get, CRUD, mark_overdue_bulk
│   │   │   ├── service.py        # create (conductor/personal), update, patch_status
│   │   │   └── router.py         # GET/POST/PUT/PATCH/DELETE /tasks/* + /students/{id}/tasks
│   │   │
│   │   ├── roadmaps/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # Roadmap + RoadmapTemplateTask + StudentRoadmap ORM
│   │   │   ├── schemas.py        # RoadmapOut, AssignRequest, StudentRoadmapOut
│   │   │   ├── repository.py     # list public, get_with_tasks, assign, get_student_roadmaps
│   │   │   ├── service.py        # CRUD + assign (creates tasks + calendar events + notification)
│   │   │   └── router.py         # GET/POST/PUT/DELETE /roadmaps/* + /roadmaps/{id}/assign
│   │   │
│   │   ├── appointments/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # AvailabilitySlot + Appointment ORM
│   │   │   ├── schemas.py        # SlotOut, AppointmentOut, BookRequest, CancelRequest
│   │   │   ├── repository.py     # slots CRUD, appointment CRUD, list
│   │   │   ├── service.py        # create_slots, book, cancel, complete (side effects)
│   │   │   └── router.py         # GET/POST/DELETE /appointments/slots + /appointments/*
│   │   │
│   │   ├── messages/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # Conversation + Message ORM
│   │   │   ├── schemas.py        # MessageOut, ConversationOut, SendMessageRequest
│   │   │   ├── repository.py     # get_or_create_conversation, list_messages, mark_read
│   │   │   ├── service.py        # send, broadcast, mark_read, list
│   │   │   └── router.py         # GET/POST /conversations/* + /messages/broadcast
│   │   │
│   │   ├── calendar/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # CalendarEvent ORM
│   │   │   ├── schemas.py        # CalendarEventOut, CalendarEventCreate
│   │   │   ├── repository.py     # list (date range), get, CRUD
│   │   │   ├── service.py        # get/create/update/delete, create_from_source
│   │   │   └── router.py         # GET/POST/PUT/DELETE /calendar/*
│   │   │
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # Notification ORM
│   │   │   ├── schemas.py        # NotificationOut
│   │   │   ├── repository.py     # list, mark_read, unread_count, create
│   │   │   ├── service.py        # create_notification (central), mark_read, get_count
│   │   │   └── router.py         # GET/PATCH /notifications/*
│   │   │
│   │   ├── faq/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # FAQ ORM
│   │   │   ├── schemas.py        # FAQOut, FAQCreate, ReorderRequest
│   │   │   ├── repository.py     # list_active, CRUD, reorder
│   │   │   ├── service.py        # CRUD + reorder logic
│   │   │   └── router.py         # GET/POST/PUT/DELETE/PATCH /faqs/*
│   │   │
│   │   ├── alumni/
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # AlumniStory ORM
│   │   │   ├── schemas.py        # AlumniOut, AlumniCreate
│   │   │   ├── repository.py     # list_published, get, CRUD
│   │   │   ├── service.py        # CRUD
│   │   │   └── router.py         # GET/POST/PUT/DELETE /alumni/*
│   │   │
│   │   └── reports/
│   │       ├── __init__.py
│   │       ├── models.py         # (no dedicated table — queries across modules)
│   │       ├── schemas.py        # OverviewReport, StudentReport, UniversityReport
│   │       ├── repository.py     # aggregate queries
│   │       ├── service.py        # compute stats
│   │       └── router.py         # GET /reports/*
│   │
│   ├── workers/
│   │   ├── celery_app.py         # Celery factory + Beat schedule
│   │   ├── email_tasks.py        # send_email_task
│   │   ├── reminder_tasks.py     # check_task_deadlines, send_appointment_reminders
│   │   └── maintenance_tasks.py  # mark_overdue_tasks, cleanup_tokens, staleness_check
│   │
│   ├── storage/
│   │   ├── minio_client.py       # MinIO wrapper (upload, signed URL, delete)
│   │   └── file_validator.py     # magic-byte MIME validation
│   │
│   └── email/
│       ├── sender.py             # aiosmtplib async send
│       └── templates/            # Jinja2 HTML (8 templates per TZ)
│
├── migrations/
│   ├── env.py
│   └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_students.py
│   ├── test_tasks.py
│   ├── test_appointments.py
│   └── test_messages.py
│
├── scripts/
│   ├── seed_data.py
│   └── create_admin.py
│
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.celery
│   └── nginx.conf
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── requirements.txt
├── .env.example
├── alembic.ini
└── README.md
```

---

## Layer Isolation Rules

| File | Allowed imports |
|------|----------------|
| `router.py` | `schemas.py`, `service.py`, `dependencies.py`, `core/permissions.py` |
| `service.py` | `repository.py`, `schemas.py`, `models.py`, `core/*`, `storage/*`, `workers/*` |
| `repository.py` | `models.py`, `database.py` |
| `models.py` | `database.py` (Base) only |
| `schemas.py` | Pydantic only, no ORM imports |

> `router.py` **never** imports `repository.py` directly. It only calls `service.py` methods.

---

## Delivery Chunks (Based on TZ §16 MVP Plan)

### Chunk 0 — Infrastructure (Day 1, ~3h)
- `docker-compose.yml` (postgres, redis, minio, api, celery, nginx)
- `app/config.py` + `app/database.py`
- `app/core/exceptions.py` + `app/core/constants.py`
- `app/core/security.py` (JWT + bcrypt)
- `migrations/` — Alembic init + **all tables in one initial migration**
- `app/main.py` — app factory + middleware (CORS, rate limiter, exception handler)

### Chunk 1 — Auth Module (Day 1, ~3h)
**Tables:** `users`, `refresh_tokens`
- `modules/auth/` — all 6 files
- `modules/users/models.py` (User ORM needed by auth)
- Endpoints: `POST /auth/register|login|refresh|logout|forgot-password|reset-password|change-password`
- Redis OTP storage for password reset

### Chunk 2 — Users & Profile (Day 2, ~3h)
**Tables:** `student_profiles`
- `modules/users/` — all 6 files
- `modules/profile/` — all 6 files
- `app/dependencies.py` — `get_current_user`, `require_role`
- `app/core/permissions.py`
- Endpoints: `GET/PUT /users/me`, `GET/PUT/DELETE /students/*`, `GET/PUT /students/{id}/profile`

### Chunk 3 — Tasks (Day 2, ~3h)
**Tables:** `tasks`
- `modules/tasks/` — all 6 files
- Endpoints: `GET/POST /students/{id}/tasks`, `POST /tasks/personal`, `PUT/PATCH/DELETE /tasks/*`
- `PATCH /tasks/{id}/status` → triggers notification to conductor

### Chunk 4 — Documents (Day 3, ~3h)
**Tables:** `student_documents`
- `modules/documents/` — all 6 files
- `app/storage/minio_client.py` + `file_validator.py`
- Endpoints: `GET/POST/DELETE /students/{id}/documents/*`
- MinIO bucket creation on startup (lifespan)

### Chunk 5 — Messages / Chat (Day 3, ~3h)
**Tables:** `conversations`, `messages`
- `modules/messages/` — all 6 files
- Endpoints: `GET/POST /conversations/*`, `POST /messages/broadcast`
- Broadcast creates individual messages per matching student

### Chunk 6 — Appointments (Day 4, ~4h)
**Tables:** `availability_slots`, `appointments`
- `modules/appointments/` — all 6 files
- Endpoints: `GET/POST/DELETE /appointments/slots`, `POST/GET/PATCH /appointments/*`
- Booking side effects: mark slot unavailable, create calendar events for both parties, send notifications + email

### Chunk 7 — Universities (Day 4, ~3h)
**Tables:** `universities`, `university_programs`
- `modules/universities/` — all 6 files
- Endpoints: `GET/POST/PUT/DELETE /universities/*` + programs sub-resource
- Filtered list: country, field, gpa, tuition, degree_level, scholarship, search

### Chunk 8 — News & Calendar (Day 5, ~4h)
**Tables:** `news`, `calendar_events`
- `modules/news/` + `modules/calendar/` — all 6 files each
- News endpoints: `GET/POST/PUT/DELETE /news/*` + `POST /news/{id}/add-to-calendar`
- Calendar endpoints: `GET/POST/PUT/DELETE /calendar/*`
- `add-to-calendar` creates `calendar_event` with `source_type="news"`

### Chunk 9 — Notifications (Day 6, ~3h)
**Tables:** `notifications`
- `modules/notifications/` — all 6 files
- `service.create_notification()` is the **central internal function** called by all other services
- Endpoints: `GET /notifications`, `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`, `GET /notifications/unread-count`
- Redis cache for unread count (TTL 1 min)

### Chunk 10 — Roadmaps (Day 6, ~3h)
**Tables:** `roadmaps`, `roadmap_template_tasks`, `student_roadmaps`
- `modules/roadmaps/` — all 6 files
- Assign endpoint side effects: create `student_roadmap` → create tasks from template → add to calendar → send notification
- Endpoints: `GET/POST/PUT/DELETE /roadmaps/*` + `POST /roadmaps/{id}/assign` + `GET /students/{id}/roadmaps`

### Chunk 11 — Email + Celery Jobs (Day 7, ~4h)
- `app/email/sender.py` (aiosmtplib)
- `app/email/templates/` (8 Jinja2 HTML templates)
- `app/workers/celery_app.py` (Beat schedule)
- `app/workers/email_tasks.py` — `send_email_task` with retry
- `app/workers/reminder_tasks.py` — `check_task_deadlines`, `send_appointment_reminders`
- `app/workers/maintenance_tasks.py` — `mark_overdue_tasks`, `cleanup_expired_tokens`, `check_university_staleness`

### Chunk 12 — FAQ, Alumni, Reports (Day 7, ~3h)
- `modules/faq/` + `modules/alumni/` + `modules/reports/` — all 6 files each
- Reports: aggregate queries across modules (no dedicated table)
- Caching: FAQ and public roadmaps cached in Redis

### Chunk 13 — Root Router + Final Wiring
- `app/routers.py` — imports all `module.router.router` and registers with prefix `/api/v1`
- `scripts/seed_data.py` + `scripts/create_admin.py`
- `tests/` — conftest + 5 test files

---

## Cross-Module Dependencies

```
notifications.service  ← called by: tasks, appointments, roadmaps, messages, news
calendar.service       ← called by: appointments, roadmaps, news
workers/*              ← called by: appointments.service, auth.service, tasks.service
storage/*              ← called by: documents.service, universities.service, news.service
```

> These cross-module calls go **service → service only**. Never router → foreign service.

---

## Key Technical Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Auth tokens | JWT access (60min) + hashed refresh (30d, DB) | Per TZ |
| Password reset | 6-digit OTP in Redis (15min TTL) | Per TZ |
| Notification delivery | Polling (`/notifications/unread-count` every 30s) | MVP simplicity |
| File storage | MinIO (self-hosted S3) | No per-request cost |
| File MIME validation | `python-magic` (reads magic bytes) | Security: no extension spoofing |
| Soft delete | `is_published=False` for universities/news | Per TZ |
| Timezone | Store UTC in DB, display UTC+6 on frontend | Per TZ |
| Rate limiting | `slowapi`: login 5/min, OTP 3/min | Per TZ §14.5 |
| Caching | Redis: university list (5min), FAQ (10min), unread count (1min) | Per TZ §15.3 |
