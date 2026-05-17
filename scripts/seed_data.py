import asyncio
import io
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func

from app.config import settings
from app.core.constants import (
    APPOINTMENT_STATUS_COMPLETED,
    APPOINTMENT_STATUS_CONFIRMED,
    APPOINTMENT_STATUS_PENDING,
    BUCKET_DOCUMENTS,
    BUCKET_MESSAGES,
    ROLE_ADMIN,
    ROLE_CONDUCTOR,
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
EXTRA_COUNT = 10


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


def _upload_seed_image(conversation_id: uuid.UUID, sender_id: uuid.UUID) -> tuple[str | None, int, str | None]:
    """Create and upload a simple test image (PNG)."""
    # Minimal 1x1 PNG image (transparent)
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D,  # IHDR chunk size
        0x49, 0x48, 0x44, 0x52,  # IHDR
        0x00, 0x00, 0x00, 0x01,  # width: 1
        0x00, 0x00, 0x00, 0x01,  # height: 1
        0x08, 0x06,  # bit depth: 8, color type: 6 (RGBA)
        0x00, 0x00, 0x00,  # compression, filter, interlace
        0x1F, 0x15, 0xC4, 0x89,  # CRC
        0x00, 0x00, 0x00, 0x0A,  # IDAT chunk size
        0x49, 0x44, 0x41, 0x54,  # IDAT
        0x78, 0x9C, 0x62, 0x00, 0x00, 0x00, 0x02, 0x00, 0x01,
        0xE5, 0x27, 0xDE, 0xFC,  # CRC
        0x00, 0x00, 0x00, 0x00,  # IEND chunk size
        0x49, 0x45, 0x4E, 0x44,  # IEND
        0xAE, 0x42, 0x60, 0x82,  # CRC
    ])
    key = f"{conversation_id}/{sender_id}/{uuid.uuid4().hex}.png"
    try:
        upload_file(BUCKET_MESSAGES, key, io.BytesIO(png_data), len(png_data), "image/png")
        print(f"✓ Uploaded image: {key}")
        return key, len(png_data), "image/png"
    except Exception as e:
        print(f"✗ Failed to upload image: {e}")
        return None, 0, None


async def seed_data() -> None:
    await init_buckets()

    async with AsyncSessionLocal() as session:
        total_users = (
            await session.execute(select(func.count()).select_from(User))
        ).scalar_one()
        if total_users > 0:
            append_only = os.getenv("SEED_APPEND_ONLY", "1").strip().lower() in {"1", "true", "yes", "y"}
            if not append_only:
                print("Seed skipped: data already exists.")
                return

            now = _now_utc()
            status_cycle = [
                APPOINTMENT_STATUS_CONFIRMED,
                APPOINTMENT_STATUS_PENDING,
                APPOINTMENT_STATUS_COMPLETED,
            ]

            admin = (
                await session.execute(select(User).where(User.email == "admin@nobal.local"))
            ).scalar_one_or_none()
            if admin is None:
                admin = await _create_user(session, "admin@nobal.local", "Admin User", ROLE_ADMIN)

            conductor = (
                await session.execute(select(User).where(User.email == settings.conductor_email))
            ).scalar_one_or_none()
            if conductor is None:
                conductor = (
                    await session.execute(select(User).where(User.role == ROLE_CONDUCTOR).limit(1))
                ).scalar_one_or_none()
            if conductor is None:
                conductor = await _create_user(session, settings.conductor_email, "Conductor", ROLE_CONDUCTOR)

            student_count = (
                await session.execute(select(func.count()).select_from(User).where(User.role == ROLE_STUDENT))
            ).scalar_one()
            university_count = (
                await session.execute(select(func.count()).select_from(University))
            ).scalar_one()
            news_count = (
                await session.execute(select(func.count()).select_from(News))
            ).scalar_one()
            roadmap_count = (
                await session.execute(select(func.count()).select_from(Roadmap))
            ).scalar_one()
            faq_order_max = (
                await session.execute(select(func.max(FAQ.order_index)).select_from(FAQ))
            ).scalar_one()
            faq_order_start = faq_order_max or 0

            students: list[User] = []
            for idx in range(EXTRA_COUNT):
                seq = student_count + idx + 1
                student = await _create_user(
                    session,
                    f"student{seq}@nobal.local",
                    f"Extra {seq} Student",
                    ROLE_STUDENT,
                )
                students.append(student)

            profiles = []
            for idx, student in enumerate(students):
                seq = student_count + idx + 1
                ielts_passed = seq % 2 == 0
                sat_passed = seq % 3 == 0
                profiles.append(
                    StudentProfile(
                        user_id=student.id,
                        group_type="D" if seq % 2 == 0 else "F",
                        course_year=2 if seq % 2 == 0 else 3,
                        gpa=Decimal("3.0") + (Decimal("0.1") * (seq % 6)),
                        ielts_passed=ielts_passed,
                        ielts_score=Decimal("6.0") + (Decimal("0.1") * (seq % 5)) if ielts_passed else None,
                        sat_passed=sat_passed,
                        sat_score=1200 + (seq % 6) * 35 if sat_passed else None,
                        target_country="USA" if seq % 2 == 0 else "Canada",
                        target_major="Engineering" if seq % 2 == 0 else "Business",
                        notes=f"Append seed profile for {student.full_name}",
                    )
                )
            session.add_all(profiles)

            universities: list[University] = []
            for idx in range(EXTRA_COUNT):
                seq = university_count + idx + 1
                universities.append(
                    University(
                        name=f"Append University {seq}",
                        country="Kazakhstan",
                        city=f"Append City {seq}",
                        qs_ranking=800 + seq,
                        language_of_instr="English",
                        website_url=f"https://example.com/append-universities/{seq}",
                        description=f"Append seed university profile {seq}.",
                        is_published=True,
                        last_verified_at=now - timedelta(days=idx),
                    )
                )
            session.add_all(universities)
            await session.flush()

            programs: list[UniversityProgram] = []
            for idx, university in enumerate(universities):
                seq = university_count + idx + 1
                programs.append(
                    UniversityProgram(
                        university_id=university.id,
                        name=f"Append Program {seq}",
                        degree_level="bachelor",
                        field="General",
                        min_gpa=Decimal("2.8"),
                        min_ielts=Decimal("5.5"),
                        tuition_usd=9000 + (seq * 100),
                        intake_seasons="Fall",
                        scholarship_info="Merit scholarship available",
                        application_fee=50,
                        requirements_text="Transcript and motivation letter.",
                    )
                )
            session.add_all(programs)

            news_items: list[News] = []
            for idx in range(EXTRA_COUNT):
                seq = news_count + idx + 1
                news_items.append(
                    News(
                        author_id=conductor.id,
                        title=f"Append news {seq}",
                        body="Additional announcement for seeded append mode.",
                        category="announcement",
                        event_date=date.today() + timedelta(days=40 + idx),
                        is_published=True,
                        views_count=seq * 11,
                    )
                )
            session.add_all(news_items)
            await session.flush()

            roadmaps: list[Roadmap] = []
            for idx in range(EXTRA_COUNT):
                seq = roadmap_count + idx + 1
                roadmaps.append(
                    Roadmap(
                        title=f"Append Roadmap {seq}",
                        description="Additional roadmap for append seed.",
                        target_type=f"Append_{seq}",
                        is_public=True,
                        created_by=conductor.id,
                    )
                )
            session.add_all(roadmaps)
            await session.flush()

            roadmap_template_tasks: list[RoadmapTemplateTask] = []
            for idx, roadmap in enumerate(roadmaps, start=1):
                roadmap_template_tasks.append(
                    RoadmapTemplateTask(
                        roadmap_id=roadmap.id,
                        title=f"Append step {idx}A",
                        description="Append roadmap first milestone.",
                        order_index=1,
                        days_offset=7,
                    )
                )
                roadmap_template_tasks.append(
                    RoadmapTemplateTask(
                        roadmap_id=roadmap.id,
                        title=f"Append step {idx}B",
                        description="Append roadmap second milestone.",
                        order_index=2,
                        days_offset=14,
                    )
                )
            session.add_all(roadmap_template_tasks)

            student_roadmaps: list[StudentRoadmap] = []
            for idx, student in enumerate(students):
                student_roadmaps.append(
                    StudentRoadmap(
                        student_id=student.id,
                        roadmap_id=roadmaps[idx].id,
                        assigned_by=conductor.id,
                        title=roadmaps[idx].title,
                        is_active=True,
                    )
                )
            session.add_all(student_roadmaps)
            await session.flush()

            tasks: list[Task] = []
            for idx, student in enumerate(students):
                student_roadmap = student_roadmaps[idx]
                tasks.append(
                    Task(
                        student_id=student.id,
                        created_by=conductor.id,
                        title=f"Append IELTS task #{idx + 1}",
                        description="Mock test and review errors",
                        status=TASK_STATUS_IN_PROGRESS,
                        priority="high",
                        deadline=now + timedelta(days=12 + idx),
                        is_conductor_task=True,
                        student_roadmap_id=student_roadmap.id,
                    )
                )
                tasks.append(
                    Task(
                        student_id=student.id,
                        created_by=student.id,
                        title=f"Append personal plan #{idx + 1}",
                        description="Plan weekly self-study",
                        status=TASK_STATUS_TODO,
                        priority="medium",
                        deadline=now + timedelta(days=6 + idx),
                        is_conductor_task=False,
                    )
                )
                tasks.append(
                    Task(
                        student_id=student.id,
                        created_by=conductor.id,
                        title=f"Append transcript task #{idx + 1}",
                        description="Upload latest transcript",
                        status=TASK_STATUS_DONE if idx % 2 == 0 else TASK_STATUS_OVERDUE,
                        priority="low",
                        deadline=now - timedelta(days=3 + idx),
                        completed_at=now - timedelta(days=2 + idx) if idx % 2 == 0 else None,
                        is_conductor_task=True,
                    )
                )
            session.add_all(tasks)
            await session.flush()

            slots: list[AvailabilitySlot] = []
            for idx in range(len(students)):
                slot_start = now + timedelta(days=idx + 1)
                slots.append(
                    AvailabilitySlot(
                        conductor_id=conductor.id,
                        start_time=slot_start,
                        end_time=slot_start + timedelta(minutes=45),
                        duration_min=45,
                        is_available=False,
                    )
                )
            session.add_all(slots)
            await session.flush()

            appointments: list[Appointment] = []
            for idx, student in enumerate(students):
                appointments.append(
                    Appointment(
                        slot_id=slots[idx].id,
                        student_id=student.id,
                        conductor_id=conductor.id,
                        status=status_cycle[idx % len(status_cycle)],
                        notes=f"Append appointment for student {idx + 1}",
                    )
                )
            session.add_all(appointments)
            await session.flush()

            conversations: list[Conversation] = []
            for idx, student in enumerate(students):
                conversation = Conversation(
                    student_id=student.id,
                    conductor_id=conductor.id,
                    last_message_at=now - timedelta(minutes=idx),
                )
                conversations.append(conversation)
            session.add_all(conversations)
            await session.flush()

            messages: list[Message] = []
            image_count = 0
            for idx, student in enumerate(students):
                conversation = conversations[idx]
                student_message = Message(
                    conversation_id=conversation.id,
                    sender_id=student.id,
                    body=f"Append message from student {idx + 1}.",
                    is_read=True,
                    read_at=now - timedelta(hours=1, minutes=idx),
                    created_at=now - timedelta(hours=1, minutes=idx),
                )
                # Add image to conductor's response every 2nd message
                conductor_message = Message(
                    conversation_id=conversation.id,
                    sender_id=conductor.id,
                    body="Append response from conductor.",
                    is_read=False,
                    created_at=now - timedelta(minutes=idx),
                )
                if idx % 2 == 0:
                    print(f"[{idx}] Attempting to upload image...")
                    image_key, image_size, content_type = _upload_seed_image(conversation.id, conductor.id)
                    if image_key:
                        conductor_message.image_object_key = image_key
                        conductor_message.image_content_type = content_type
                        conductor_message.image_size = image_size
                        image_count += 1
                        print(f"[{idx}] ✓ Image attached to message")
                    else:
                        print(f"[{idx}] ✗ Image upload failed")
                
                conversation.last_message_at = conductor_message.created_at
                messages.extend([student_message, conductor_message])
            session.add_all(messages)
            print(f"Total messages with images: {image_count}")

            notifications: list[Notification] = []
            for idx, student in enumerate(students):
                notifications.append(
                    Notification(
                        user_id=student.id,
                        title="Append task assigned",
                        body=f"Append IELTS task #{idx + 1} was assigned.",
                        type="new_task",
                        source_type="task",
                    )
                )
                notifications.append(
                    Notification(
                        user_id=student.id,
                        title="Append new message",
                        body="Conductor replied in append mode.",
                        type="new_message",
                        source_type="message",
                    )
                )
            session.add_all(notifications)

            events: list[CalendarEvent] = []
            for idx, student in enumerate(students):
                events.append(
                    CalendarEvent(
                        user_id=student.id,
                        title="Append appointment",
                        description=f"Append student #{idx + 1} appointment",
                        event_type="appointment",
                        start_time=slots[idx].start_time,
                        end_time=slots[idx].end_time,
                        source_id=appointments[idx].id,
                        source_type="appointment",
                    )
                )
                events.append(
                    CalendarEvent(
                        user_id=student.id,
                        title=f"Append task deadline #{idx + 1}",
                        description="Complete append task",
                        event_type="task_deadline",
                        start_time=tasks[idx * 3].deadline,
                        end_time=tasks[idx * 3].deadline + timedelta(hours=1),
                        source_id=tasks[idx * 3].id,
                        source_type="task",
                    )
                )
            session.add_all(events)

            faqs: list[FAQ] = []
            for idx in range(EXTRA_COUNT):
                seq = idx + 1
                faqs.append(
                    FAQ(
                        question=f"Append FAQ question {student_count + seq}?",
                        answer="Append FAQ answer.",
                        category="general",
                        order_index=faq_order_start + seq,
                        created_by=conductor.id,
                    )
                )
            session.add_all(faqs)

            alumni_items: list[AlumniStory] = []
            for idx, university in enumerate(universities):
                alumni_items.append(
                    AlumniStory(
                        author_id=conductor.id,
                        student_name=f"Append Alumni {student_count + idx + 1}",
                        graduation_year=2024 - (idx % 3),
                        university_id=university.id,
                        university_name=university.name,
                        program_name=programs[idx].name,
                        scholarship_type="Partial",
                        story_text="Append alumni story with consistent preparation.",
                        gpa_at_time=Decimal("3.4") + (Decimal("0.1") * (idx % 3)),
                        ielts_at_time=Decimal("6.5"),
                        sat_at_time=1320 + (idx * 10),
                        is_published=True,
                    )
                )
            session.add_all(alumni_items)

            documents: list[StudentDocument] = []
            for idx, student in enumerate(students):
                key, size, content_type = _upload_seed_document(student.id, "cv")
                documents.append(
                    StudentDocument(
                        student_id=student.id,
                        doc_type="cv",
                        object_key=key,
                        content_type=content_type,
                        size=size,
                        notes=f"Append seed CV for student #{idx + 1}",
                    )
                )
            session.add_all(documents)

            refresh_tokens = [
                RefreshToken(
                    user_id=user.id,
                    token_hash=hash_password(uuid.uuid4().hex),
                    expires_at=now + timedelta(days=30 + idx),
                )
                for idx, user in enumerate([admin, conductor, *students])
            ]
            session.add_all(refresh_tokens)

            await session.commit()
            print(f"Append seed completed. Added students: {len(students)}")
            return

        admin = await _create_user(session, "admin@nobal.local", "Admin User", ROLE_ADMIN)
        conductor = await _create_user(
            session,
            settings.conductor_email,
            "Conductor",
            ROLE_CONDUCTOR,
        )
        now = _now_utc()

        students: list[User] = []
        student_specs = [
            ("Aruzhan", "D", 2, Decimal("3.8"), True, Decimal("7.0"), True, 1420, "USA", "Computer Science"),
            ("Dias", "F", 3, Decimal("3.4"), True, Decimal("6.5"), False, None, "Kazakhstan", "Business"),
            ("Madina", "D", 2, Decimal("3.9"), True, Decimal("7.5"), True, 1480, "UK", "Economics"),
            ("Alim", "F", 3, Decimal("3.1"), False, None, True, 1310, "Canada", "Engineering"),
            ("Aigerim", "D", 2, Decimal("3.7"), True, Decimal("6.0"), False, None, "Netherlands", "Design"),
            ("Nursultan", "F", 3, Decimal("3.2"), True, Decimal("6.5"), True, 1360, "Germany", "Data Science"),
            ("Sofiya", "D", 2, Decimal("3.6"), False, None, True, 1290, "Korea", "International Relations"),
            ("Timur", "F", 3, Decimal("3.5"), True, Decimal("6.0"), False, None, "Singapore", "Finance"),
            ("Amina", "D", 2, Decimal("3.8"), True, Decimal("7.0"), True, 1450, "Australia", "Medicine"),
            ("Yerlan", "F", 3, Decimal("3.0"), False, None, False, None, "Poland", "Information Systems"),
        ]
        base_index = len(student_specs)
        for idx in range(EXTRA_COUNT):
            seq = base_index + idx + 1
            group_type = "D" if seq % 2 == 0 else "F"
            course_year = 2 if seq % 2 == 0 else 3
            gpa = Decimal("3.0") + (Decimal("0.1") * (seq % 5))
            ielts_passed = seq % 2 == 0
            ielts_score = Decimal("6.0") + (Decimal("0.1") * (seq % 5)) if ielts_passed else None
            sat_passed = seq % 3 == 0
            sat_score = 1200 + (seq % 5) * 40 if sat_passed else None
            target_country = "USA" if seq % 2 == 0 else "Canada"
            target_major = "Engineering" if seq % 2 == 0 else "Business"
            student_specs.append(
                (
                    f"Extra {seq}",
                    group_type,
                    course_year,
                    gpa,
                    ielts_passed,
                    ielts_score,
                    sat_passed,
                    sat_score,
                    target_country,
                    target_major,
                )
            )
        for idx, spec in enumerate(student_specs, start=1):
            student_name = spec[0]
            student = await _create_user(
                session,
                f"student{idx}@nobal.local",
                f"{student_name} Student",
                ROLE_STUDENT,
            )
            students.append(student)

        # Student profiles
        profiles = []
        for student, spec in zip(students, student_specs, strict=True):
            _, group_type, course_year, gpa, ielts_passed, ielts_score, sat_passed, sat_score, target_country, target_major = spec
            profiles.append(
                StudentProfile(
                    user_id=student.id,
                    group_type=group_type,
                    course_year=course_year,
                    gpa=gpa,
                    ielts_passed=ielts_passed,
                    ielts_score=ielts_score,
                    sat_passed=sat_passed,
                    sat_score=sat_score,
                    target_country=target_country,
                    target_major=target_major,
                    notes=f"Seed profile for {student.full_name}",
                )
            )
        session.add_all(profiles)

        # Universities and programs
        university_specs = [
            ("Nazarbayev University", "Kazakhstan", "Astana", 219, "English"),
            ("KIMEP University", "Kazakhstan", "Almaty", 651, "English"),
            ("Al-Farabi Kazakh National University", "Kazakhstan", "Almaty", 1500, "Kazakh / Russian"),
            ("University of Manchester", "UK", "Manchester", 32, "English"),
            ("University of Toronto", "Canada", "Toronto", 21, "English"),
            ("National University of Singapore", "Singapore", "Singapore", 8, "English"),
            ("Seoul National University", "South Korea", "Seoul", 41, "English / Korean"),
            ("Delft University of Technology", "Netherlands", "Delft", 47, "English"),
            ("University of Melbourne", "Australia", "Melbourne", 14, "English"),
            ("Warsaw University of Technology", "Poland", "Warsaw", 801, "English / Polish"),
        ]
        base_index = len(university_specs)
        for idx in range(EXTRA_COUNT):
            seq = base_index + idx + 1
            university_specs.append(
                (
                    f"Sample University {seq}",
                    "Kazakhstan",
                    f"City {seq}",
                    900 + seq,
                    "English",
                )
            )
        universities: list[University] = []
        for idx, (name, country, city, ranking, language) in enumerate(university_specs, start=1):
            universities.append(
                University(
                    name=name,
                    country=country,
                    city=city,
                    qs_ranking=ranking,
                    language_of_instr=language,
                    website_url=f"https://example.com/universities/{idx}",
                    description=f"Seed university profile for {name}.",
                    is_published=True,
                    last_verified_at=now - timedelta(days=idx),
                )
            )
        session.add_all(universities)
        await session.flush()

        program_specs = [
            ("Computer Science", "bachelor", "CS", Decimal("3.2"), Decimal("6.5"), 0, "Fall"),
            ("Electrical Engineering", "bachelor", "Engineering", Decimal("3.0"), Decimal("6.0"), 0, "Fall"),
            ("Business Administration", "bachelor", "Business", Decimal("2.8"), Decimal("6.0"), 12000, "Fall, Spring"),
            ("Economics", "bachelor", "Economics", Decimal("3.1"), Decimal("6.5"), 18000, "Fall"),
            ("Mechanical Engineering", "bachelor", "Engineering", Decimal("3.0"), Decimal("6.0"), 20000, "Fall"),
            ("Data Science", "master", "Data", Decimal("3.3"), Decimal("6.5"), 22000, "Fall"),
            ("International Relations", "bachelor", "Humanities", Decimal("3.0"), Decimal("6.5"), 15000, "Fall"),
            ("Architecture", "bachelor", "Design", Decimal("2.9"), Decimal("6.0"), 19000, "Fall"),
            ("Medicine", "bachelor", "Health", Decimal("3.5"), Decimal("7.0"), 25000, "Spring"),
            ("Information Systems", "bachelor", "CS", Decimal("3.1"), Decimal("6.0"), 16000, "Fall"),
        ]
        base_index = len(program_specs)
        for idx in range(EXTRA_COUNT):
            seq = base_index + idx + 1
            program_specs.append(
                (
                    f"General Studies {seq}",
                    "bachelor",
                    "General",
                    Decimal("2.7"),
                    Decimal("5.5"),
                    8000 + (seq * 100),
                    "Fall",
                )
            )
        programs = []
        for university, program_spec in zip(universities, program_specs, strict=True):
            name, degree_level, field, min_gpa, min_ielts, tuition_usd, intake_seasons = program_spec
            programs.append(
                UniversityProgram(
                    university_id=university.id,
                    name=name,
                    degree_level=degree_level,
                    field=field,
                    min_gpa=min_gpa,
                    min_ielts=min_ielts,
                    tuition_usd=tuition_usd,
                    intake_seasons=intake_seasons,
                    scholarship_info="Merit scholarship available",
                    application_fee=50,
                    requirements_text="High school transcript, motivation letter, and interview.",
                )
            )
        session.add_all(programs)

        # News
        news_specs = [
            ("Scholarship deadline approaching", "Submit your applications before the deadline.", "deadline", 20),
            ("Summer camp registration", "Early registration is open now.", "summer_camp", 45),
            ("IELTS workshop announced", "Join the speaking workshop this Friday.", "webinar", 5),
            ("Hackathon roadmap published", "Check the new hackathon timeline.", "hackathon", 10),
            ("University fair next month", "Meet admissions teams from abroad.", "university_news", 30),
            ("ENT prep session", "Practice test and review session is scheduled.", "general", 7),
            ("Internship opportunities", "New internship openings added this week.", "internship", 14),
            ("Olympiad selection round", "Selection results will be posted soon.", "olympiad", 12),
            ("Application checklist update", "Documents checklist refreshed for all students.", "general", 3),
            ("Deadline reminder for NU applicants", "NU application deadline is near.", "deadline", 8),
        ]
        base_index = len(news_specs)
        for idx in range(EXTRA_COUNT):
            seq = base_index + idx + 1
            news_specs.append(
                (
                    f"Extra update {seq}",
                    "Additional announcement for students.",
                    "announcement",
                    50 + seq,
                )
            )
        news_items = [
            News(
                author_id=conductor.id,
                title=title,
                body=body,
                category=category,
                event_date=date.today() + timedelta(days=offset_days),
                is_published=True,
                views_count=idx * 13,
            )
            for idx, (title, body, category, offset_days) in enumerate(news_specs, start=1)
        ]
        session.add_all(news_items)

        # Roadmaps and template tasks
        roadmap_specs = [
            ("NU Admission Roadmap", "Roadmap for NU application", "NU"),
            ("Abroad CS Roadmap", "Apply to computer science programs abroad", "Abroad_IT"),
            ("Business Roadmap", "Apply to business schools", "Abroad_Business"),
            ("Scholarship Roadmap", "Scholarship-focused preparation track", "Scholarship"),
            ("IELTS Fast Track", "Intensive IELTS preparation", "IELTS"),
            ("SAT Track", "SAT preparation timeline", "SAT"),
            ("ENT Track", "ENT preparation roadmap", "ENT"),
            ("Portfolio Track", "Build design and application portfolio", "Portfolio"),
            ("Interview Track", "Admissions interview prep", "Interview"),
            ("Backup Applications", "Fallback university application plan", "Backup"),
        ]
        base_index = len(roadmap_specs)
        for idx in range(EXTRA_COUNT):
            seq = base_index + idx + 1
            roadmap_specs.append(
                (
                    f"Extra Roadmap {seq}",
                    "Additional roadmap for testing.",
                    f"Extra_{seq}",
                )
            )
        roadmaps: list[Roadmap] = []
        for title, description, target_type in roadmap_specs:
            roadmaps.append(
                Roadmap(
                    title=title,
                    description=description,
                    target_type=target_type,
                    is_public=True,
                    created_by=conductor.id,
                )
            )
        session.add_all(roadmaps)
        await session.flush()

        template_tasks = []
        for idx, roadmap in enumerate(roadmaps, start=1):
            template_tasks.append(
                RoadmapTemplateTask(
                    roadmap_id=roadmap.id,
                    title=f"Plan step {idx}A",
                    description="First milestone for this roadmap.",
                    order_index=1,
                    days_offset=7,
                )
            )
            template_tasks.append(
                RoadmapTemplateTask(
                    roadmap_id=roadmap.id,
                    title=f"Plan step {idx}B",
                    description="Second milestone for this roadmap.",
                    order_index=2,
                    days_offset=14,
                )
            )
        session.add_all(template_tasks)

        # Student roadmaps and tasks
        student_roadmaps: list[StudentRoadmap] = []
        for idx, student in enumerate(students):
            student_roadmaps.append(
                StudentRoadmap(
                    student_id=student.id,
                    roadmap_id=roadmaps[idx].id,
                    assigned_by=conductor.id,
                    title=roadmaps[idx].title,
                    is_active=True,
                )
            )
        session.add_all(student_roadmaps)
        await session.flush()

        tasks: list[Task] = []
        for idx, student in enumerate(students):
            student_roadmap = student_roadmaps[idx]
            tasks.append(
                Task(
                    student_id=student.id,
                    created_by=conductor.id,
                    title=f"IELTS practice #{idx + 1}",
                    description="Mock test and review errors",
                    status=TASK_STATUS_IN_PROGRESS,
                    priority="high",
                    deadline=now + timedelta(days=10 + idx),
                    is_conductor_task=True,
                    student_roadmap_id=student_roadmap.id,
                )
            )
            tasks.append(
                Task(
                    student_id=student.id,
                    created_by=student.id,
                    title=f"Personal study plan #{idx + 1}",
                    description="Plan weekly self-study",
                    status=TASK_STATUS_TODO,
                    priority="medium",
                    deadline=now + timedelta(days=5 + idx),
                    is_conductor_task=False,
                )
            )
            tasks.append(
                Task(
                    student_id=student.id,
                    created_by=conductor.id,
                    title=f"Submit transcript #{idx + 1}",
                    description="Upload latest transcript",
                    status=TASK_STATUS_DONE if idx % 2 == 0 else TASK_STATUS_OVERDUE,
                    priority="low",
                    deadline=now - timedelta(days=2 + idx),
                    completed_at=now - timedelta(days=1 + idx) if idx % 2 == 0 else None,
                    is_conductor_task=True,
                )
            )
        session.add_all(tasks)
        await session.flush()

        # Availability slots and appointments
        slots: list[AvailabilitySlot] = []
        slots_count = len(students) + 2
        for idx in range(slots_count):
            slot_start = now + timedelta(days=(idx // 2) + 1, hours=(idx % 2) * 2)
            slots.append(
                AvailabilitySlot(
                    conductor_id=conductor.id,
                    start_time=slot_start,
                    end_time=slot_start + timedelta(minutes=45),
                    duration_min=45,
                    is_available=idx >= len(students),
                )
            )
        session.add_all(slots)
        await session.flush()

        appointment_statuses = [
            APPOINTMENT_STATUS_CONFIRMED,
            APPOINTMENT_STATUS_PENDING,
            APPOINTMENT_STATUS_COMPLETED,
        ]
        status_cycle = [
            appointment_statuses[idx % len(appointment_statuses)]
            for idx in range(len(students))
        ]
        appointments: list[Appointment] = []
        for idx, student in enumerate(students):
            slot = slots[idx]
            slot.is_available = False
            appointments.append(
                Appointment(
                    slot_id=slot.id,
                    student_id=student.id,
                    conductor_id=conductor.id,
                    status=status_cycle[idx],
                    notes=f"Discuss roadmap and deadlines for student {idx + 1}",
                )
            )
        session.add_all(appointments)
        await session.flush()

        created_convos = []
        # Conversations and messages
        for idx, student in enumerate(students):
            convo = Conversation(
                student_id=student.id,
                conductor_id=conductor.id,
                last_message_at=now - timedelta(minutes=idx),
            )
            session.add(convo)
            await session.flush()
            created_convos.append(convo)

            msg1 = Message(
                conversation_id=convo.id,
                sender_id=student.id,
                body=f"Hello! I have a question about my roadmap #{idx + 1}.",
                is_read=True,
                read_at=now - timedelta(hours=1, minutes=idx),
                created_at=now - timedelta(hours=1, minutes=idx),
            )
            msg2 = Message(
                conversation_id=convo.id,
                sender_id=conductor.id,
                body="Sure, let's review it in our next meeting.",
                is_read=False,
                created_at=now - timedelta(minutes=idx),
            )
            session.add_all([msg1, msg2])
            convo.last_message_at = msg2.created_at

        extra_task_students = students[:EXTRA_COUNT]
        for idx, student in enumerate(extra_task_students):
            extra_convo = created_convos[idx]

            session.add_all(
                [
                    Message(
                        conversation_id=extra_convo.id,
                        sender_id=student.id,
                        body=f"Extra seed message from student {idx + 1}.",
                        is_read=True,
                        read_at=now - timedelta(hours=2, minutes=idx),
                        created_at=now - timedelta(hours=2, minutes=idx),
                    ),
                    Message(
                        conversation_id=extra_convo.id,
                        sender_id=conductor.id,
                        body="Thanks for the update.",
                        is_read=False,
                        created_at=now - timedelta(minutes=30 + idx),
                    ),
                ]
            )

        # Notifications
        notifications = []
        for idx, student in enumerate(students):
            notifications.append(
                Notification(
                    user_id=student.id,
                    title="New task assigned",
                    body=f"IELTS practice #{idx + 1} was assigned.",
                    type="new_task",
                    source_type="task",
                )
            )
            notifications.append(
                Notification(
                    user_id=student.id,
                    title="New message received",
                    body="Your conductor replied to your question.",
                    type="new_message",
                    source_type="message",
                )
            )
        notifications.append(
            Notification(
                user_id=conductor.id,
                title="Appointment booked",
                body="Students booked multiple slots.",
                type="appointment_confirmed",
                source_type="appointment",
            )
        )
        session.add_all(notifications)

        # Calendar events
        events = []
        for idx, student in enumerate(students):
            events.append(
                CalendarEvent(
                    user_id=student.id,
                    title="Appointment with Conductor",
                    description=f"Discuss student #{idx + 1} roadmap",
                    event_type="appointment",
                    start_time=slots[idx].start_time,
                    end_time=slots[idx].end_time,
                    source_id=appointments[idx].id,
                    source_type="appointment",
                )
            )
            events.append(
                CalendarEvent(
                    user_id=student.id,
                    title=f"Task deadline #{idx + 1}",
                    description="Complete assigned task",
                    event_type="task_deadline",
                    start_time=tasks[idx * 3].deadline,
                    end_time=tasks[idx * 3].deadline + timedelta(hours=1),
                    source_id=tasks[idx * 3].id,
                    source_type="task",
                )
            )
        events.append(
            CalendarEvent(
                user_id=students[0].id,
                title="Scholarship deadline",
                description="Submit applications",
                event_type="news_event",
                start_time=now + timedelta(days=20),
                end_time=now + timedelta(days=20, hours=1),
                source_id=news_items[0].id,
                source_type="news",
            )
        )
        for idx, student in enumerate(students[:EXTRA_COUNT]):
            event_start = now + timedelta(days=30 + idx)
            events.append(
                CalendarEvent(
                    user_id=student.id,
                    title=f"Extra event {idx + 1}",
                    description="Additional calendar entry.",
                    event_type="custom",
                    start_time=event_start,
                    end_time=event_start + timedelta(hours=1),
                    source_type="custom",
                )
            )
        session.add_all(events)

        # FAQ
        faq_specs = [
            ("How to upload documents?", "Go to Documents and upload your file.", "documents"),
            ("How to book an appointment?", "Choose an available slot and confirm.", "appointments"),
            ("How to reset password?", "Use the forgot password flow from login.", "auth"),
            ("How are tasks assigned?", "The conductor assigns tasks from the dashboard.", "tasks"),
            ("How to update profile?", "Open your profile and save changes.", "profile"),
            ("How to read notifications?", "Open the notifications panel in the app.", "notifications"),
            ("How to view roadmaps?", "Go to the roadmaps section in the student app.", "roadmaps"),
            ("Can I create personal tasks?", "Yes, students can add personal tasks.", "tasks"),
            ("Where do news items appear?", "In the news feed and calendar.", "news"),
            ("How to contact the conductor?", "Use the messages section.", "messages"),
        ]
        base_index = len(faq_specs)
        for idx in range(EXTRA_COUNT):
            seq = base_index + idx + 1
            faq_specs.append(
                (
                    f"Extra FAQ question {seq}?",
                    "Sample answer for extra FAQ.",
                    "general",
                )
            )
        faqs = [
            FAQ(
                question=question,
                answer=answer,
                category=category,
                order_index=idx,
                created_by=conductor.id,
            )
            for idx, (question, answer, category) in enumerate(faq_specs, start=1)
        ]
        session.add_all(faqs)

        # Alumni
        alumni_items = []
        for idx in range(len(universities)):
            university = universities[idx]
            alumni_items.append(
                AlumniStory(
                    author_id=conductor.id,
                    student_name=f"Alumni {idx + 1}",
                    graduation_year=2024 - (idx % 3),
                    university_id=university.id,
                    university_name=university.name,
                    program_name=programs[idx].name,
                    scholarship_type="Full" if idx % 2 == 0 else "Partial",
                    story_text="Prepared early, followed the roadmap, and stayed consistent.",
                    gpa_at_time=Decimal("3.5") + (Decimal("0.1") * (idx % 3)),
                    ielts_at_time=Decimal("6.5") + (Decimal("0.5") * (idx % 2)),
                    sat_at_time=1350 + (idx * 10),
                    is_published=True,
                )
            )
        session.add_all(alumni_items)

        # Documents
        documents = []
        for idx, student in enumerate(students):
            key, size, content_type = _upload_seed_document(student.id, "cv")
            documents.append(
                StudentDocument(
                    student_id=student.id,
                    doc_type="cv",
                    object_key=key,
                    content_type=content_type,
                    size=size,
                    notes=f"Seed CV for student #{idx + 1}",
                )
            )
        for idx, student in enumerate(students[:EXTRA_COUNT]):
            key, size, content_type = _upload_seed_document(student.id, "transcript")
            documents.append(
                StudentDocument(
                    student_id=student.id,
                    doc_type="transcript",
                    object_key=key,
                    content_type=content_type,
                    size=size,
                    notes=f"Seed transcript for student #{idx + 1}",
                )
            )
        session.add_all(documents)

        # Refresh tokens
        refresh_tokens = [
            RefreshToken(
                user_id=user.id,
                token_hash=hash_password(uuid.uuid4().hex),
                expires_at=now + timedelta(days=30 + idx),
            )
            for idx, user in enumerate([admin, conductor, *students])
        ]
        session.add_all(refresh_tokens)

        extra_notifications = []
        for idx, student in enumerate(students[:EXTRA_COUNT]):
            extra_notifications.append(
                Notification(
                    user_id=student.id,
                    title=f"Extra reminder {idx + 1}",
                    body="Please review your upcoming tasks.",
                    type="reminder",
                    source_type="task",
                )
            )
        session.add_all(extra_notifications)

        await session.commit()

        print("Seed data created. Default password:", DEFAULT_PASSWORD)


if __name__ == "__main__":
    asyncio.run(seed_data())
