from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.auth.two_factor import router as two_factor_router
from app.modules.enrollments.router import router as enrollments_router
from app.modules.users.notification_settings import router as notification_settings_router
from app.modules.users.router import router as users_router
from app.modules.profile.router import router as profile_router
from app.modules.documents.router import router as documents_router
from app.modules.tasks.router import router as tasks_router
from app.modules.notifications.router import router as notifications_router
from app.modules.messages.router import router as messages_router
from app.modules.appointments.router import router as appointments_router
from app.modules.universities.router import router as universities_router
from app.modules.news.router import router as news_router
from app.modules.calendar.router import router as calendar_router
from app.modules.roadmaps.router import router as roadmaps_router
from app.modules.faq.router import router as faq_router
from app.modules.alumni.router import router as alumni_router
from app.modules.reports.router import router as reports_router
from app.modules.advisers.router import router as advisers_router
from app.modules.reviews.router import router as reviews_router
from app.modules.admin.router import router as admin_router
# from app.modules.universities.router import router as universities_router
# from app.modules.news.router import router as news_router
# from app.modules.tasks.router import router as tasks_router
# from app.modules.roadmaps.router import router as roadmaps_router
# from app.modules.appointments.router import router as appointments_router
# from app.modules.messages.router import router as messages_router
# from app.modules.calendar.router import router as calendar_router
# from app.modules.notifications.router import router as notifications_router
# from app.modules.faq.router import router as faq_router
# from app.modules.alumni.router import router as alumni_router
# from app.modules.reports.router import router as reports_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(two_factor_router, prefix="/auth", tags=["Auth 2FA"])
api_router.include_router(users_router, tags=["Users"])
api_router.include_router(profile_router, tags=["Profile"])
api_router.include_router(documents_router, tags=["Documents"])
api_router.include_router(tasks_router, tags=["Tasks"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(messages_router, prefix="/messages", tags=["Messages"])
api_router.include_router(appointments_router, prefix="/appointments", tags=["Appointments"])
api_router.include_router(universities_router, prefix="/universities", tags=["Universities"])
api_router.include_router(news_router, prefix="/news", tags=["News"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(roadmaps_router, tags=["Roadmaps"])
api_router.include_router(faq_router, tags=["FAQ"])
api_router.include_router(alumni_router, tags=["Alumni"])
api_router.include_router(reports_router, tags=["Reports"])
api_router.include_router(enrollments_router, tags=["Enrollments"])
api_router.include_router(notification_settings_router, tags=["Notification Settings"])
api_router.include_router(advisers_router, tags=["Advisers"])
api_router.include_router(reviews_router, tags=["Reviews"])
api_router.include_router(admin_router, tags=["Admin"])
# api_router.include_router(universities_router, prefix="/universities", tags=["Universities"])
# api_router.include_router(news_router, prefix="/news", tags=["News"])
# api_router.include_router(tasks_router, tags=["Tasks"])
# api_router.include_router(roadmaps_router, prefix="/roadmaps", tags=["Roadmaps"])
# api_router.include_router(appointments_router, prefix="/appointments", tags=["Appointments"])
# api_router.include_router(messages_router, tags=["Messages"])
# api_router.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
# api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
# api_router.include_router(faq_router, prefix="/faqs", tags=["FAQ"])
# api_router.include_router(alumni_router, prefix="/alumni", tags=["Alumni"])
# api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
