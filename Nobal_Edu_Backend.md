# Technical Specification: Backend System
## Nobal Education — Student Admission Management Platform

**Version:** 1.0  
**Date:** April 30, 2026  
**Stack:** Python · FastAPI · PostgreSQL · Docker  
**Language:** English  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Database Schema](#3-database-schema)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [API Endpoints](#5-api-endpoints)
   - 5.1 [Auth](#51-auth)
   - 5.2 [Users / Students](#52-users--students)
   - 5.3 [Documents](#53-documents)
   - 5.4 [Universities](#54-universities)
   - 5.5 [News & Events](#55-news--events)
   - 5.6 [Tasks](#56-tasks)
   - 5.7 [Roadmaps](#57-roadmaps)
   - 5.8 [Appointments](#58-appointments)
   - 5.9 [Messages (Chat)](#59-messages-chat)
   - 5.10 [Calendar](#510-calendar)
   - 5.11 [Notifications](#511-notifications)
   - 5.12 [FAQ](#512-faq)
   - 5.13 [Alumni Stories](#513-alumni-stories)
   - 5.14 [Reports (ADVISER/Admin)](#514-reports-ADVISERadmin)
6. [Notification System](#6-notification-system)
7. [File Storage Strategy](#7-file-storage-strategy)
8. [Email Integration](#8-email-integration)
9. [Background Jobs (Celery)](#9-background-jobs-celery)
10. [Error Handling & Validation](#10-error-handling--validation)
11. [Project Structure](#11-project-structure)
12. [Docker Compose Configuration](#12-docker-compose-configuration)
13. [Environment Variables](#13-environment-variables)
14. [Security Requirements](#14-security-requirements)
15. [Performance & Scalability](#15-performance--scalability)
16. [Development Roadmap / MVP Plan](#16-development-roadmap--mvp-plan)

---

## 1. Project Overview

### 1.1 Purpose

Nobal Education is a platform designed for a college-level admission advisor ("ADVISER") and their students. The ADVISER works 1-on-1 with approximately 100 students per year (2nd and 3rd year), guiding them through:

- University application process (Kazakhstan + abroad)
- Standardized test preparation (IELTS, SAT, ENT/KTA)
- Participation in olympiads, hackathons, incubators, summer camps
- Personal document management (CV, Motivation Letter, Recommendation Letter)
- Personalized task management and roadmap execution

### 1.2 Actors

| Role | Description |
|------|-------------|
| `student` | College student, uses mobile app (Flutter) |
| `ADVISER` | Admission advisor, uses web dashboard |
| `admin` | System administrator, full control (can be same person as ADVISER) |

### 1.3 Key Constraints

- Single ADVISER per deployment
- ~100 active students per academic year
- Groups: D-group and F-group
- Budget-conscious: minimize paid external services
- Languages: Russian and Kazakh (UI), English API responses
- Timezone: Asia/Almaty (UTC+6)
- Deployment: Docker on college-owned server

---

## 2. System Architecture

### 2.1 High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                        Clients                           │
│   Flutter App (Student)   │   Web Dashboard (ADVISER)  │
└──────────────┬────────────┴──────────────┬──────────────┘
               │                           │
               ▼                           ▼
       ┌───────────────────────────────────────┐
       │           Nginx (Reverse Proxy)        │
       │         SSL Termination + Static       │
       └────────────────────┬──────────────────┘
                            │
                            ▼
       ┌───────────────────────────────────────┐
       │         FastAPI Application            │
       │   (Uvicorn + Gunicorn workers)         │
       └───┬────────────────┬──────────────────┘
           │                │
     ┌─────▼──────┐  ┌──────▼──────┐
     │ PostgreSQL │  │    Redis     │
     │  (main DB) │  │ (cache +     │
     └────────────┘  │  task queue) │
                     └──────┬──────┘
                            │
                     ┌──────▼──────┐
                     │   Celery     │
                     │  (workers)   │
                     └─────────────┘
                            │
                     ┌──────▼──────┐
                     │  MinIO /     │
                     │  Local FS    │
                     │ (file store) │
                     └─────────────┘
```

### 2.2 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.12+ |
| Framework | FastAPI | 0.111+ |
| ORM | SQLAlchemy | 2.0 (async) |
| Migrations | Alembic | 1.13+ |
| Database | PostgreSQL | 16 |
| Cache / Queue Broker | Redis | 7 |
| Background Jobs | Celery | 5.3+ |
| File Storage | MinIO (self-hosted S3-compatible) | latest |
| Email | SMTP (college SMTP or Brevo free tier) | — |
| Auth | JWT (access + refresh tokens) | — |
| Password Hashing | bcrypt | — |
| Validation | Pydantic v2 | 2.7+ |
| HTTP Server | Uvicorn + Gunicorn | — |
| Reverse Proxy | Nginx | latest |
| Containerization | Docker + Docker Compose | — |
| Testing | Pytest + httpx | — |

### 2.3 Request / Response Contract

- All requests: `Content-Type: application/json`
- File uploads: `multipart/form-data`
- All responses: JSON
- Timestamps: ISO 8601 format, UTC stored, UTC+6 displayed on frontend
- Pagination: `?page=1&page_size=20` (default page_size=20, max=100)
- Standard success response envelope:

```json
{
  "success": true,
  "data": { ... },
  "meta": { "page": 1, "page_size": 20, "total": 150 }
}
```

- Standard error response envelope:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "GPA must be between 0 and 4.0",
    "details": { "field": "gpa", "value": 5.1 }
  }
}
```

---

## 3. Database Schema

### 3.1 Entity Relationship Diagram (Text)

```
users (1) ──────────────────── (1) student_profiles
users (1) ──────────────────── (*) tasks
users (1) ──────────────────── (*) appointments (as student)
users (1) ──────────────────── (*) messages (as sender)
users (1) ──────────────────── (*) calendar_events
users (1) ──────────────────── (*) notifications
users (1) ──────────────────── (*) student_documents
users (1) ──────────────────── (*) roadmap_assignments (student_roadmaps)
roadmaps (1) ─────────────────(*) roadmap_assignments
roadmaps (1) ─────────────────(*) roadmap_tasks (template tasks)
universities (1) ─────────────(*) university_programs
news (*) ──────────────────── (*) calendar_events (via FK event_id)
appointments (*) ─────────────(*) calendar_events
tasks (*) ────────────────────(*) calendar_events (deadline)
```

### 3.2 Table Definitions

#### `users`
```sql
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    full_name     VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('student','ADVISER','admin')),
    is_active     BOOLEAN DEFAULT TRUE,
    avatar_url    VARCHAR(500),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);
```

#### `student_profiles`
```sql
CREATE TABLE student_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_type      VARCHAR(1) NOT NULL CHECK (group_type IN ('D','F')),
    course_year     SMALLINT NOT NULL CHECK (course_year IN (2,3)),
    gpa             NUMERIC(3,2) CHECK (gpa >= 0 AND gpa <= 4.0),
    ielts_passed    BOOLEAN DEFAULT FALSE,
    ielts_score     NUMERIC(3,1) CHECK (ielts_score >= 0 AND ielts_score <= 9.0),
    ielts_date      DATE,
    sat_passed      BOOLEAN DEFAULT FALSE,
    sat_score       SMALLINT CHECK (sat_score >= 400 AND sat_score <= 1600),
    sat_date        DATE,
    ent_score       SMALLINT CHECK (ent_score >= 0 AND ent_score <= 140),
    kta_score       SMALLINT,
    target_country  VARCHAR(100),
    target_major    VARCHAR(200),
    notes           TEXT,                          -- ADVISER private notes
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### `student_documents`
```sql
CREATE TABLE student_documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    doc_type     VARCHAR(50) NOT NULL CHECK (doc_type IN (
                   'cv','motivation_letter','recommendation_letter',
                   'personal_statement','other'
                 )),
    file_name    VARCHAR(255) NOT NULL,
    file_url     VARCHAR(500) NOT NULL,
    file_size    INT NOT NULL,              -- bytes
    mime_type    VARCHAR(100) NOT NULL,
    uploaded_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Only one active document per type per student
CREATE UNIQUE INDEX idx_student_docs_type ON student_documents(student_id, doc_type);
```

#### `universities`
```sql
CREATE TABLE universities (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  VARCHAR(300) NOT NULL,
    country               VARCHAR(100) NOT NULL,
    city                  VARCHAR(100),
    logo_url              VARCHAR(500),
    cover_image_url       VARCHAR(500),
    website_url           VARCHAR(500),
    description           TEXT,
    acceptance_rate       NUMERIC(5,2),
    total_students        INT,
    international_pct     NUMERIC(5,2),
    qs_ranking            SMALLINT,
    the_ranking           SMALLINT,
    language_of_instr     VARCHAR(100),
    is_published          BOOLEAN DEFAULT TRUE,
    last_verified_at      TIMESTAMPTZ,              -- for staleness tracking
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_universities_country ON universities(country);
CREATE INDEX idx_universities_published ON universities(is_published);
```

#### `university_programs`
```sql
CREATE TABLE university_programs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id     UUID NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
    name              VARCHAR(300) NOT NULL,
    degree_level      VARCHAR(50) CHECK (degree_level IN ('bachelor','master','phd','foundation')),
    field             VARCHAR(100),                -- e.g. "Computer Science", "Business"
    min_gpa           NUMERIC(3,2),
    min_ielts         NUMERIC(3,1),
    min_sat           SMALLINT,
    tuition_usd       INT,                        -- annual tuition in USD
    scholarship_info  TEXT,
    application_fee   INT,
    intake_seasons    VARCHAR(100),               -- e.g. "Fall, Spring"
    deadline          DATE,
    campus_life       TEXT,
    requirements_text TEXT,                       -- free text for additional requirements
    apply_url         VARCHAR(500),
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_programs_university ON university_programs(university_id);
CREATE INDEX idx_programs_field ON university_programs(field);
```

#### `news`
```sql
CREATE TABLE news (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id     UUID NOT NULL REFERENCES users(id),
    title         VARCHAR(500) NOT NULL,
    body          TEXT NOT NULL,
    cover_url     VARCHAR(500),
    category      VARCHAR(50) NOT NULL CHECK (category IN (
                    'olympiad','hackathon','deadline','summer_camp',
                    'webinar','internship','university_news','general'
                  )),
    event_date    DATE,                    -- date of the event/deadline
    external_url  VARCHAR(500),
    is_published  BOOLEAN DEFAULT TRUE,
    views_count   INT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_news_category ON news(category);
CREATE INDEX idx_news_published ON news(is_published, created_at DESC);
```

#### `roadmaps`
```sql
CREATE TABLE roadmaps (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title        VARCHAR(300) NOT NULL,
    description  TEXT,
    target_type  VARCHAR(50),             -- e.g. "NU", "Abroad_IT", "Abroad_Business"
    is_public    BOOLEAN DEFAULT TRUE,
    created_by   UUID NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

#### `roadmap_template_tasks`
```sql
CREATE TABLE roadmap_template_tasks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    roadmap_id    UUID NOT NULL REFERENCES roadmaps(id) ON DELETE CASCADE,
    title         VARCHAR(300) NOT NULL,
    description   TEXT,
    order_index   SMALLINT NOT NULL,
    days_offset   INT,                    -- relative day offset from assignment date
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

#### `student_roadmaps`
```sql
CREATE TABLE student_roadmaps (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    roadmap_id    UUID REFERENCES roadmaps(id) ON DELETE SET NULL,
    assigned_by   UUID NOT NULL REFERENCES users(id),
    title         VARCHAR(300) NOT NULL,  -- copy of roadmap title at time of assignment
    assigned_at   TIMESTAMPTZ DEFAULT NOW(),
    is_active     BOOLEAN DEFAULT TRUE
);
```

#### `tasks`
```sql
CREATE TABLE tasks (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_roadmap_id  UUID REFERENCES student_roadmaps(id) ON DELETE SET NULL,
    created_by          UUID NOT NULL REFERENCES users(id),   -- ADVISER or admin
    title               VARCHAR(300) NOT NULL,
    description         TEXT,
    status              VARCHAR(20) DEFAULT 'todo' CHECK (status IN ('todo','in_progress','done','overdue')),
    priority            VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
    deadline            TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    is_ADVISER_task   BOOLEAN DEFAULT TRUE,      -- FALSE = student personal task
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_student ON tasks(student_id, status);
CREATE INDEX idx_tasks_deadline ON tasks(deadline) WHERE deadline IS NOT NULL;
```

#### `appointments`
```sql
CREATE TABLE appointments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ADVISER_id  UUID NOT NULL REFERENCES users(id),
    slot_id       UUID NOT NULL REFERENCES availability_slots(id),
    status        VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending','confirmed','cancelled_by_student','cancelled_by_ADVISER','completed')),
    notes         TEXT,                    -- student notes for the meeting
    cancelled_at  TIMESTAMPTZ,
    cancel_reason TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

#### `availability_slots`
```sql
CREATE TABLE availability_slots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ADVISER_id    UUID NOT NULL REFERENCES users(id),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    duration_min    SMALLINT DEFAULT 45,
    is_available    BOOLEAN DEFAULT TRUE,       -- FALSE when booked
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_slots_ADVISER_time ON availability_slots(ADVISER_id, start_time);
CREATE INDEX idx_slots_available ON availability_slots(is_available, start_time);
```

#### `messages`
```sql
CREATE TABLE messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id     UUID NOT NULL REFERENCES users(id),
    body          TEXT NOT NULL,
    is_read       BOOLEAN DEFAULT FALSE,
    read_at       TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
```

#### `conversations`
```sql
CREATE TABLE conversations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ADVISER_id  UUID NOT NULL REFERENCES users(id),
    last_message_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(student_id, ADVISER_id)
);
```

#### `calendar_events`
```sql
CREATE TABLE calendar_events (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          VARCHAR(300) NOT NULL,
    description    TEXT,
    event_type     VARCHAR(30) CHECK (event_type IN (
                     'appointment','task_deadline','news_event',
                     'university_deadline','custom'
                   )),
    start_time     TIMESTAMPTZ NOT NULL,
    end_time       TIMESTAMPTZ,
    all_day        BOOLEAN DEFAULT FALSE,
    color          VARCHAR(7) DEFAULT '#3B82F6',     -- hex color
    source_id      UUID,                              -- FK to news/task/appointment
    source_type    VARCHAR(30),
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_calendar_user_time ON calendar_events(user_id, start_time);
```

#### `notifications`
```sql
CREATE TABLE notifications (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title          VARCHAR(300) NOT NULL,
    body           TEXT,
    type           VARCHAR(50) NOT NULL CHECK (type IN (
                     'new_task','task_deadline','new_message','appointment_confirmed',
                     'appointment_reminder','appointment_cancelled','new_news',
                     'deadline_reminder','roadmap_assigned','university_updated'
                   )),
    is_read        BOOLEAN DEFAULT FALSE,
    read_at        TIMESTAMPTZ,
    source_id      UUID,
    source_type    VARCHAR(30),
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
```

#### `faqs`
```sql
CREATE TABLE faqs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    category    VARCHAR(100),
    order_index SMALLINT DEFAULT 0,
    is_active   BOOLEAN DEFAULT TRUE,
    created_by  UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### `alumni_stories`
```sql
CREATE TABLE alumni_stories (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id        UUID NOT NULL REFERENCES users(id),
    student_name     VARCHAR(255) NOT NULL,
    graduation_year  SMALLINT,
    university_id    UUID REFERENCES universities(id),
    university_name  VARCHAR(300),                   -- in case university not in DB
    program_name     VARCHAR(300),
    scholarship_type VARCHAR(200),
    story_text       TEXT NOT NULL,
    photo_url        VARCHAR(500),
    gpa_at_time      NUMERIC(3,2),
    ielts_at_time    NUMERIC(3,1),
    sat_at_time      SMALLINT,
    is_published     BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);
```

#### `refresh_tokens`
```sql
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
```

---

## 4. Authentication & Authorization

### 4.1 JWT Strategy

- **Access Token**: expires in 60 minutes, signed with HS256, contains `user_id`, `role`, `email`
- **Refresh Token**: expires in 30 days, stored in DB as hashed value, rotated on each use
- **Password Reset**: 6-digit OTP sent to email, valid 15 minutes, stored in Redis

### 4.2 Token Flow

```
POST /auth/login
  → returns { access_token, refresh_token }

POST /auth/refresh
  → { refresh_token } → returns new { access_token, refresh_token }
  → old refresh_token invalidated immediately

POST /auth/logout
  → { refresh_token } → deletes from DB

POST /auth/forgot-password
  → { email } → sends OTP to email

POST /auth/reset-password
  → { email, otp, new_password } → updates hash
```

### 4.3 Role-Based Access Control

```python
# Permission matrix
PERMISSIONS = {
    "student": [
        "read:own_profile", "update:own_profile",
        "read:own_documents", "upload:own_documents",
        "read:universities", "read:news", "read:faqs",
        "read:alumni_stories", "read:roadmaps",
        "read:own_tasks", "update:own_task_status",
        "create:own_tasks",                          # personal tasks only
        "read:own_appointments", "create:appointment",
        "cancel:own_appointment",
        "read:own_messages", "send:message",
        "read:own_calendar", "create:own_calendar_event",
        "read:own_notifications",
    ],
    "ADVISER": [
        "read:all_students", "update:student_profile",
        "read:student_documents",
        "create:university", "update:university", "delete:university",
        "create:news", "update:news", "delete:news",
        "create:roadmap", "update:roadmap", "delete:roadmap",
        "assign:roadmap",
        "create:task", "update:task", "delete:task",
        "manage:availability_slots",
        "read:all_messages", "send:message", "broadcast:message",
        "read:all_notifications",
        "create:faq", "update:faq", "delete:faq",
        "create:alumni_story", "update:alumni_story",
        "read:reports",
    ],
    "admin": ["*"]  # all permissions
}
```

### 4.4 Middleware

```python
# Dependency injection pattern
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User: ...
async def require_role(*roles: str): ...
async def require_student(): ...
async def require_ADVISER_or_admin(): ...
```

---

## 5. API Endpoints

Base URL: `/api/v1`  
Auth header: `Authorization: Bearer <access_token>`

---

### 5.1 Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | ❌ | Student self-registration |
| POST | `/auth/login` | ❌ | Login for all roles |
| POST | `/auth/refresh` | ❌ | Refresh access token |
| POST | `/auth/logout` | ✅ | Invalidate refresh token |
| POST | `/auth/forgot-password` | ❌ | Send OTP to email |
| POST | `/auth/reset-password` | ❌ | Reset with OTP |
| POST | `/auth/change-password` | ✅ | Change own password |

**POST /auth/register**
```json
// Request
{
  "email": "aizat@college.edu.kz",
  "full_name": "Aizat Bekova",
  "password": "SecurePass123!",
  "group_type": "D",
  "course_year": 2,
  "gpa": 3.7,
  "ielts_passed": true,
  "ielts_score": 6.5,
  "sat_passed": false
}

// Response 201
{
  "success": true,
  "data": {
    "user": { "id": "uuid", "email": "aizat@...", "role": "student" },
    "access_token": "eyJ...",
    "refresh_token": "eyJ..."
  }
}
```

**POST /auth/login**
```json
// Request
{ "email": "ADVISER@college.edu.kz", "password": "pass" }

// Response 200
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "user": { "id": "uuid", "role": "ADVISER", "full_name": "Zarina Nurlanovna" }
  }
}
```

---

### 5.2 Users / Students

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/students` | ✅ | ADVISER/admin | List all students with filters |
| GET | `/students/{id}` | ✅ | ADVISER/admin/self | Get student full profile |
| PUT | `/students/{id}/profile` | ✅ | ADVISER/admin/self | Update student profile |
| GET | `/users/me` | ✅ | any | Get own profile |
| PUT | `/users/me` | ✅ | any | Update own profile |
| DELETE | `/students/{id}` | ✅ | admin | Delete student account |
| POST | `/ADVISER/students/invite` | ✅ | ADVISER/admin | Create student account manually |

**GET /students**
```
Query params:
  - group_type: D|F
  - course_year: 2|3
  - ielts_passed: true|false
  - sat_passed: true|false
  - search: string (full_name search)
  - page: int
  - page_size: int
```

```json
// Response 200
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "full_name": "Aizat Bekova",
      "email": "aizat@...",
      "group_type": "D",
      "course_year": 2,
      "gpa": 3.7,
      "ielts_passed": true,
      "ielts_score": 6.5,
      "sat_passed": false,
      "avatar_url": null,
      "tasks_total": 12,
      "tasks_done": 8,
      "unread_messages": 2,
      "last_seen": "2026-04-29T14:30:00Z"
    }
  ],
  "meta": { "page": 1, "page_size": 20, "total": 85 }
}
```

**GET /students/{id}** — Full profile for ADVISER view:
```json
{
  "success": true,
  "data": {
    "user": { "id": "uuid", "full_name": "...", "email": "..." },
    "profile": { "group_type": "D", "gpa": 3.7, "ielts_score": 6.5, ... },
    "documents": [
      { "doc_type": "cv", "file_name": "cv_aizat.pdf", "uploaded_at": "..." }
    ],
    "active_roadmap": { "id": "uuid", "title": "NU Roadmap", "progress_pct": 42 },
    "tasks_summary": { "total": 12, "done": 8, "overdue": 1 },
    "next_appointment": { "id": "uuid", "start_time": "2026-05-03T10:00:00Z" }
  }
}
```

---

### 5.3 Documents

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/students/{id}/documents` | ✅ | ADVISER/admin/self | List documents |
| POST | `/students/{id}/documents` | ✅ | self | Upload/replace document |
| GET | `/students/{id}/documents/{doc_type}` | ✅ | ADVISER/admin/self | Download document |
| DELETE | `/students/{id}/documents/{doc_type}` | ✅ | self/ADVISER | Delete document |

**POST /students/{id}/documents**
```
Content-Type: multipart/form-data

Fields:
  - doc_type: cv|motivation_letter|recommendation_letter|personal_statement|other
  - file: <binary>

Constraints:
  - Max file size: 10 MB
  - Allowed MIME types: application/pdf, application/msword,
    application/vnd.openxmlformats-officedocument.wordprocessingml.document
  - One document per type (replace existing)
```

```json
// Response 201
{
  "success": true,
  "data": {
    "id": "uuid",
    "doc_type": "cv",
    "file_name": "cv_aizat.pdf",
    "file_size": 245678,
    "uploaded_at": "2026-04-30T10:00:00Z"
  }
}
```

---

### 5.4 Universities

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/universities` | ✅ | any | List with filters |
| GET | `/universities/{id}` | ✅ | any | Get detail with programs |
| POST | `/universities` | ✅ | ADVISER/admin | Create |
| PUT | `/universities/{id}` | ✅ | ADVISER/admin | Update |
| DELETE | `/universities/{id}` | ✅ | ADVISER/admin | Soft delete |
| POST | `/universities/{id}/programs` | ✅ | ADVISER/admin | Add program |
| PUT | `/universities/{id}/programs/{prog_id}` | ✅ | ADVISER/admin | Update program |
| DELETE | `/universities/{id}/programs/{prog_id}` | ✅ | ADVISER/admin | Delete program |

**GET /universities**
```
Query params:
  - country: string
  - field: string (CS, Business, etc.)
  - min_gpa: float
  - max_tuition: int
  - degree_level: bachelor|master
  - has_scholarship: bool
  - search: string (name search)
  - page, page_size
```

**GET /universities/{id}** — includes structured data similar to unitap.kz:
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Nazarbayev University",
    "country": "Kazakhstan",
    "city": "Astana",
    "logo_url": "https://...",
    "qs_ranking": 219,
    "acceptance_rate": 15.0,
    "total_students": 8500,
    "international_pct": 12.0,
    "language_of_instr": "English",
    "last_verified_at": "2026-01-15T00:00:00Z",
    "programs": [
      {
        "id": "uuid",
        "name": "Computer Science",
        "degree_level": "bachelor",
        "min_gpa": 3.5,
        "min_ielts": 6.5,
        "tuition_usd": 0,
        "scholarship_info": "Full scholarship available",
        "deadline": "2026-02-01",
        "intake_seasons": "Fall",
        "requirements_text": "...",
        "apply_url": "https://..."
      }
    ]
  }
}
```

---

### 5.5 News & Events

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/news` | ✅ | any | List news/events |
| GET | `/news/{id}` | ✅ | any | Get detail |
| POST | `/news` | ✅ | ADVISER/admin | Create |
| PUT | `/news/{id}` | ✅ | ADVISER/admin | Update |
| DELETE | `/news/{id}` | ✅ | ADVISER/admin | Delete |
| POST | `/news/{id}/add-to-calendar` | ✅ | student | Add event to own calendar |

**GET /news**
```
Query params:
  - category: olympiad|hackathon|deadline|summer_camp|webinar|internship|university_news|general
  - upcoming: bool (event_date >= today)
  - page, page_size
```

**POST /news** (ADVISER)
```json
// Request
{
  "title": "MIT Hackathon 2026",
  "body": "Annual international hackathon...",
  "category": "hackathon",
  "event_date": "2026-06-15",
  "external_url": "https://hackathon.mit.edu",
  "is_published": true
}

// Response 201
{ "success": true, "data": { "id": "uuid", ... } }
```

**POST /news/{id}/add-to-calendar** — creates calendar_event for the student:
```json
// Request
{ "reminder_days_before": 3 }
// Creates calendar_event with source_type="news", source_id=news.id
```

---

### 5.6 Tasks

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/students/{id}/tasks` | ✅ | ADVISER/admin/self | List tasks |
| POST | `/students/{id}/tasks` | ✅ | ADVISER/admin | Create ADVISER task for student |
| POST | `/tasks/personal` | ✅ | student | Create own personal task |
| PUT | `/tasks/{id}` | ✅ | ADVISER/admin or task-owner | Update task |
| PATCH | `/tasks/{id}/status` | ✅ | student (own) | Update task status |
| DELETE | `/tasks/{id}` | ✅ | ADVISER/admin | Delete |
| GET | `/tasks/{id}` | ✅ | ADVISER/admin/self | Get task detail |

**POST /students/{id}/tasks** (ADVISER):
```json
// Request
{
  "title": "Prepare for IELTS Speaking",
  "description": "Practice speaking test with partner 3 times per week",
  "priority": "high",
  "deadline": "2026-05-30T23:59:00Z",
  "student_roadmap_id": "uuid-optional"
}
```

**PATCH /tasks/{id}/status** (student):
```json
// Request
{ "status": "done" }
// Triggers: notification to ADVISER, auto-set completed_at
```

**GET /students/{id}/tasks**
```
Query params:
  - status: todo|in_progress|done|overdue
  - is_ADVISER_task: bool
  - page, page_size
```

---

### 5.7 Roadmaps

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/roadmaps` | ✅ | any | List public roadmaps |
| GET | `/roadmaps/{id}` | ✅ | any | Get roadmap detail with template tasks |
| POST | `/roadmaps` | ✅ | ADVISER/admin | Create roadmap |
| PUT | `/roadmaps/{id}` | ✅ | ADVISER/admin | Update |
| DELETE | `/roadmaps/{id}` | ✅ | ADVISER/admin | Delete |
| POST | `/roadmaps/{id}/assign` | ✅ | ADVISER/admin | Assign roadmap to student |
| GET | `/students/{id}/roadmaps` | ✅ | ADVISER/admin/self | Get student assigned roadmaps |

**POST /roadmaps/{id}/assign** (ADVISER):
```json
// Request
{
  "student_id": "uuid",
  "customize_tasks": [
    { "template_task_id": "uuid", "deadline": "2026-06-01T23:59:00Z" }
  ]
}
// Effect:
//   1. Creates student_roadmap record
//   2. Creates tasks from template + custom deadlines
//   3. Adds deadline tasks to student calendar
//   4. Sends notification to student
```

---

### 5.8 Appointments

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/appointments/slots` | ✅ | student | Get available ADVISER slots |
| POST | `/appointments/slots` | ✅ | ADVISER/admin | Create availability slot(s) |
| DELETE | `/appointments/slots/{id}` | ✅ | ADVISER/admin | Delete slot (if not booked) |
| POST | `/appointments` | ✅ | student | Book appointment |
| GET | `/appointments` | ✅ | ADVISER/admin | List all appointments |
| GET | `/appointments/my` | ✅ | student | List own appointments |
| PATCH | `/appointments/{id}/cancel` | ✅ | student/ADVISER | Cancel appointment |
| PATCH | `/appointments/{id}/complete` | ✅ | ADVISER/admin | Mark completed |

**POST /appointments/slots** (ADVISER — create weekly schedule):
```json
// Request
{
  "slots": [
    { "start_time": "2026-05-05T09:00:00+06:00", "duration_min": 45 },
    { "start_time": "2026-05-05T10:00:00+06:00", "duration_min": 45 },
    { "start_time": "2026-05-06T14:00:00+06:00", "duration_min": 45 }
  ]
}
```

**POST /appointments** (student):
```json
// Request
{ "slot_id": "uuid", "notes": "Want to discuss IELTS preparation" }

// Effect:
//   1. Creates appointment record
//   2. Marks slot as unavailable
//   3. Creates calendar_event for student
//   4. Creates calendar_event for ADVISER
//   5. Sends email + in-app notifications to both
//   6. Schedules reminder job (same-day for both)
```

**PATCH /appointments/{id}/cancel**:
```json
// Request
{ "reason": "Schedule conflict" }

// Effect:
//   1. Updates appointment status
//   2. Re-marks slot as available
//   3. Removes calendar events
//   4. Notifies other party via email + in-app
```

---

### 5.9 Messages (Chat)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/conversations` | ✅ | ADVISER/admin | List all conversations |
| GET | `/conversations/my` | ✅ | student | Get own conversation |
| GET | `/conversations/{id}/messages` | ✅ | participant | Get messages (paginated) |
| POST | `/conversations/{id}/messages` | ✅ | participant | Send message |
| PATCH | `/conversations/{id}/read` | ✅ | participant | Mark messages as read |
| POST | `/messages/broadcast` | ✅ | ADVISER/admin | Send message to all students |

**GET /conversations/{id}/messages**:
```
Query params: page, page_size (newest first)
```

```json
// Response
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "sender_id": "uuid",
      "sender_name": "Zarina Nurlanovna",
      "sender_role": "ADVISER",
      "body": "Don't forget to submit your CV draft before our meeting",
      "is_read": false,
      "created_at": "2026-04-30T09:15:00Z"
    }
  ],
  "meta": { "page": 1, "total": 42 }
}
```

**POST /messages/broadcast** (ADVISER):
```json
// Request
{
  "body": "Reminder: IELTS registration deadline is May 15!",
  "filter": {
    "group_type": "D",
    "ielts_passed": false
  }
}
// Creates individual message in each matching student's conversation
// Sends push notification to each
```

---

### 5.10 Calendar

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/calendar` | ✅ | any | Get own calendar events |
| POST | `/calendar` | ✅ | any | Create manual calendar event |
| PUT | `/calendar/{id}` | ✅ | owner | Update event |
| DELETE | `/calendar/{id}` | ✅ | owner | Delete event |

**GET /calendar**:
```
Query params:
  - from: ISO date
  - to: ISO date
  - event_type: appointment|task_deadline|news_event|university_deadline|custom
```

```json
// Response
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "Meeting with ADVISER",
      "event_type": "appointment",
      "start_time": "2026-05-03T10:00:00+06:00",
      "end_time": "2026-05-03T10:45:00+06:00",
      "color": "#3B82F6",
      "source": { "type": "appointment", "id": "uuid" }
    }
  ]
}
```

---

### 5.11 Notifications

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/notifications` | ✅ | any | Get own notifications |
| PATCH | `/notifications/{id}/read` | ✅ | owner | Mark single as read |
| PATCH | `/notifications/read-all` | ✅ | any | Mark all as read |
| GET | `/notifications/unread-count` | ✅ | any | Get unread count |

```json
// GET /notifications response
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "type": "new_task",
      "title": "New task assigned",
      "body": "ADVISER assigned: Complete IELTS mock test",
      "is_read": false,
      "created_at": "2026-04-30T08:00:00Z",
      "source": { "type": "task", "id": "uuid" }
    }
  ]
}
```

---

### 5.12 FAQ

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/faqs` | ✅ | any | List active FAQs |
| POST | `/faqs` | ✅ | ADVISER/admin | Create FAQ |
| PUT | `/faqs/{id}` | ✅ | ADVISER/admin | Update |
| DELETE | `/faqs/{id}` | ✅ | ADVISER/admin | Delete |
| PATCH | `/faqs/reorder` | ✅ | ADVISER/admin | Reorder FAQs |

---

### 5.13 Alumni Stories

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/alumni` | ✅ | any | List published stories |
| GET | `/alumni/{id}` | ✅ | any | Get story detail |
| POST | `/alumni` | ✅ | ADVISER/admin | Create story |
| PUT | `/alumni/{id}` | ✅ | ADVISER/admin | Update |
| DELETE | `/alumni/{id}` | ✅ | ADVISER/admin | Delete |

---

### 5.14 Reports (ADVISER/Admin)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/reports/overview` | ✅ | ADVISER/admin | Dashboard statistics |
| GET | `/reports/students` | ✅ | ADVISER/admin | Student progress report |
| GET | `/reports/universities` | ✅ | ADVISER/admin | Application statistics |

**GET /reports/overview**:
```json
{
  "success": true,
  "data": {
    "total_students": 92,
    "by_group": { "D": 47, "F": 45 },
    "ielts_passed": 34,
    "sat_passed": 21,
    "avg_gpa": 3.42,
    "tasks_completed_this_month": 187,
    "appointments_this_month": 24,
    "applied_abroad": 8
  }
}
```

---

## 6. Notification System

### 6.1 Trigger Matrix

| Event | Recipient | Channel | Timing |
|-------|-----------|---------|--------|
| Student registers | ADVISER | In-app + Email | Immediate |
| ADVISER assigns task | Student | In-app + Email | Immediate |
| Student completes task | ADVISER | In-app | Immediate |
| New message received | Other party | In-app | Immediate |
| Appointment booked | Both | In-app + Email | Immediate |
| Appointment reminder | Both | In-app + Email | Same day (08:00) |
| Appointment cancelled | Other party | In-app + Email | Immediate |
| Task deadline approaching (3 days) | Student | In-app + Email | 08:00 local time |
| Task deadline approaching (1 day) | Student | In-app + Email | 08:00 local time |
| Task overdue | Student | In-app | 08:00 local time |
| News event published | All students | In-app | Immediate |
| University data staleness (1 year) | ADVISER | In-app + Email | Once per day check |
| Roadmap assigned | Student | In-app + Email | Immediate |

### 6.2 Notification Creation Flow

```python
async def create_notification(
    user_id: UUID,
    type: NotificationType,
    title: str,
    body: str,
    source_id: UUID | None = None,
    source_type: str | None = None,
):
    # 1. Insert to notifications table
    # 2. Queue email if email_required[type]
    # 3. Push to WebSocket if connected (optional: future SSE/WebSocket)
```

### 6.3 In-App Delivery via Polling

Since WebSocket adds complexity, polling is used for MVP:
- `GET /notifications/unread-count` — called every 30 seconds by frontend
- Full notifications list fetched on app open

---

## 7. File Storage Strategy

### 7.1 MinIO (Self-Hosted S3)

MinIO is deployed as a Docker service. It provides S3-compatible API, runs on the college server, and has no per-request cost.

**Buckets:**
```
eduadviser-documents/   → student documents (CV, letters)
eduadviser-avatars/     → user profile photos
eduadviser-universities/ → university logos and covers
eduadviser-news/        → news cover images
eduadviser-alumni/      → alumni story photos
```

**Access Policy:**
- `eduadviser-documents/` — **private** (access via signed URLs only)
- All other buckets — **public-read**

### 7.2 Signed URL Generation

```python
def get_signed_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    # generates pre-signed GET URL valid for expires_in seconds
    # Used for: document downloads
```

### 7.3 File Validation

```python
ALLOWED_DOC_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
}
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
```

---

## 8. Email Integration

### 8.1 SMTP Configuration

Use college SMTP server (primary) or Brevo free tier (backup, 300 emails/day free).

```python
EMAIL_HOST = "smtp.college.edu.kz"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "noreply@eduadviser.college.edu.kz"
```

### 8.2 Email Templates

All emails are HTML templates using Jinja2:

| Template | Trigger |
|----------|---------|
| `welcome.html` | Student registration |
| `password_reset.html` | Forgot password OTP |
| `appointment_confirmed.html` | Appointment booked |
| `appointment_reminder.html` | Day-of reminder |
| `appointment_cancelled.html` | Cancellation |
| `task_assigned.html` | New task from ADVISER |
| `deadline_reminder.html` | 3-day and 1-day task deadline |
| `new_message.html` | Unread message summary |

### 8.3 Email Sending via Celery

All emails are sent asynchronously via Celery to avoid blocking request handlers:

```python
@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, to: str, subject: str, template: str, context: dict):
    try:
        render_and_send(to, subject, template, context)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

---

## 9. Background Jobs (Celery)

### 9.1 Celery Configuration

```python
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/1"
CELERY_TIMEZONE = "Asia/Almaty"
```

### 9.2 Periodic Tasks (Celery Beat)

| Task | Schedule | Description |
|------|----------|-------------|
| `check_task_deadlines` | Every day at 08:00 | Find tasks due in 3 days and 1 day, send reminders |
| `mark_overdue_tasks` | Every day at 00:01 | Set `status=overdue` for past-deadline uncompleted tasks |
| `check_appointment_reminders` | Every hour | Find appointments today, send reminder at 08:00 |
| `check_university_staleness` | Every day at 09:00 | Find universities not verified in >365 days, notify ADVISER |
| `cleanup_expired_tokens` | Every day at 02:00 | Delete expired refresh tokens from DB |

### 9.3 Task Definitions

```python
# tasks/reminders.py

@celery_app.task
def check_task_deadlines():
    now = datetime.now(tz=ALMATY_TZ)
    three_days = now + timedelta(days=3)
    one_day = now + timedelta(days=1)

    # Find tasks with deadline in [now+2d 23:59, now+3d 23:59]
    # and deadline in [now 23:59, now+1d 23:59]
    # Create notifications and send emails for each

@celery_app.task
def mark_overdue_tasks():
    now = datetime.now(tz=ALMATY_TZ)
    # UPDATE tasks SET status='overdue'
    # WHERE status NOT IN ('done','overdue') AND deadline < now

@celery_app.task
def send_appointment_reminders():
    now = datetime.now(tz=ALMATY_TZ)
    today_start = now.replace(hour=0, minute=0, second=0)
    today_end = today_start + timedelta(days=1)
    # Find confirmed appointments today
    # If current time is 08:00 ± 5min, send reminder
```

---

## 10. Error Handling & Validation

### 10.1 HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Successful GET, PUT, PATCH |
| 201 | Successful POST (created) |
| 204 | Successful DELETE |
| 400 | Validation error, bad request |
| 401 | Unauthenticated (no/invalid token) |
| 403 | Unauthorized (valid token, wrong role) |
| 404 | Resource not found |
| 409 | Conflict (duplicate, slot already booked) |
| 413 | File too large |
| 422 | Unprocessable entity (Pydantic validation) |
| 500 | Internal server error |

### 10.2 Custom Error Codes

```python
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    SLOT_ALREADY_BOOKED = "SLOT_ALREADY_BOOKED"
    DOCUMENT_TYPE_EXISTS = "DOCUMENT_TYPE_EXISTS"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    INVALID_OTP = "INVALID_OTP"
    OTP_EXPIRED = "OTP_EXPIRED"
    APPOINTMENT_CANCEL_DENIED = "APPOINTMENT_CANCEL_DENIED"
```

### 10.3 Global Exception Handler

```python
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )
```

### 10.4 Input Validation Rules

```python
# Student Profile
class StudentProfileUpdate(BaseModel):
    gpa: float = Field(None, ge=0.0, le=4.0)
    ielts_score: float = Field(None, ge=0.0, le=9.0)
    sat_score: int = Field(None, ge=400, le=1600)
    ent_score: int = Field(None, ge=0, le=140)
    course_year: int = Field(None, ge=2, le=3)
    group_type: Literal["D", "F"] = None

# Task
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str = Field(None, max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"
    deadline: datetime = Field(None)  # must be in future

    @field_validator("deadline")
    def deadline_must_be_future(cls, v):
        if v and v <= datetime.now(tz=timezone.utc):
            raise ValueError("Deadline must be in the future")
        return v
```

---

## 11. Project Structure

```
eduadviser-backend/
├── app/
│   ├── main.py                  # FastAPI app factory
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # Async SQLAlchemy engine + session
│   ├── dependencies.py          # Shared FastAPI dependencies
│   │
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── student_profile.py
│   │   ├── document.py
│   │   ├── university.py
│   │   ├── news.py
│   │   ├── task.py
│   │   ├── roadmap.py
│   │   ├── appointment.py
│   │   ├── message.py
│   │   ├── calendar_event.py
│   │   ├── notification.py
│   │   ├── faq.py
│   │   └── alumni_story.py
│   │
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── student.py
│   │   ├── document.py
│   │   ├── university.py
│   │   ├── news.py
│   │   ├── task.py
│   │   ├── roadmap.py
│   │   ├── appointment.py
│   │   ├── message.py
│   │   ├── calendar.py
│   │   ├── notification.py
│   │   └── report.py
│   │
│   ├── routers/                 # API route handlers
│   │   ├── auth.py
│   │   ├── students.py
│   │   ├── documents.py
│   │   ├── universities.py
│   │   ├── news.py
│   │   ├── tasks.py
│   │   ├── roadmaps.py
│   │   ├── appointments.py
│   │   ├── messages.py
│   │   ├── calendar.py
│   │   ├── notifications.py
│   │   ├── faqs.py
│   │   ├── alumni.py
│   │   └── reports.py
│   │
│   ├── services/                # Business logic
│   │   ├── auth_service.py
│   │   ├── student_service.py
│   │   ├── document_service.py
│   │   ├── university_service.py
│   │   ├── news_service.py
│   │   ├── task_service.py
│   │   ├── roadmap_service.py
│   │   ├── appointment_service.py
│   │   ├── message_service.py
│   │   ├── calendar_service.py
│   │   ├── notification_service.py
│   │   └── report_service.py
│   │
│   ├── core/
│   │   ├── security.py          # JWT, bcrypt helpers
│   │   ├── permissions.py       # RBAC decorators
│   │   ├── exceptions.py        # Custom exception classes
│   │   └── constants.py
│   │
│   ├── workers/
│   │   ├── celery_app.py        # Celery app factory
│   │   ├── email_tasks.py       # Email sending tasks
│   │   ├── reminder_tasks.py    # Deadline/appointment reminders
│   │   └── maintenance_tasks.py # DB cleanup, staleness checks
│   │
│   ├── storage/
│   │   ├── minio_client.py      # MinIO S3 client wrapper
│   │   └── file_validator.py
│   │
│   └── email/
│       ├── sender.py
│       └── templates/
│           ├── base.html
│           ├── welcome.html
│           ├── password_reset.html
│           ├── appointment_confirmed.html
│           ├── appointment_reminder.html
│           ├── appointment_cancelled.html
│           ├── task_assigned.html
│           ├── deadline_reminder.html
│           └── new_message.html
│
├── migrations/                  # Alembic migrations
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
│   ├── seed_data.py             # Initial data seeding
│   └── create_admin.py         # Create admin user
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

## 12. Docker Compose Configuration

```yaml
# docker-compose.yml

version: "3.9"

services:

  # ─── PostgreSQL ──────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    container_name: ec_postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ec_network

  # ─── Redis ───────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: ec_redis
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - ec_network

  # ─── MinIO ───────────────────────────────────────────────
  minio:
    image: minio/minio:latest
    container_name: ec_minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"     # MinIO console (remove in production)
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - ec_network

  # ─── FastAPI ─────────────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: ec_api
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ROOT_USER}
      - MINIO_SECRET_KEY=${MINIO_ROOT_PASSWORD}
    env_file:
      - .env
    volumes:
      - ./app:/app/app         # hot reload in dev
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    networks:
      - ec_network

  # ─── Celery Worker ───────────────────────────────────────
  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.celery
    container_name: ec_celery_worker
    depends_on:
      - redis
      - postgres
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
    networks:
      - ec_network

  # ─── Celery Beat (Scheduler) ─────────────────────────────
  celery_beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.celery
    container_name: ec_celery_beat
    depends_on:
      - redis
      - postgres
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
    command: celery -A app.workers.celery_app beat --loglevel=info --scheduler redbeat.RedBeatScheduler
    networks:
      - ec_network

  # ─── Nginx ───────────────────────────────────────────────
  nginx:
    image: nginx:alpine
    container_name: ec_nginx
    depends_on:
      - api
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./static:/static:ro
      - certbot_certs:/etc/letsencrypt:ro
    networks:
      - ec_network

volumes:
  postgres_data:
  redis_data:
  minio_data:
  certbot_certs:

networks:
  ec_network:
    driver: bridge
```

---

## 13. Environment Variables

```bash
# .env.example

# ─── App ─────────────────────────────────────────────────
APP_ENV=development                      # development | production
APP_SECRET_KEY=change-this-to-a-very-long-random-secret
APP_HOST=https://eduadviser.college.edu.kz

# ─── JWT ─────────────────────────────────────────────────
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
JWT_ALGORITHM=HS256

# ─── Database ────────────────────────────────────────────
POSTGRES_DB=eduadviser
POSTGRES_USER=ec_user
POSTGRES_PASSWORD=change_this_password

# ─── Redis ───────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── MinIO ───────────────────────────────────────────────
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=change_this_minio_password
MINIO_ENDPOINT=minio:9000
MINIO_USE_SSL=false                      # true in production with SSL

# ─── Email ───────────────────────────────────────────────
EMAIL_HOST=smtp.college.edu.kz
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=noreply@eduadviser.college.edu.kz
EMAIL_HOST_PASSWORD=smtp_password
EMAIL_FROM_NAME=eduadviser

# ─── Timezone ────────────────────────────────────────────
TZ=Asia/Almaty

# ─── File Limits ─────────────────────────────────────────
MAX_DOCUMENT_SIZE_MB=10
MAX_IMAGE_SIZE_MB=5

# ─── ADVISER Account ───────────────────────────────────
ADVISER_EMAIL=ADVISER@college.edu.kz
ADVISER_INITIAL_PASSWORD=change_immediately
```

---

## 14. Security Requirements

### 14.1 Password Policy
- Minimum 8 characters
- At least one uppercase letter, one lowercase, one digit
- Hashed with bcrypt (cost factor 12)

### 14.2 Token Security
- Access token: short-lived (60 min), contains only essential claims
- Refresh token: stored as bcrypt hash in DB, rotated on every use
- Old refresh tokens immediately invalidated (prevents reuse after theft)

### 14.3 File Upload Security
```python
# Validate MIME type by reading file magic bytes, NOT just extension
import magic
def validate_file_type(file_bytes: bytes, allowed_types: set[str]) -> bool:
    detected = magic.from_buffer(file_bytes, mime=True)
    return detected in allowed_types
```

### 14.4 SQL Injection Prevention
- All queries via SQLAlchemy ORM (parameterized)
- No raw SQL strings with user input
- Alembic migrations for schema changes only

### 14.5 Rate Limiting
```python
# Using slowapi (FastAPI rate limiter)
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("5/minute")          # Prevent brute force
async def login(request: Request, ...): ...

@router.post("/auth/forgot-password")
@limiter.limit("3/minute")          # Prevent OTP spam
async def forgot_password(request: Request, ...): ...
```

### 14.6 CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://eduadviser.college.edu.kz",   # Web dashboard
        "http://localhost:3000",                  # Dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 14.7 Data Privacy
- Student documents stored in private MinIO bucket
- Access only via time-limited signed URLs (1 hour)
- ADVISER can only view documents of own students
- No cross-student data exposure

---

## 15. Performance & Scalability

### 15.1 Target Load
- 100 active users, single ADVISER
- Peak: 20 concurrent users
- Message history: ~200 messages per conversation
- Database size: estimated <5 GB for 2 years

### 15.2 Database Optimizations
- All FK columns indexed
- Composite indexes on frequent query patterns (see schema)
- Pagination on all list endpoints (max page_size=100)
- Async SQLAlchemy with connection pool (pool_size=10, max_overflow=20)

### 15.3 Caching Strategy (Redis)
```python
# Cache keys
CACHE_KEYS = {
    "universities_list": "universities:list:{hash_of_filters}",  # TTL: 5 min
    "faqs": "faqs:active",                                        # TTL: 10 min
    "roadmaps_public": "roadmaps:public",                         # TTL: 5 min
    "unread_count:{user_id}": "notifications:unread:{user_id}",   # TTL: 1 min
}
```

### 15.4 File Upload Performance
- Stream multipart uploads directly to MinIO (no full load into RAM)
- Use `python-multipart` streaming

---

## 16. Development Roadmap / MVP Plan

Given the 1-week deadline for MVP, the following priority order is recommended:

### Week 1 (MVP — Core Features)

| Priority | Feature | Estimated Time |
|----------|---------|----------------|
| P0 | Docker setup + DB schema + migrations | Day 1 |
| P0 | Auth (register, login, JWT, refresh) | Day 1 |
| P0 | Student profile CRUD | Day 2 |
| P0 | Tasks (ADVISER creates, student updates status) | Day 2 |
| P1 | Documents upload/download | Day 3 |
| P1 | Messages (1-on-1 chat) | Day 3 |
| P1 | Appointments (slots + booking) | Day 4 |
| P1 | Universities (CRUD + list with filters) | Day 4 |
| P1 | News & Events (CRUD + add to calendar) | Day 5 |
| P1 | Calendar (events aggregation) | Day 5 |
| P2 | Notifications (in-app) | Day 6 |
| P2 | Roadmaps (CRUD + assign to student) | Day 6 |
| P2 | Email notifications (Celery) | Day 7 |
| P2 | Reports + FAQ + Alumni Stories | Day 7 |

### Post-MVP (After Launch)
- Broadcast messaging
- Advanced university filters + smart matching
- Celery Beat scheduled reminders
- University staleness tracking
- Full test coverage

---

## Appendix A: Dockerfile

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# System deps for python-magic, psycopg2
RUN apt-get update && apt-get install -y \
    libmagic1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
```

## Appendix B: Core Requirements File

```txt
# requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.29.0
gunicorn==22.0.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.7.1
pydantic-settings==2.2.1
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
celery==5.3.6
redis==5.0.4
redbeat==2.2.0
minio==7.2.7
python-magic==0.4.27
jinja2==3.1.4
aiosmtplib==3.0.1
slowapi==0.1.9
httpx==0.27.0       # for testing
pytest==8.2.0
pytest-asyncio==0.23.6
```

---

*End of Technical Specification*  
*eduadviser Backend — v1.0 — April 2026*
