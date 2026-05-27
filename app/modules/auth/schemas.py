from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ─── Requests ────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    group_type: Literal["D1", "D2", "F1", "F2", "F3", "F4"]
    course_year: int = Field(..., ge=2, le=3)
    gpa: float | None = Field(None, ge=0.0, le=4.0)
    ielts_passed: bool = False
    ielts_score: float | None = Field(None, ge=0.0, le=9.0)
    sat_passed: bool = False
    sat_score: int | None = Field(None, ge=400, le=1600)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = Field(None, max_length=10)  # required only if 2FA is enabled


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


# ─── Responses ───────────────────────────────────────────────────────────────

class UserBrief(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserBrief


class AccessTokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class TokenEnvelope(BaseModel):
    success: bool = True
    data: TokenResponse


class AccessTokenEnvelope(BaseModel):
    success: bool = True
    data: AccessTokenResponse


class SessionOut(BaseModel):
    id: UUID
    device_name: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class SessionsResponse(BaseModel):
    success: bool = True
    data: list[SessionOut]
