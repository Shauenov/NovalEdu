from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.permissions import CurrentUser, get_current_user, require_ADVISER_or_admin, require_student
from app.core.response import SuccessResponse
from app.modules.appointments.service import AppointmentsService
from app.modules.appointments.schemas import (
    AppointmentResponse,
    AppointmentsResponse,
    AppointmentOut,
    BookRequest,
    CancelRequest,
    SlotCreate,
    SlotOut,
    SlotsResponse,
    SlotsBatchCreate,
)

router = APIRouter()


@router.get("/slots", response_model=SlotsResponse)
async def list_slots(
    adviser_id: UUID | None = None,
    from_time: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    svc = AppointmentsService(db)
    slots = await svc.list_available_slots(adviser_id=adviser_id, from_time=from_time)
    return SlotsResponse(data=[SlotOut.model_validate(s) for s in slots])


@router.post("/slots", response_model=SlotsResponse, status_code=201)
async def create_slot(
    body: SlotCreate | SlotsBatchCreate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_ADVISER_or_admin()),
):
    svc = AppointmentsService(db)
    if isinstance(body, SlotsBatchCreate):
        items = await svc.create_slots_bulk(
            UUID(current_user.user_id),
            [(s.start_time, s.end_time, s.duration_min) for s in body.slots],
        )
        return SlotsResponse(data=[SlotOut.model_validate(s) for s in items])

    slot = await svc.create_slot(
        UUID(current_user.user_id),
        body.start_time,
        body.end_time,
        body.duration_min,
    )
    return SlotsResponse(data=[SlotOut.model_validate(slot)])


@router.delete("/slots/{slot_id}", response_model=SuccessResponse)
async def delete_slot(slot_id: UUID, db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(require_ADVISER_or_admin())):
    # For simplicity: soft-delete not implemented — leave for future
    svc = AppointmentsService(db)
    slot = await svc.repo.get_slot(slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.adviser_id != UUID(current_user.user_id):
        raise HTTPException(status_code=403, detail="Not allowed")
    # Only allow delete if available
    if not slot.is_available:
        raise HTTPException(status_code=409, detail="Cannot delete booked slot")
    await svc.repo.delete_slot(slot)
    await db.commit()
    return SuccessResponse()


@router.post("", response_model=AppointmentResponse, status_code=201)
async def book_appointment(
    body: BookRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = AppointmentsService(db)
    appt = await svc.book(body.slot_id, UUID(current_user.user_id), body.notes, body.consultation_type)
    return AppointmentResponse(data=AppointmentOut.model_validate(appt))


@router.get("", response_model=AppointmentsResponse)
async def list_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    svc = AppointmentsService(db)
    if current_user.role == "student":
        raise HTTPException(status_code=403, detail="Students should use /appointments/my")
    appts = await svc.list_for_adviser(UUID(current_user.user_id))
    return AppointmentsResponse(data=[AppointmentOut.model_validate(a) for a in appts])


@router.get("/my", response_model=AppointmentsResponse)
async def list_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_student()),
):
    svc = AppointmentsService(db)
    appts = await svc.list_for_student(UUID(current_user.user_id))
    return AppointmentsResponse(data=[AppointmentOut.model_validate(a) for a in appts])


@router.patch("/{appointment_id}/cancel", response_model=SuccessResponse)
async def cancel_appointment(
    appointment_id: UUID,
    body: CancelRequest | None = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
 ) -> SuccessResponse:
    svc = AppointmentsService(db)
    await svc.cancel(
        appointment_id,
        requester_id=UUID(current_user.user_id),
        requester_role=current_user.role,
        cancel_reason=body.reason if body else None,
    )
    return SuccessResponse()


@router.patch("/{appointment_id}/complete", response_model=SuccessResponse)
async def complete_appointment(appointment_id: UUID, db: AsyncSession = Depends(get_db), current_user: CurrentUser = Depends(require_ADVISER_or_admin())):
    svc = AppointmentsService(db)
    await svc.complete(appointment_id)
    return SuccessResponse()
