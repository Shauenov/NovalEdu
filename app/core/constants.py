from zoneinfo import ZoneInfo

# Timezone
ALMATY_TZ = ZoneInfo("Asia/Almaty")

# Roles
ROLE_STUDENT = "student"
ROLE_CONDUCTOR = "conductor"
ROLE_ADMIN = "admin"

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# MinIO bucket names
BUCKET_DOCUMENTS = "educonductor-documents"
BUCKET_AVATARS = "educonductor-avatars"
BUCKET_UNIVERSITIES = "educonductor-universities"
BUCKET_NEWS = "educonductor-news"
BUCKET_ALUMNI = "educonductor-alumni"

# All buckets with their public-read policy flag
MINIO_BUCKETS: dict[str, bool] = {
    BUCKET_DOCUMENTS: False,    # private — signed URLs only
    BUCKET_AVATARS: True,
    BUCKET_UNIVERSITIES: True,
    BUCKET_NEWS: True,
    BUCKET_ALUMNI: True,
}

# Signed URL expiry (seconds)
SIGNED_URL_EXPIRE_SECONDS = 3600

# OTP
OTP_EXPIRE_SECONDS = 900  # 15 minutes

# Redis cache TTLs (seconds)
CACHE_TTL_UNIVERSITIES = 300     # 5 min
CACHE_TTL_FAQS = 600             # 10 min
CACHE_TTL_ROADMAPS = 300         # 5 min
CACHE_TTL_UNREAD_COUNT = 60      # 1 min

# File allowed MIME types
ALLOWED_DOC_MIME_TYPES = frozenset({
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})

ALLOWED_IMAGE_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})

# Task statuses
TASK_STATUS_TODO = "todo"
TASK_STATUS_IN_PROGRESS = "in_progress"
TASK_STATUS_DONE = "done"
TASK_STATUS_OVERDUE = "overdue"

# Appointment statuses
APPOINTMENT_STATUS_PENDING = "pending"
APPOINTMENT_STATUS_CONFIRMED = "confirmed"
APPOINTMENT_STATUS_CANCELLED_BY_STUDENT = "cancelled_by_student"
APPOINTMENT_STATUS_CANCELLED_BY_CONDUCTOR = "cancelled_by_conductor"
APPOINTMENT_STATUS_COMPLETED = "completed"
