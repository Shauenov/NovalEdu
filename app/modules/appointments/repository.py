from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointments.models import AvailabilitySlot, Appointment
from app.modules.users.models import User


class AppointmentsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_slot(self, **kwargs) -> AvailabilitySlot:
        slot = AvailabilitySlot(**kwargs)
        self.db.add(slot)
        await self.db.flush()
        await self.db.refresh(slot)
        return slot

    async def list_available_slots(self, adviser_id: UUID | None = None, from_time: datetime | None = None) -> list[AvailabilitySlot]:
        stmt = select(AvailabilitySlot).where(AvailabilitySlot.is_available == True)
        if adviser_id:
            stmt = stmt.where(AvailabilitySlot.adviser_id == adviser_id)
        if from_time:
            stmt = stmt.where(AvailabilitySlot.start_time >= from_time)
        result = await self.db.execute(stmt.order_by(AvailabilitySlot.start_time))
        return result.scalars().all()

    async def get_slot(self, slot_id: UUID) -> AvailabilitySlot | None:
        result = await self.db.execute(select(AvailabilitySlot).where(AvailabilitySlot.id == slot_id))
        return result.scalar_one_or_none()

    async def delete_slot(self, slot: AvailabilitySlot) -> None:
        await self.db.delete(slot)
        await self.db.flush()

    async def mark_slot_unavailable(self, slot: AvailabilitySlot) -> None:
        slot.is_available = False
        await self.db.flush()

    async def mark_slot_available(self, slot: AvailabilitySlot) -> None:
        slot.is_available = True
        await self.db.flush()

    async def create_appointment(self, **kwargs) -> Appointment:
        appt = Appointment(**kwargs)
        self.db.add(appt)
        await self.db.flush()
        await self.db.refresh(appt)
        return appt

    async def get_appointment(self, appointment_id: UUID) -> Appointment | None:
        result = await self.db.execute(select(Appointment).where(Appointment.id == appointment_id))
        return result.scalar_one_or_none()

    async def get_slot_by_appointment(self, appt: Appointment) -> AvailabilitySlot | None:
        if not appt.slot_id:
            return None
        result = await self.db.execute(select(AvailabilitySlot).where(AvailabilitySlot.id == appt.slot_id))
        return result.scalar_one_or_none()

    async def list_appointments_for_adviser(self, adviser_id: UUID) -> list[dict]:
        stmt = (
            select(Appointment, User.full_name, User.avatar_url,
                   AvailabilitySlot.start_time, AvailabilitySlot.end_time)
            .join(User, User.id == Appointment.student_id)
            .outerjoin(AvailabilitySlot, AvailabilitySlot.id == Appointment.slot_id)
            .where(Appointment.adviser_id == adviser_id)
            .order_by(Appointment.created_at.desc())
        )
        rows = (await self.db.execute(stmt)).all()
        result = []
        for appt, full_name, avatar_url, slot_start, slot_end in rows:
            d = {k: v for k, v in appt.__dict__.items() if not k.startswith('_')}
            d['student_name'] = full_name
            d['student_avatar_url'] = avatar_url
            d['slot_start_time'] = slot_start
            d['slot_end_time'] = slot_end
            result.append(d)
        return result

    async def list_appointments_for_student(self, student_id: UUID) -> list[dict]:
        stmt = (
            select(Appointment, User.full_name, User.avatar_url,
                   AvailabilitySlot.start_time, AvailabilitySlot.end_time)
            .join(User, User.id == Appointment.student_id)
            .outerjoin(AvailabilitySlot, AvailabilitySlot.id == Appointment.slot_id)
            .where(Appointment.student_id == student_id)
            .order_by(Appointment.created_at.desc())
        )
        rows = (await self.db.execute(stmt)).all()
        result = []
        for appt, full_name, avatar_url, slot_start, slot_end in rows:
            d = {k: v for k, v in appt.__dict__.items() if not k.startswith('_')}
            d['student_name'] = full_name
            d['student_avatar_url'] = avatar_url
            d['slot_start_time'] = slot_start
            d['slot_end_time'] = slot_end
            result.append(d)
        return result

    async def update_appointment_status(self, appt: Appointment, status: str) -> None:
        appt.status = status
        await self.db.flush()

    async def get_next_for_student(self, student_id: UUID, now: datetime) -> dict | None:
        """The student's earliest active (pending/confirmed) appointment whose slot
        hasn't ended yet — covers both "happening now" and "next upcoming"."""
        stmt = (
            select(Appointment, User.full_name, User.avatar_url,
                   AvailabilitySlot.start_time, AvailabilitySlot.end_time)
            .join(User, User.id == Appointment.student_id)
            .join(AvailabilitySlot, AvailabilitySlot.id == Appointment.slot_id)
            .where(
                Appointment.student_id == student_id,
                Appointment.status.in_(['pending', 'confirmed']),
                AvailabilitySlot.end_time > now,
            )
            .order_by(AvailabilitySlot.start_time.asc())
            .limit(1)
        )
        row = (await self.db.execute(stmt)).first()
        if not row:
            return None
        appt, full_name, avatar_url, slot_start, slot_end = row
        d = {k: v for k, v in appt.__dict__.items() if not k.startswith('_')}
        d['student_name'] = full_name
        d['student_avatar_url'] = avatar_url
        d['slot_start_time'] = slot_start
        d['slot_end_time'] = slot_end
        return d
