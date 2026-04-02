from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DeviceRegister(BaseModel):
    platform: str = "android"
    device_name: Optional[str] = None
    fcm_token: Optional[str] = None
    notification_listener_enabled: bool = False


class DeviceResponse(BaseModel):
    id: int
    platform: str
    device_name: Optional[str]
    notification_listener_enabled: bool

    class Config:
        from_attributes = True


class NotificationStatusUpdate(BaseModel):
    notification_listener_enabled: bool
    device_id: Optional[int] = None
