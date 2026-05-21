"""Seed script for Nobal Education.

Generates a large, realistic dataset that matches the CURRENT models
(adviser_id / is_adviser_task naming, enrollments, task history, the extended
profile / university / document / appointment fields, etc.).

Run inside the API container:
    python -m scripts.seed_data

Behaviour:
    * Admin and adviser accounts are get-or-created (matched by email), so it is
      safe to run against a DB that already has those accounts.
    * If student data already exists, the script skips unless SEED_FORCE=1.
"""

import asyncio
import io
import os
import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.config import settings
from app.core.constants import (
    APPOINTMENT_STATUS_COMPLETED,
    APPOINTMENT_STATUS_CONFIRMED,
    APPOINTMENT_STATUS_PENDING,
    BUCKET_DOCUMENTS,
    BUCKET_MESSAGES,
    ROLE_ADMIN,
    ROLE_ADVISER,
    ROLE_STUDENT,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_OVERDUE,
    TASK_STATUS_TODO,
)
from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.modules.alumni.models import AlumniStory
from app.modules.appointments.models import Appointment, AvailabilitySlot
from app.modules.auth.models import RefreshToken
from app.modules.calendar.models import CalendarEvent
from app.modules.documents.models import StudentDocument
from app.modules.enrollments.models import Enrollment
from app.modules.faq.models import FAQ
from app.modules.messages.models import Conversation, Message
from app.modules.news.models import News
from app.modules.notifications.models import Notification
from app.modules.profile.models import StudentProfile
from app.modules.roadmaps.models import Roadmap, RoadmapTemplateTask, StudentRoadmap
from app.modules.tasks.models import Task, TaskHistory
from app.modules.universities.models import University, UniversityProgram
from app.modules.users.models import User
from app.storage.minio_client import init_buckets, upload_file

# ──────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────
DEFAULT_PASSWORD = os.getenv("SEED_PASSWORD", "Student2026!")
N_STUDENTS = int(os.getenv("SEED_STUDENTS", "30"))
ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@nobal.tech")

random.seed(42)

# ──────────────────────────────────────────────────────────────────────────
# Data pools
# ──────────────────────────────────────────────────────────────────────────
MALE_NAMES = [
    "Dias", "Alim", "Nursultan", "Timur", "Yerlan", "Arman", "Daniyar", "Bekzat",
    "Sanzhar", "Aibek", "Ruslan", "Olzhas", "Damir", "Azamat", "Miras",
]
FEMALE_NAMES = [
    "Aruzhan", "Madina", "Aigerim", "Sofiya", "Amina", "Dana", "Aizhan", "Kamila",
    "Aknur", "Tomiris", "Zarina", "Inkar", "Diana", "Ayauzhan", "Saule",
]
SURNAMES = [
    "Toleuov", "Akhmetova", "Bekov", "Sultanova", "Nurlanov", "Kassymova",
    "Ospanov", "Zhaksybekova", "Mukhamedov", "Serikova", "Abdrakhmanov",
    "Iskakova", "Tursynbek", "Omarova", "Yermekov", "Aldiyarova",
]
TARGET_COUNTRIES = ["USA", "UK", "Canada", "Germany", "Netherlands", "South Korea",
                    "Singapore", "Australia", "Kazakhstan", "Poland", "Turkey", "UAE"]
MAJORS = ["Computer Science", "Business", "Economics", "Engineering", "Data Science",
          "Medicine", "Design", "International Relations", "Finance", "Law",
          "Biotechnology", "Architecture"]
SCHOOLS = ["NIS Almaty", "RFMSh", "BIL Astana", "Haileybury Almaty", "Lyceum #134",
           "Gymnasium #1", "Miras International School", "QSI Astana"]
GENDERS_BY_NAME = "infer"  # determined from name lists

# (name, country, city, qs, the, accept%, total_students, intl%, lang)
UNIVERSITIES = [
    ("Nazarbayev University", "Kazakhstan", "Astana", 219, 351, Decimal("22.50"), 6500, Decimal("18.00"), "English"),
    ("KIMEP University", "Kazakhstan", "Almaty", 651, None, Decimal("45.00"), 4200, Decimal("9.50"), "English"),
    ("Al-Farabi Kazakh National University", "Kazakhstan", "Almaty", 150, 801, Decimal("38.00"), 22000, Decimal("11.00"), "Kazakh / Russian / English"),
    ("Suleyman Demirel University", "Kazakhstan", "Kaskelen", 591, None, Decimal("52.00"), 5800, Decimal("7.00"), "English / Kazakh"),
    ("Massachusetts Institute of Technology", "USA", "Cambridge", 1, 3, Decimal("4.10"), 11500, Decimal("33.00"), "English"),
    ("University of Manchester", "UK", "Manchester", 32, 51, Decimal("56.00"), 40000, Decimal("28.00"), "English"),
    ("University of Toronto", "Canada", "Toronto", 21, 21, Decimal("43.00"), 97000, Decimal("25.00"), "English"),
    ("National University of Singapore", "Singapore", "Singapore", 8, 19, Decimal("5.00"), 38000, Decimal("30.00"), "English"),
    ("Seoul National University", "South Korea", "Seoul", 41, 62, Decimal("14.00"), 28000, Decimal("13.00"), "English / Korean"),
    ("Delft University of Technology", "Netherlands", "Delft", 47, 48, Decimal("65.00"), 27000, Decimal("32.00"), "English"),
    ("University of Melbourne", "Australia", "Melbourne", 14, 39, Decimal("70.00"), 52000, Decimal("44.00"), "English"),
    ("Technical University of Munich", "Germany", "Munich", 28, 37, Decimal("8.00"), 50000, Decimal("39.00"), "English / German"),
    ("Warsaw University of Technology", "Poland", "Warsaw", 801, None, Decimal("60.00"), 24000, Decimal("12.00"), "English / Polish"),
    ("Koç University", "Turkey", "Istanbul", 415, 401, Decimal("30.00"), 7000, Decimal("16.00"), "English"),
    ("Khalifa University", "UAE", "Abu Dhabi", 230, 201, Decimal("25.00"), 4000, Decimal("21.00"), "English"),
]

# (program name, degree, field, min_gpa, min_ielts, min_sat, tuition_usd, fee, seasons)
PROGRAM_TEMPLATES = [
    ("Computer Science", "bachelor", "CS", Decimal("3.2"), Decimal("6.5"), 1300, 0, 75, "Fall"),
    ("Software Engineering", "bachelor", "CS", Decimal("3.0"), Decimal("6.0"), 1250, 12000, 60, "Fall, Spring"),
    ("Data Science", "master", "Data", Decimal("3.3"), Decimal("6.5"), None, 22000, 90, "Fall"),
    ("Business Administration", "bachelor", "Business", Decimal("2.8"), Decimal("6.0"), 1200, 14000, 50, "Fall, Spring"),
    ("Economics", "bachelor", "Economics", Decimal("3.1"), Decimal("6.5"), 1320, 16000, 70, "Fall"),
    ("Electrical Engineering", "bachelor", "Engineering", Decimal("3.0"), Decimal("6.0"), 1280, 18000, 60, "Fall"),
    ("Mechanical Engineering", "bachelor", "Engineering", Decimal("3.0"), Decimal("6.0"), 1260, 19000, 60, "Fall"),
    ("Medicine", "bachelor", "Health", Decimal("3.6"), Decimal("7.0"), 1450, 25000, 120, "Spring"),
    ("International Relations", "bachelor", "Humanities", Decimal("3.0"), Decimal("6.5"), 1240, 15000, 55, "Fall"),
    ("Architecture", "bachelor", "Design", Decimal("2.9"), Decimal("6.0"), 1220, 17000, 65, "Fall"),
]

ROADMAP_SPECS = [
    ("NU Admission Roadmap", "Step-by-step plan for the Nazarbayev University application.", "NU"),
    ("Study Abroad: CS", "Apply to top computer science programs abroad.", "Abroad_IT"),
    ("Business Schools Track", "Application track for international business schools.", "Abroad_Business"),
    ("Scholarship Hunter", "Scholarship-focused preparation and applications.", "Scholarship"),
    ("IELTS Fast Track", "8-week intensive IELTS preparation.", "IELTS"),
    ("SAT Preparation", "SAT timeline from diagnostics to test day.", "SAT"),
    ("ENT Mastery", "ENT preparation roadmap for local universities.", "ENT"),
    ("Portfolio Builder", "Build a strong design / architecture portfolio.", "Portfolio"),
    ("Interview Prep", "Admissions and scholarship interview preparation.", "Interview"),
    ("Safety Applications", "Backup university application plan.", "Backup"),
]

ROADMAP_STEPS = [
    ("Initial assessment & goal setting", 0),
    ("Choose target universities", 7),
    ("Prepare standardized tests", 21),
    ("Draft motivation letter", 35),
    ("Collect recommendation letters", 49),
    ("Finalize and submit applications", 70),
]

NEWS_SPECS = [
    ("Scholarship deadline approaching", "Submit your applications before the end of the month to be considered for merit scholarships.", "deadline", 20, True),
    ("Summer camp registration open", "Early-bird registration for the academic summer camp is now open.", "summer_camp", 45, True),
    ("IELTS speaking workshop", "Join our speaking workshop this Friday with a certified examiner.", "webinar", 5, True),
    ("Hackathon roadmap published", "Check the new hackathon timeline and team registration.", "hackathon", 10, True),
    ("University fair next month", "Meet admissions representatives from 20+ universities abroad.", "university_news", 30, True),
    ("ENT prep intensive", "A full-day ENT practice test and review session is scheduled.", "general", 7, False),
    ("New internship openings", "Several internship opportunities were added this week.", "internship", 14, False),
    ("Olympiad selection results", "Results of the selection round will be posted soon.", "olympiad", 12, False),
    ("Application checklist updated", "The documents checklist has been refreshed for all students.", "general", 3, False),
    ("NU application deadline reminder", "The Nazarbayev University application deadline is near.", "deadline", 8, True),
    ("Common App workshop", "Learn how to fill the Common App step by step.", "webinar", 16, True),
    ("Financial aid info session", "Understand need-based and merit-based financial aid options.", "webinar", 25, True),
]

FAQ_SPECS = [
    ("How do I upload documents?", "Open the Documents section and tap Upload, then choose your file.", "documents"),
    ("How do I book an appointment?", "Pick an available slot in Appointments and confirm the booking.", "appointments"),
    ("How do I reset my password?", "Use the 'Forgot password' link on the login screen.", "auth"),
    ("How are tasks assigned to me?", "Your adviser assigns tasks; you can also create personal tasks.", "tasks"),
    ("How do I update my profile?", "Open Profile, edit the fields, and tap Save.", "profile"),
    ("Where do I see notifications?", "Open the notifications panel from the top bar.", "notifications"),
    ("How do roadmaps work?", "A roadmap is a set of milestone tasks tailored to your goal.", "roadmaps"),
    ("Can I create personal tasks?", "Yes — use the personal task button on the Tasks screen.", "tasks"),
    ("Where do news items appear?", "In the News feed, and optionally in your calendar.", "news"),
    ("How do I contact my adviser?", "Use the Messages section to chat with your adviser.", "messages"),
    ("What is enrollment progress?", "It tracks how far you are in each university's application.", "enrollments"),
    ("How is my GPA used?", "Programs list a minimum GPA; we match you against requirements.", "profile"),
]

DOC_TYPES = ["cv", "transcript", "passport", "motivation_letter", "ielts_certificate",
             "recommendation", "sat_report"]
DOC_CATEGORY = {
    "cv": "personal", "transcript": "education", "passport": "personal",
    "motivation_letter": "education", "ielts_certificate": "education",
    "recommendation": "education", "sat_report": "education",
}
CONSULTATION_TYPES = ["video", "audio", "chat"]


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


async def _get_or_create_user(session, email: str, full_name: str, role: str) -> User:
    existing = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(DEFAULT_PASSWORD),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


# ──────────────────────────────────────────────────────────────────────────
# MinIO helpers
# ──────────────────────────────────────────────────────────────────────────
def _make_seed_pdf(title: str = "Seed Document") -> bytes:
    content = f"BT /F1 14 Tf 50 750 Td ({title}) Tj ET"
    content_bytes = content.encode()
    c_len = len(content_bytes)
    objects: list[bytes] = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    objects.append(
        f"4 0 obj\n<< /Length {c_len} >>\nstream\n".encode()
        + content_bytes
        + b"\nendstream\nendobj\n"
    )
    objects.append(
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    header = b"%PDF-1.4\n"
    body = b""
    offsets: list[int] = []
    pos = len(header)
    for obj in objects:
        offsets.append(pos)
        body += obj
        pos += len(obj)
    xref_pos = len(header) + len(body)
    n = len(objects) + 1
    xref = f"xref\n0 {n}\n0000000000 65535 f \n".encode()
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    trailer = (
        f"trailer\n<< /Size {n} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return header + body + xref + trailer


def _upload_seed_document(student_id: uuid.UUID, doc_type: str) -> tuple[str, int, str]:
    title = doc_type.replace("_", " ").title()
    data = _make_seed_pdf(title)
    key = f"{student_id}/{doc_type}/{uuid.uuid4().hex}.pdf"
    try:
        upload_file(BUCKET_DOCUMENTS, key, io.BytesIO(data), len(data), "application/pdf")
        return key, len(data), "application/pdf"
    except Exception:
        return f"{student_id}/{doc_type}/missing.pdf", len(data), "application/pdf"


def _upload_seed_image(conversation_id: uuid.UUID, sender_id: uuid.UUID) -> tuple[str | None, int, str | None]:
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89,
        0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41, 0x54,
        0x78, 0x9C, 0x62, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,
        0xE5, 0x27, 0xDE, 0xFC, 0x00, 0x00, 0x00, 0x00,
        0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
    ])
    key = f"{conversation_id}/{sender_id}/{uuid.uuid4().hex}.png"
    try:
        upload_file(BUCKET_MESSAGES, key, io.BytesIO(png_data), len(png_data), "image/png")
        return key, len(png_data), "image/png"
    except Exception:
        return None, 0, None


# ──────────────────────────────────────────────────────────────────────────
# Main seed
# ──────────────────────────────────────────────────────────────────────────
async def seed_data() -> None:
    await init_buckets()
    now = _now_utc()
    today = date.today()

    async with AsyncSessionLocal() as session:
        student_total = (
            await session.execute(
                select(func.count()).select_from(User).where(User.role == ROLE_STUDENT)
            )
        ).scalar_one()
        force = os.getenv("SEED_FORCE", "0").strip().lower() in {"1", "true", "yes", "y"}
        if student_total > 0 and not force:
            print(f"Seed skipped: {student_total} students already exist. Set SEED_FORCE=1 to add more.")
            return

        # ── Staff ────────────────────────────────────────────────────────
        admin = await _get_or_create_user(session, ADMIN_EMAIL, "Nobal Admin", ROLE_ADMIN)
        adviser = await _get_or_create_user(
            session, settings.ADVISER_email, "Nobal Adviser", ROLE_ADVISER
        )

        # ── Students + profiles ──────────────────────────────────────────
        students: list[User] = []
        profiles: list[StudentProfile] = []
        for i in range(N_STUDENTS):
            is_female = i % 2 == 0
            first = (FEMALE_NAMES if is_female else MALE_NAMES)[i % 15]
            surname = SURNAMES[i % len(SURNAMES)]
            full_name = f"{first} {surname}"
            student = await _get_or_create_user(
                session, f"student{i + 1}@students.nobal.tech", full_name, ROLE_STUDENT
            )
            students.append(student)

            ielts_passed = i % 3 != 0
            sat_passed = i % 4 == 0
            ent_done = i % 2 == 0
            profiles.append(
                StudentProfile(
                    user_id=student.id,
                    group_type=["D", "D1", "D2", "F", "F1", "F2", "F3", "F4"][i % 8],
                    course_year=2 if i % 2 == 0 else 3,
                    gpa=Decimal("3.0") + Decimal("0.1") * (i % 10),
                    ielts_passed=ielts_passed,
                    ielts_score=Decimal("6.0") + Decimal("0.5") * (i % 4) if ielts_passed else None,
                    ielts_date=today - timedelta(days=30 + i * 3) if ielts_passed else None,
                    sat_passed=sat_passed,
                    sat_score=1200 + (i % 6) * 40 if sat_passed else None,
                    sat_date=today - timedelta(days=60 + i * 2) if sat_passed else None,
                    ent_score=110 + (i % 30) if ent_done else None,
                    kta_score=80 + (i % 20) if i % 3 == 0 else None,
                    target_country=TARGET_COUNTRIES[i % len(TARGET_COUNTRIES)],
                    target_major=MAJORS[i % len(MAJORS)],
                    phone=f"+7707{1000000 + i:07d}",
                    gender="female" if is_female else "male",
                    birth_date=date(2006 - (i % 3), (i % 12) + 1, (i % 27) + 1),
                    school_name=SCHOOLS[i % len(SCHOOLS)],
                    degree_level="bachelor" if i % 5 != 0 else "master",
                    target_countries=f'["{TARGET_COUNTRIES[i % len(TARGET_COUNTRIES)]}", "{TARGET_COUNTRIES[(i + 1) % len(TARGET_COUNTRIES)]}"]',
                    budget_max=10000 + (i % 8) * 5000,
                    notes=f"Seed profile for {full_name}.",
                )
            )
        session.add_all(profiles)

        # ── Universities + programs ──────────────────────────────────────
        universities: list[University] = []
        for idx, (name, country, city, qs, the_r, accept, total, intl, lang) in enumerate(UNIVERSITIES):
            dorm = idx % 3 != 0
            universities.append(
                University(
                    name=name,
                    country=country,
                    city=city,
                    website_url=f"https://example.edu/{idx + 1}",
                    description=f"{name} is located in {city}, {country}. A strong choice for ambitious students.",
                    acceptance_rate=accept,
                    total_students=total,
                    international_pct=intl,
                    qs_ranking=qs,
                    the_ranking=the_r,
                    language_of_instr=lang,
                    is_published=True,
                    last_verified_at=now - timedelta(days=idx),
                    dorm_available=dorm,
                    dorm_cost_per_month=(120 + idx * 10) if dorm else None,
                    dorm_cost_currency="USD" if dorm else None,
                    dorm_guaranteed_for="1st year" if dorm else None,
                    dorm_room_types="2,3-местные" if dorm else None,
                    dining_spots_total=5 + (idx % 6),
                    cafes_count=f"{3 + idx % 3}-{5 + idx % 3}",
                    shops_count=f"{1 + idx % 2}-{3 + idx % 2}",
                    parking_count=200 + idx * 25,
                    has_medical_center=idx % 2 == 0,
                    has_library=True,
                    campus_extra="Modern campus with sports complex and research labs.",
                )
            )
        session.add_all(universities)
        await session.flush()

        programs: list[UniversityProgram] = []
        for uni_idx, university in enumerate(universities):
            n_progs = 2 + (uni_idx % 2)  # 2-3 programs each
            for p in range(n_progs):
                tpl = PROGRAM_TEMPLATES[(uni_idx + p) % len(PROGRAM_TEMPLATES)]
                pname, degree, field, min_gpa, min_ielts, min_sat, tuition, fee, seasons = tpl
                programs.append(
                    UniversityProgram(
                        university_id=university.id,
                        name=pname,
                        degree_level=degree,
                        field=field,
                        min_gpa=min_gpa,
                        min_ielts=min_ielts,
                        min_sat=min_sat,
                        tuition_usd=tuition,
                        scholarship_info="Merit and need-based scholarships available.",
                        application_fee=fee,
                        intake_seasons=seasons,
                        deadline=today + timedelta(days=60 + uni_idx * 5),
                        campus_life="Active student clubs, sports, and career services.",
                        requirements_text="Transcript, motivation letter, recommendations, and language certificate.",
                        apply_url=f"https://example.edu/{uni_idx + 1}/apply",
                        is_active=True,
                    )
                )
        session.add_all(programs)
        await session.flush()

        # ── Enrollments (1-3 distinct universities per student) ───────────
        enroll_statuses = ["selected", "applying", "submitted", "accepted", "rejected"]
        enrollments: list[Enrollment] = []
        for i, student in enumerate(students):
            n_enr = 1 + (i % 3)
            chosen = random.sample(universities, k=n_enr)
            for j, uni in enumerate(chosen):
                status = enroll_statuses[(i + j) % len(enroll_statuses)]
                progress = {"selected": 10, "applying": 40, "submitted": 70,
                            "accepted": 100, "rejected": 100}[status]
                enrollments.append(
                    Enrollment(
                        student_id=student.id,
                        university_id=uni.id,
                        status=status,
                        progress=progress,
                    )
                )
        session.add_all(enrollments)

        # ── Roadmaps + template tasks ────────────────────────────────────
        roadmaps: list[Roadmap] = []
        for r_idx, (title, desc, target) in enumerate(ROADMAP_SPECS):
            roadmaps.append(
                Roadmap(
                    title=title,
                    description=desc,
                    target_type=target,
                    is_public=True,
                    university_id=universities[r_idx % len(universities)].id if r_idx % 2 == 0 else None,
                    created_by=adviser.id,
                )
            )
        session.add_all(roadmaps)
        await session.flush()

        template_tasks: list[RoadmapTemplateTask] = []
        for roadmap in roadmaps:
            for step_idx, (step_title, offset) in enumerate(ROADMAP_STEPS, start=1):
                template_tasks.append(
                    RoadmapTemplateTask(
                        roadmap_id=roadmap.id,
                        title=step_title,
                        description=f"{step_title} for {roadmap.title}.",
                        order_index=step_idx,
                        days_offset=offset,
                    )
                )
        session.add_all(template_tasks)

        # ── Student roadmaps (1-2 per student) ───────────────────────────
        student_roadmaps: list[StudentRoadmap] = []
        sr_by_student: dict[uuid.UUID, StudentRoadmap] = {}
        for i, student in enumerate(students):
            primary = roadmaps[i % len(roadmaps)]
            sr = StudentRoadmap(
                student_id=student.id,
                roadmap_id=primary.id,
                assigned_by=adviser.id,
                title=primary.title,
                is_active=True,
            )
            student_roadmaps.append(sr)
            sr_by_student[student.id] = sr
            if i % 3 == 0:
                secondary = roadmaps[(i + 3) % len(roadmaps)]
                student_roadmaps.append(
                    StudentRoadmap(
                        student_id=student.id,
                        roadmap_id=secondary.id,
                        assigned_by=adviser.id,
                        title=secondary.title,
                        is_active=False,
                    )
                )
        session.add_all(student_roadmaps)
        await session.flush()

        # ── Tasks (+ history) ────────────────────────────────────────────
        tasks: list[Task] = []
        task_history: list[TaskHistory] = []
        for i, student in enumerate(students):
            sr = sr_by_student[student.id]
            # adviser task — in progress
            t1 = Task(
                student_id=student.id, created_by=adviser.id,
                title=f"IELTS mock test #{i + 1}",
                description="Complete a full mock test and review mistakes.",
                status=TASK_STATUS_IN_PROGRESS, priority="high",
                task_type="assignment",
                deadline=now + timedelta(days=10 + (i % 14)),
                reminder_minutes=60,
                is_adviser_task=True,
                student_roadmap_id=sr.id,
            )
            # personal task — todo
            t2 = Task(
                student_id=student.id, created_by=student.id,
                title=f"Weekly self-study plan #{i + 1}",
                description="Plan and track weekly self-study sessions.",
                status=TASK_STATUS_TODO, priority="medium",
                task_type="assignment",
                deadline=now + timedelta(days=5 + (i % 7)),
                is_adviser_task=False,
            )
            # adviser task — done or overdue
            done = i % 2 == 0
            t3 = Task(
                student_id=student.id, created_by=adviser.id,
                title=f"Upload transcript #{i + 1}",
                description="Upload your latest official transcript.",
                status=TASK_STATUS_DONE if done else TASK_STATUS_OVERDUE,
                priority="low", task_type="assignment",
                deadline=now - timedelta(days=2 + (i % 5)),
                completed_at=now - timedelta(days=1 + (i % 4)) if done else None,
                is_adviser_task=True,
            )
            # meeting-type deadline task with time/location
            t4 = Task(
                student_id=student.id, created_by=adviser.id,
                title=f"Consultation prep #{i + 1}",
                description="Prepare questions for the next consultation.",
                status=TASK_STATUS_TODO, priority="medium",
                task_type="deadline",
                deadline=now + timedelta(days=3 + (i % 6)),
                time_from=time(14, 0), time_to=time(15, 0),
                location="Office 204" if i % 2 == 0 else "Online",
                reminder_minutes=30,
                is_adviser_task=True,
            )
            tasks.extend([t1, t2, t3, t4])
        session.add_all(tasks)
        await session.flush()

        for t in tasks:
            task_history.append(
                TaskHistory(
                    task_id=t.id, changed_by=t.created_by,
                    event_type="created", old_value=None, new_value=t.status,
                )
            )
            if t.status in (TASK_STATUS_DONE, TASK_STATUS_IN_PROGRESS):
                task_history.append(
                    TaskHistory(
                        task_id=t.id, changed_by=t.created_by,
                        event_type="status_changed",
                        old_value=TASK_STATUS_TODO, new_value=t.status,
                    )
                )
        session.add_all(task_history)

        # ── Availability slots + appointments ────────────────────────────
        slots: list[AvailabilitySlot] = []
        slots_total = N_STUDENTS + 10  # extra free slots
        for i in range(slots_total):
            slot_start = now + timedelta(days=(i // 3) + 1, hours=(i % 3) * 2)
            slots.append(
                AvailabilitySlot(
                    adviser_id=adviser.id,
                    start_time=slot_start,
                    end_time=slot_start + timedelta(minutes=45),
                    duration_min=45,
                    is_available=i >= N_STUDENTS,  # last 10 stay free
                )
            )
        session.add_all(slots)
        await session.flush()

        status_cycle = [APPOINTMENT_STATUS_CONFIRMED, APPOINTMENT_STATUS_PENDING,
                        APPOINTMENT_STATUS_COMPLETED]
        appointments: list[Appointment] = []
        for i, student in enumerate(students):
            slot = slots[i]
            slot.is_available = False
            appointments.append(
                Appointment(
                    slot_id=slot.id,
                    student_id=student.id,
                    adviser_id=adviser.id,
                    status=status_cycle[i % len(status_cycle)],
                    consultation_type=CONSULTATION_TYPES[i % len(CONSULTATION_TYPES)],
                    notes=f"Discuss roadmap and deadlines for {student.full_name}.",
                )
            )
        session.add_all(appointments)
        await session.flush()

        # ── Conversations + messages (1 per student) ─────────────────────
        conversations: list[Conversation] = []
        for i, student in enumerate(students):
            conversations.append(
                Conversation(
                    student_id=student.id,
                    adviser_id=adviser.id,
                    last_message_at=now - timedelta(minutes=i),
                )
            )
        session.add_all(conversations)
        await session.flush()

        messages: list[Message] = []
        for i, (student, convo) in enumerate(zip(students, conversations, strict=True)):
            m1 = Message(
                conversation_id=convo.id, sender_id=student.id,
                body=f"Hello! I have a question about my roadmap (#{i + 1}).",
                is_read=True, read_at=now - timedelta(hours=2, minutes=i),
                created_at=now - timedelta(hours=2, minutes=i),
            )
            m2 = Message(
                conversation_id=convo.id, sender_id=adviser.id,
                body="Sure! Let's go over it in our next consultation.",
                is_read=(i % 2 == 0),
                read_at=(now - timedelta(hours=1)) if i % 2 == 0 else None,
                created_at=now - timedelta(hours=1, minutes=i),
            )
            m3 = Message(
                conversation_id=convo.id, sender_id=student.id,
                body="Thank you, see you then!",
                is_read=False, created_at=now - timedelta(minutes=i + 1),
            )
            # attach an image to every 5th adviser message
            if i % 5 == 0:
                key, size, ctype = _upload_seed_image(convo.id, adviser.id)
                if key:
                    m2.image_object_key = key
                    m2.image_content_type = ctype
                    m2.image_size = size
            convo.last_message_at = m3.created_at
            messages.extend([m1, m2, m3])
        session.add_all(messages)

        # ── Notifications ────────────────────────────────────────────────
        notifications: list[Notification] = []
        for i, student in enumerate(students):
            notifications.append(
                Notification(
                    user_id=student.id, title="New task assigned",
                    body=f"IELTS mock test #{i + 1} was assigned to you.",
                    type="new_task", source_type="task",
                    is_read=(i % 3 == 0),
                )
            )
            notifications.append(
                Notification(
                    user_id=student.id, title="New message",
                    body="Your adviser replied to your question.",
                    type="new_message", source_type="message",
                )
            )
            if i % 4 == 0:
                notifications.append(
                    Notification(
                        user_id=student.id, title="Appointment confirmed",
                        body="Your consultation has been confirmed.",
                        type="appointment_confirmed", source_type="appointment",
                    )
                )
        notifications.append(
            Notification(
                user_id=adviser.id, title="New bookings",
                body="Several students booked consultation slots.",
                type="appointment_confirmed", source_type="appointment",
            )
        )
        session.add_all(notifications)

        # ── Calendar events ──────────────────────────────────────────────
        events: list[CalendarEvent] = []
        for i, student in enumerate(students):
            slot = slots[i]
            events.append(
                CalendarEvent(
                    user_id=student.id, title="Consultation with adviser",
                    description="Discuss application roadmap.",
                    event_type="appointment",
                    start_time=slot.start_time, end_time=slot.end_time,
                    color="#3B82F6",
                    source_id=appointments[i].id, source_type="appointment",
                )
            )
            t1 = tasks[i * 4]
            events.append(
                CalendarEvent(
                    user_id=student.id, title=f"Deadline: {t1.title}",
                    description="Task deadline.",
                    event_type="task_deadline",
                    start_time=t1.deadline, end_time=t1.deadline + timedelta(hours=1),
                    color="#EF4444",
                    source_id=t1.id, source_type="task",
                )
            )
        session.add_all(events)

        # ── FAQ ──────────────────────────────────────────────────────────
        faqs = [
            FAQ(question=q, answer=a, category=c, order_index=idx, is_active=True,
                created_by=adviser.id)
            for idx, (q, a, c) in enumerate(FAQ_SPECS, start=1)
        ]
        session.add_all(faqs)

        # ── News ─────────────────────────────────────────────────────────
        news_items = [
            News(
                author_id=adviser.id, title=title, body=body, category=cat,
                event_date=today + timedelta(days=offset),
                allow_calendar=allow_cal, is_published=True, views_count=idx * 17,
            )
            for idx, (title, body, cat, offset, allow_cal) in enumerate(NEWS_SPECS, start=1)
        ]
        session.add_all(news_items)
        await session.flush()

        # news → calendar events for students who opted-in style
        for n in news_items:
            if n.allow_calendar:
                ev_start = datetime.combine(n.event_date, time(9, 0), tzinfo=timezone.utc)
                events_extra = [
                    CalendarEvent(
                        user_id=students[k].id, title=n.title,
                        description=n.body[:200], event_type="news_event",
                        start_time=ev_start, end_time=ev_start + timedelta(hours=1),
                        color="#10B981", source_id=n.id, source_type="news",
                    )
                    for k in range(min(5, len(students)))
                ]
                session.add_all(events_extra)

        # ── Alumni stories ───────────────────────────────────────────────
        alumni: list[AlumniStory] = []
        for idx, uni in enumerate(universities):
            uni_programs = [p for p in programs if p.university_id == uni.id]
            prog_name = uni_programs[0].name if uni_programs else "General Studies"
            alumni.append(
                AlumniStory(
                    author_id=adviser.id,
                    student_name=f"{FEMALE_NAMES[idx % 15] if idx % 2 else MALE_NAMES[idx % 15]} {SURNAMES[idx % len(SURNAMES)]}",
                    graduation_year=2024 - (idx % 4),
                    university_id=uni.id,
                    university_name=uni.name,
                    program_name=prog_name,
                    scholarship_type="Full" if idx % 2 == 0 else "Partial",
                    story_text="Started early, followed the roadmap, and stayed consistent throughout the application season.",
                    gpa_at_time=Decimal("3.5") + Decimal("0.1") * (idx % 4),
                    ielts_at_time=Decimal("6.5") + Decimal("0.5") * (idx % 2),
                    sat_at_time=1350 + (idx * 10),
                    is_published=True,
                )
            )
        session.add_all(alumni)

        # ── Documents (2-3 distinct doc_types per student) ───────────────
        documents: list[StudentDocument] = []
        doc_statuses = ["active", "pending", "expired", "needs_update"]
        for i, student in enumerate(students):
            n_docs = 2 + (i % 2)
            for d in range(n_docs):
                doc_type = DOC_TYPES[(i + d) % len(DOC_TYPES)]
                key, size, ctype = _upload_seed_document(student.id, doc_type)
                status = doc_statuses[(i + d) % len(doc_statuses)]
                documents.append(
                    StudentDocument(
                        student_id=student.id,
                        doc_type=doc_type,
                        category=DOC_CATEGORY.get(doc_type, "other"),
                        status=status,
                        expires_at=(now + timedelta(days=365)) if doc_type == "ielts_certificate" else None,
                        object_key=key,
                        content_type=ctype,
                        size=size,
                        notes=f"Seed {doc_type} for {student.full_name}.",
                    )
                )
        session.add_all(documents)

        # ── Refresh tokens / sessions (with device metadata) ─────────────
        devices = [("iPhone 15", "Mobile App"), ("Chrome / Windows", "Web"),
                   ("Samsung Galaxy", "Mobile App"), ("Safari / macOS", "Web")]
        refresh_tokens: list[RefreshToken] = []
        for idx, user in enumerate([admin, adviser, *students]):
            dev, _ = devices[idx % len(devices)]
            refresh_tokens.append(
                RefreshToken(
                    user_id=user.id,
                    token_hash=hash_password(uuid.uuid4().hex),
                    expires_at=now + timedelta(days=30),
                    device_name=dev,
                    ip_address=f"192.168.1.{(idx % 250) + 1}",
                    last_used_at=now - timedelta(hours=idx % 48),
                )
            )
        session.add_all(refresh_tokens)

        await session.commit()

        print("✓ Seed completed.")
        print(f"  Admin:      {admin.email}")
        print(f"  Adviser:    {adviser.email}")
        print(f"  Students:   {len(students)}  (password: {DEFAULT_PASSWORD})")
        print(f"  Universities:{len(universities)}  Programs: {len(programs)}")
        print(f"  Enrollments:{len(enrollments)}  Roadmaps: {len(roadmaps)}")
        print(f"  Tasks:      {len(tasks)}  History: {len(task_history)}")
        print(f"  Appointments:{len(appointments)}  Slots: {len(slots)}")
        print(f"  Messages:   {len(messages)}  Notifications: {len(notifications)}")
        print(f"  Documents:  {len(documents)}  Alumni: {len(alumni)}")
        print(f"  News:       {len(news_items)}  FAQ: {len(faqs)}")


if __name__ == "__main__":
    asyncio.run(seed_data())
