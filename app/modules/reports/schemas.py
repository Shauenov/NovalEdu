from typing import Dict
from uuid import UUID

from pydantic import BaseModel


class OverviewReport(BaseModel):
    total_students: int
    by_group: dict
    ielts_passed: int
    sat_passed: int
    avg_gpa: float | None
    tasks_completed_this_month: int
    appointments_this_month: int
    applied_abroad: int
    total_budget_usd: int  # sum of students' budget_max (target scholarship budget)


class StudentProgressItem(BaseModel):
    id: UUID
    full_name: str
    group_type: str | None
    course_year: int | None
    gpa: float | None
    ielts_passed: bool
    sat_passed: bool
    tasks_total: int
    tasks_done: int
    tasks_overdue: int


class UniversityStats(BaseModel):
    by_target_country: dict
    by_target_major: dict


class OverviewResponse(BaseModel):
    success: bool = True
    data: OverviewReport


class StudentsResponse(BaseModel):
    success: bool = True
    data: list[StudentProgressItem]


class UniversitiesResponse(BaseModel):
    success: bool = True
    data: UniversityStats
