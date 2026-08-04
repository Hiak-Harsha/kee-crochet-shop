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
    identifier: EmailStr


class OTPVerify(BaseModel):
    identifier: EmailStr
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


class CustomRequestCreate(BaseModel):
    description: str = Field(..., max_length=1000)
    color_palette: str | None = Field(None, max_length=255)


class CustomRequestOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    description: str
    color_palette: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
