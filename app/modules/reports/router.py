from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_adviser_or_admin
from app.database import get_db
from app.modules.reports.schemas import OverviewResponse, StudentsResponse, UniversitiesResponse, OverviewReport, StudentProgressItem, UniversityStats
from app.modules.reports.service import ReportsService

router = APIRouter()


@router.get("/reports/overview", response_model=OverviewResponse)
async def overview(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_adviser_or_admin()),
) -> OverviewResponse:
    service = ReportsService(db)
    data = await service.overview(current_user.role)
    return OverviewResponse(data=OverviewReport(**data))


@router.get("/reports/students", response_model=StudentsResponse)
async def students(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_adviser_or_admin()),
) -> StudentsResponse:
    service = ReportsService(db)
    items = await service.students(current_user.role)
    return StudentsResponse(data=[StudentProgressItem(**i) for i in items])


@router.get("/reports/universities", response_model=UniversitiesResponse)
async def universities(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_adviser_or_admin()),
) -> UniversitiesResponse:
    service = ReportsService(db)
    data = await service.universities(current_user.role)
    return UniversitiesResponse(data=UniversityStats(**data))
