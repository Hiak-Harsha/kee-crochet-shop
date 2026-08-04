import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OTPRequest(BaseModel):
    identifier: str  # Email or phone number


class OTPVerify(BaseModel):
    identifier: str
    code: str


class GoogleLogin(BaseModel):
    id_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    phone: str | None = None
    role: str
    auth_provider: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
