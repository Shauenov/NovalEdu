import asyncio
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func

from app.config import settings
from app.core.constants import (
    APPOINTMENT_STATUS_CONFIRMED,
    BUCKET_DOCUMENTS,
    ROLE_ADMIN,
    ROLE_CONDUCTOR,
    ROLE_STUDENT,
    TASK_STATUS_DONE,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_TODO,
)
from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.modules.alumni.models import AlumniStory
from app.modules.appointments.models import Appointment, AvailabilitySlot
from app.modules.auth.models import RefreshToken
from app.modules.calendar.models import CalendarEvent
from app.modules.documents.models import StudentDocument
from app.modules.faq.models import FAQ
from app.modules.messages.models import Conversation, Message
from app.modules.news.models import News
from app.modules.notifications.models import Notification
from app.modules.profile.models import StudentProfile
from app.modules.roadmaps.models import Roadmap, RoadmapTemplateTask, StudentRoadmap
from app.modules.tasks.models import Task
from app.modules.universities.models import University, UniversityProgram
from app.modules.users.models import User
from app.storage.minio_client import init_buckets, upload_file


DEFAULT_PASSWORD = "Password123!"


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


async def _create_user(session, email: str, full_name: str, role: str) -> User:
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


def _upload_seed_document(student_id: uuid.UUID, doc_type: str) -> tuple[str, int, str]:
    data = b"%PDF-1.4\n% Seed doc\n"
    key = f"{student_id}/{doc_type}/{uuid.uuid4().hex}.pdf"
    try:
        upload_file(BUCKET_DOCUMENTS, key, io.BytesIO(data), len(data), "application/pdf")
        return key, len(data), "application/pdf"
    except Exception:
        return f"{student_id}/{doc_type}/missing.pdf", 0, "application/pdf"


async def seed_data() -> None:
    await init_buckets()

    async with AsyncSessionLocal() as session:
        total_users = (
            await session.execute(select(func.count()).select_from(User))
        ).scalar_one()
        if total_users > 0:
            print("Seed skipped: data already exists.")
            return

        admin = await _create_user(session, "admin@nobal.local", "Admin User", ROLE_ADMIN)
        conductor = await _create_user(
            session,
            settings.conductor_email,
            "Conductor",
            ROLE_CONDUCTOR,
        )

        students: list[User] = []
        for idx in range(1, 4):
            student = await _create_user(
                session,
                f"student{idx}@nobal.local",
                f"Student {idx}",
                ROLE_STUDENT,
            )
            students.append(student)

        # Student profiles
        profiles = [
            StudentProfile(
                user_id=students[0].id,
                group_type="D",
                course_year=2,
                gpa=Decimal("3.6"),
                ielts_passed=True,
                ielts_score=Decimal("6.5"),
            ),
            StudentProfile(
                user_id=students[1].id,
                group_type="F",
                course_year=3,
                gpa=Decimal("3.2"),
                ielts_passed=False,
            ),
            StudentProfile(
                user_id=students[2].id,
                group_type="D",
                course_year=2,
                gpa=Decimal("3.9"),
                ielts_passed=True,
                ielts_score=Decimal("7.0"),
            ),
        ]
        session.add_all(profiles)

        # Universities and programs
        uni1 = University(
            name="Nazarbayev University",
            country="Kazakhstan",
            city="Astana",
            qs_ranking=219,
            language_of_instr="English",
            is_published=True,
            last_verified_at=_now_utc(),
        )
        uni2 = University(
            name="KIMEP University",
            country="Kazakhstan",
            city="Almaty",
            qs_ranking=651,
            language_of_instr="English",
            is_published=True,
            last_verified_at=_now_utc(),
        )
        session.add_all([uni1, uni2])
        await session.flush()

        programs = [
            UniversityProgram(
                university_id=uni1.id,
                name="Computer Science",
                degree_level="bachelor",
                field="CS",
                min_gpa=Decimal("3.2"),
                min_ielts=Decimal("6.5"),
                tuition_usd=0,
                intake_seasons="Fall",
            ),
            UniversityProgram(
                university_id=uni1.id,
                name="Electrical Engineering",
                degree_level="bachelor",
                field="Engineering",
                min_gpa=Decimal("3.0"),
                min_ielts=Decimal("6.0"),
                tuition_usd=0,
                intake_seasons="Fall",
            ),
            UniversityProgram(
                university_id=uni2.id,
                name="Business Administration",
                degree_level="bachelor",
                field="Business",
                min_gpa=Decimal("2.8"),
                min_ielts=Decimal("6.0"),
                tuition_usd=12000,
                intake_seasons="Fall, Spring",
            ),
        ]
        session.add_all(programs)

        # News
        news_items = [
            News(
                author_id=conductor.id,
                title="Scholarship deadline approaching",
                body="Submit your applications before the deadline.",
                category="deadline",
                event_date=date.today() + timedelta(days=20),
                is_published=True,
            ),
            News(
                author_id=conductor.id,
                title="Summer camp registration",
                body="Early registration is open now.",
                category="summer_camp",
                event_date=date.today() + timedelta(days=45),
                is_published=True,
            ),
        ]
        session.add_all(news_items)

        # Roadmap and template tasks
        roadmap = Roadmap(
            title="NU Admission Roadmap",
            description="Roadmap for NU application",
            target_type="NU",
            is_public=True,
            created_by=conductor.id,
        )
        session.add(roadmap)
        await session.flush()

        template_tasks = [
            RoadmapTemplateTask(
                roadmap_id=roadmap.id,
                title="Prepare CV",
                description="Draft a CV for review.",
                order_index=1,
                days_offset=7,
            ),
            RoadmapTemplateTask(
                roadmap_id=roadmap.id,
                title="Motivation letter",
                description="Draft motivation letter.",
                order_index=2,
                days_offset=14,
            ),
        ]
        session.add_all(template_tasks)

        # Student roadmaps and tasks
        student_roadmaps: list[StudentRoadmap] = []
        for student in students:
            sr = StudentRoadmap(
                student_id=student.id,
                roadmap_id=roadmap.id,
                assigned_by=conductor.id,
                title=roadmap.title,
                is_active=True,
            )
            student_roadmaps.append(sr)
        session.add_all(student_roadmaps)
        await session.flush()

        tasks: list[Task] = []
        for idx, student in enumerate(students):
            sr = student_roadmaps[idx]
            tasks.append(
                Task(
                    student_id=student.id,
                    created_by=conductor.id,
                    title="Complete IELTS practice",
                    description="Mock test and review errors",
                    status=TASK_STATUS_IN_PROGRESS,
                    priority="high",
                    deadline=_now_utc() + timedelta(days=10),
                    is_conductor_task=True,
                    student_roadmap_id=sr.id,
                )
            )
            tasks.append(
                Task(
                    student_id=student.id,
                    created_by=student.id,
                    title="Personal study plan",
                    description="Plan weekly self-study",
                    status=TASK_STATUS_TODO,
                    priority="medium",
                    deadline=_now_utc() + timedelta(days=5),
                    is_conductor_task=False,
                )
            )
            tasks.append(
                Task(
                    student_id=student.id,
                    created_by=conductor.id,
                    title="Submit transcript",
                    description="Upload latest transcript",
                    status=TASK_STATUS_DONE,
                    priority="low",
                    deadline=_now_utc() - timedelta(days=2),
                    completed_at=_now_utc() - timedelta(days=1),
                    is_conductor_task=True,
                )
            )
        session.add_all(tasks)

        # Availability slots and appointment
        slot_start = _now_utc() + timedelta(days=1, hours=2)
        slot1 = AvailabilitySlot(
            conductor_id=conductor.id,
            start_time=slot_start,
            end_time=slot_start + timedelta(minutes=45),
            duration_min=45,
            is_available=False,
        )
        slot2 = AvailabilitySlot(
            conductor_id=conductor.id,
            start_time=slot_start + timedelta(hours=2),
            end_time=slot_start + timedelta(hours=2, minutes=45),
            duration_min=45,
            is_available=True,
        )
        session.add_all([slot1, slot2])
        await session.flush()

        appt = Appointment(
            slot_id=slot1.id,
            student_id=students[0].id,
            conductor_id=conductor.id,
            status=APPOINTMENT_STATUS_CONFIRMED,
            notes="Discuss IELTS strategy",
        )
        session.add(appt)

        # Conversations and messages
        for student in students:
            convo = Conversation(
                student_id=student.id,
                conductor_id=conductor.id,
                last_message_at=_now_utc(),
            )
            session.add(convo)
            await session.flush()

            msg1 = Message(
                conversation_id=convo.id,
                sender_id=student.id,
                body="Hello! I have a question about my roadmap.",
                is_read=True,
                read_at=_now_utc() - timedelta(hours=1),
                created_at=_now_utc() - timedelta(hours=1),
            )
            msg2 = Message(
                conversation_id=convo.id,
                sender_id=conductor.id,
                body="Sure, let's review it in our next meeting.",
                is_read=False,
                created_at=_now_utc(),
            )
            session.add_all([msg1, msg2])
            convo.last_message_at = msg2.created_at

        # Notifications
        notifications = [
            Notification(
                user_id=students[0].id,
                title="New task assigned",
                body="Complete IELTS practice",
                type="new_task",
                source_type="task",
            ),
            Notification(
                user_id=conductor.id,
                title="Appointment booked",
                body="Student booked a slot",
                type="appointment_confirmed",
                source_type="appointment",
            ),
        ]
        session.add_all(notifications)

        # Calendar events
        events = [
            CalendarEvent(
                user_id=students[0].id,
                title="Appointment with Conductor",
                description="Discuss IELTS strategy",
                event_type="appointment",
                start_time=slot1.start_time,
                end_time=slot1.end_time,
                source_id=appt.id,
                source_type="appointment",
            ),
            CalendarEvent(
                user_id=students[0].id,
                title="IELTS practice deadline",
                description="Complete IELTS practice task",
                event_type="task_deadline",
                start_time=_now_utc() + timedelta(days=10),
                end_time=_now_utc() + timedelta(days=10, hours=1),
                source_type="task",
            ),
            CalendarEvent(
                user_id=students[0].id,
                title="Scholarship deadline",
                description="Submit applications",
                event_type="news_event",
                start_time=_now_utc() + timedelta(days=20),
                end_time=_now_utc() + timedelta(days=20, hours=1),
                source_type="news",
            ),
        ]
        session.add_all(events)

        # FAQ
        faqs = [
            FAQ(
                question="How to upload documents?",
                answer="Go to Documents and upload your file.",
                category="documents",
                order_index=1,
                created_by=conductor.id,
            ),
            FAQ(
                question="How to book an appointment?",
                answer="Choose an available slot and confirm.",
                category="appointments",
                order_index=2,
                created_by=conductor.id,
            ),
        ]
        session.add_all(faqs)

        # Alumni
        alumni = AlumniStory(
            author_id=conductor.id,
            student_name="Aruzhan T.",
            graduation_year=2024,
            university_id=uni1.id,
            university_name=uni1.name,
            program_name="Computer Science",
            scholarship_type="Full",
            story_text="Prepared early and followed the roadmap.",
            gpa_at_time=Decimal("3.8"),
            ielts_at_time=Decimal("7.0"),
            sat_at_time=1450,
            is_published=True,
        )
        session.add(alumni)

        # Documents
        for student in students:
            key, size, content_type = _upload_seed_document(student.id, "cv")
            doc = StudentDocument(
                student_id=student.id,
                doc_type="cv",
                object_key=key,
                content_type=content_type,
                size=size,
            )
            session.add(doc)

        # Refresh token example
        refresh = RefreshToken(
            user_id=admin.id,
            token_hash=hash_password(uuid.uuid4().hex),
            expires_at=_now_utc() + timedelta(days=30),
        )
        session.add(refresh)

        await session.commit()

        print("Seed data created. Default password:", DEFAULT_PASSWORD)


if __name__ == "__main__":
    asyncio.run(seed_data())
