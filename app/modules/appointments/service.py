from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ALMATY_TZ,
    APPOINTMENT_STATUS_CANCELLED_BY_CONDUCTOR,
    APPOINTMENT_STATUS_CANCELLED_BY_STUDENT,
    APPOINTMENT_STATUS_COMPLETED,
    APPOINTMENT_STATUS_CONFIRMED,
    ROLE_ADMIN,
    ROLE_CONDUCTOR,
    ROLE_STUDENT,
)
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, ValidationException
from app.core.exceptions import ErrorCode
from app.modules.appointments.repository import AppointmentsRepository
from app.modules.calendar.repository import CalendarRepository
from app.modules.users.repository import UsersRepository


class AppointmentsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AppointmentsRepository(db)

    def _normalize_slot_times(
        self,
        start_time: datetime,
        end_time: datetime | None,
        duration_min: int | None,
    ) -> tuple[datetime, int]:
        if not end_time and not duration_min:
            raise ValidationException("Provide end_time or duration_min")

        if end_time:
            if end_time <= start_time:
                raise ValidationException("End time must be after start time")
            computed = int((end_time - start_time).total_seconds() // 60)
            if computed <= 0:
                raise ValidationException("End time must be after start time")
            if duration_min is not None and abs(computed - duration_min) > 1:
                raise ValidationException("duration_min does not match end_time")
            duration_min = computed
        else:
            if duration_min is None or duration_min <= 0:
                raise ValidationException("duration_min must be positive")
            end_time = start_time + timedelta(minutes=duration_min)

        return end_time, duration_min

    async def create_slot(
        self,
        conductor_id: UUID,
        start_time: datetime,
        end_time: datetime | None = None,
        duration_min: int | None = None,
    ):
        end_time, duration_min = self._normalize_slot_times(start_time, end_time, duration_min)
        slot = await self.repo.create_slot(
            conductor_id=conductor_id,
            start_time=start_time,
            end_time=end_time,
            duration_min=duration_min,
        )
        await self.db.commit()
        return slot

    async def create_slots_bulk(
        self,
        conductor_id: UUID,
        slots: list[tuple[datetime, datetime | None, int | None]],
    ):
        items = []
        for start_time, end_time, duration_min in slots:
            end_time, duration_min = self._normalize_slot_times(start_time, end_time, duration_min)
            slot = await self.repo.create_slot(
                conductor_id=conductor_id,
                start_time=start_time,
                end_time=end_time,
                duration_min=duration_min,
            )
            items.append(slot)
        await self.db.commit()
        return items

    async def list_available_slots(self, conductor_id: UUID | None = None, from_time: datetime | None = None):
        return await self.repo.list_available_slots(conductor_id=conductor_id, from_time=from_time)

    async def book(
        self,
        slot_id: UUID,
        student_id: UUID,
        notes: str | None = None,
        consultation_type: str = "video",
    ):
        slot = await self.repo.get_slot(slot_id)
        if not slot:
            raise NotFoundException("Slot not found")
        if not slot.is_available:
            raise ConflictException(error_code=ErrorCode.SLOT_ALREADY_BOOKED, message="Slot already booked")

        # mark slot unavailable
        await self.repo.mark_slot_unavailable(slot)

        appt = await self.repo.create_appointment(
            slot_id=slot.id,
            student_id=student_id,
            conductor_id=slot.conductor_id,
            status=APPOINTMENT_STATUS_CONFIRMED,
            consultation_type=consultation_type,
            notes=notes,
        )
        user_repo = UsersRepository(self.db)
        student = await user_repo.get_by_id(student_id)
        conductor = await user_repo.get_by_id(slot.conductor_id)

        calendar_repo = CalendarRepository(self.db)
        await calendar_repo.create(
            user_id=student_id,
            title=f"Appointment with {conductor.full_name if conductor else 'Conductor'}",
            description=notes,
            event_type="appointment",
            start_time=slot.start_time,
            end_time=slot.end_time,
            all_day=False,
            color="#3B82F6",
            source_id=appt.id,
            source_type="appointment",
        )
        await calendar_repo.create(
            user_id=slot.conductor_id,
            title=f"Appointment with {student.full_name if student else 'Student'}",
            description=notes,
            event_type="appointment",
            start_time=slot.start_time,
            end_time=slot.end_time,
            all_day=False,
            color="#3B82F6",
            source_id=appt.id,
            source_type="appointment",
        )
        await self.db.commit()

        # send notification/email (best-effort)
        try:
            from app.modules.notifications.service import NotificationsService
            from app.workers.email_tasks import send_email_task

            notif = NotificationsService(self.db)
            await notif.create_notification(
                user_id=slot.conductor_id,
                notification_type="appointment_booked",
                title="Appointment booked",
                body=f"Student booked a slot at {slot.start_time}",
                source_id=appt.id,
                source_type="appointment",
            )

            appt_time = slot.start_time.astimezone(ALMATY_TZ).strftime("%Y-%m-%d %H:%M")

            if student and student.email:
                send_email_task.delay(
                    to=student.email,
                    subject="Appointment confirmed",
                    template="appointment_confirmed.html",
                    context={
                        "full_name": student.full_name,
                        "appointment_time": appt_time,
                        "participant_name": conductor.full_name if conductor else "Conductor",
                    },
                )
            if conductor and conductor.email:
                send_email_task.delay(
                    to=conductor.email,
                    subject="Appointment confirmed",
                    template="appointment_confirmed.html",
                    context={
                        "full_name": conductor.full_name,
                        "appointment_time": appt_time,
                        "participant_name": student.full_name if student else "Student",
                    },
                )

            await self.db.commit()
        except Exception:
            pass

        return appt

    async def list_for_conductor(self, conductor_id: UUID):
        return await self.repo.list_appointments_for_conductor(conductor_id)

    async def list_for_student(self, student_id: UUID):
        return await self.repo.list_appointments_for_student(student_id)

    async def cancel(
        self,
        appointment_id: UUID,
        requester_id: UUID,
        requester_role: str,
        cancel_reason: str | None = None,
    ):
        appt = await self.repo.get_appointment(appointment_id)
        if not appt:
            raise NotFoundException("Appointment not found")
        if requester_role == ROLE_STUDENT and appt.student_id != requester_id:
            raise ForbiddenException("Only the participant can cancel this appointment")
        if requester_role == ROLE_CONDUCTOR and appt.conductor_id != requester_id:
            raise ForbiddenException("Only the participant can cancel this appointment")
        if requester_role not in (ROLE_STUDENT, ROLE_CONDUCTOR, ROLE_ADMIN):
            raise ForbiddenException("Only participants can cancel this appointment")

        by_conductor = requester_role in (ROLE_CONDUCTOR, ROLE_ADMIN)
        status = (
            APPOINTMENT_STATUS_CANCELLED_BY_CONDUCTOR
            if by_conductor
            else APPOINTMENT_STATUS_CANCELLED_BY_STUDENT
        )
        await self.repo.update_appointment_status(appt, status)
        appt.cancelled_at = datetime.now(tz=timezone.utc)
        appt.cancel_reason = cancel_reason
        slot = await self.repo.get_slot_by_appointment(appt)
        if slot:
            await self.repo.mark_slot_available(slot)

        calendar_repo = CalendarRepository(self.db)
        await calendar_repo.delete_by_source(appt.student_id, appt.id, "appointment")
        await calendar_repo.delete_by_source(appt.conductor_id, appt.id, "appointment")
        await self.db.commit()

        try:
            from app.modules.notifications.service import NotificationsService
            from app.modules.users.repository import UsersRepository
            from app.workers.email_tasks import send_email_task

            user_repo = UsersRepository(self.db)
            student = await user_repo.get_by_id(appt.student_id)
            conductor = await user_repo.get_by_id(appt.conductor_id)
            slot = await self.repo.get_slot(appt.slot_id) if appt.slot_id else None
            appt_time = (
                slot.start_time.astimezone(ALMATY_TZ).strftime("%Y-%m-%d %H:%M")
                if slot
                else "TBD"
            )
            reason = cancel_reason or ("Cancelled by conductor" if by_conductor else "Cancelled by student")

            notifier = NotificationsService(self.db)
            if student:
                await notifier.create_notification(
                    user_id=student.id,
                    notification_type="appointment_cancelled",
                    title="Appointment cancelled",
                    body=f"Appointment for {appt_time} was cancelled.",
                    source_id=appt.id,
                    source_type="appointment",
                )
            if conductor:
                await notifier.create_notification(
                    user_id=conductor.id,
                    notification_type="appointment_cancelled",
                    title="Appointment cancelled",
                    body=f"Appointment for {appt_time} was cancelled.",
                    source_id=appt.id,
                    source_type="appointment",
                )

            await self.db.commit()

            if student and student.email:
                send_email_task.delay(
                    to=student.email,
                    subject="Appointment cancelled",
                    template="appointment_cancelled.html",
                    context={
                        "full_name": student.full_name,
                        "appointment_time": appt_time,
                        "reason": reason,
                    },
                )
            if conductor and conductor.email:
                send_email_task.delay(
                    to=conductor.email,
                    subject="Appointment cancelled",
                    template="appointment_cancelled.html",
                    context={
                        "full_name": conductor.full_name,
                        "appointment_time": appt_time,
                        "reason": reason,
                    },
                )
        except Exception:
            pass

        return appt

    async def complete(self, appointment_id: UUID):
        appt = await self.repo.get_appointment(appointment_id)
        if not appt:
            raise NotFoundException("Appointment not found")
        await self.repo.update_appointment_status(appt, APPOINTMENT_STATUS_COMPLETED)
        await self.db.commit()
        return appt
