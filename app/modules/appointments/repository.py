from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appointments.models import AvailabilitySlot, Appointment


class AppointmentsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_slot(self, **kwargs) -> AvailabilitySlot:
        slot = AvailabilitySlot(**kwargs)
        self.db.add(slot)
        await self.db.flush()
        await self.db.refresh(slot)
        return slot

    async def list_available_slots(self, conductor_id: UUID | None = None, from_time: datetime | None = None) -> list[AvailabilitySlot]:
        stmt = select(AvailabilitySlot).where(AvailabilitySlot.is_available == True)
        if conductor_id:
            stmt = stmt.where(AvailabilitySlot.conductor_id == conductor_id)
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

    async def list_appointments_for_conductor(self, conductor_id: UUID) -> list[Appointment]:
        result = await self.db.execute(select(Appointment).where(Appointment.conductor_id == conductor_id).order_by(Appointment.created_at.desc()))
        return result.scalars().all()

    async def list_appointments_for_student(self, student_id: UUID) -> list[Appointment]:
        result = await self.db.execute(select(Appointment).where(Appointment.student_id == student_id).order_by(Appointment.created_at.desc()))
        return result.scalars().all()

    async def update_appointment_status(self, appt: Appointment, status: str) -> None:
        appt.status = status
        await self.db.flush()
