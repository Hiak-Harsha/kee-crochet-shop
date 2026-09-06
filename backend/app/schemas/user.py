import uuid
from datetime import datetime
import re
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    phone: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OTPRequest(BaseModel):
    identifier: str

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: any) -> any:
        if isinstance(data, dict):
            if "identifier" not in data:
                if "email" in data:
                    data["identifier"] = data["email"]
                elif "phone" in data:
                    data["identifier"] = data["phone"]
        return data

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        v = v.strip()
        if "@" in v:
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
                raise ValueError("Invalid email address format")
            return v
        clean = "".join(c for c in v if c.isdigit())
        if len(clean) < 10 or len(clean) > 15:
            raise ValueError("Identifier must be a valid email or a 10-15 digit phone number")
        return v


class OTPVerify(BaseModel):
    identifier: str
    code: str

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: any) -> any:
        if isinstance(data, dict):
            if "identifier" not in data:
                if "email" in data:
                    data["identifier"] = data["email"]
                elif "phone" in data:
                    data["identifier"] = data["phone"]
            if "code" not in data and "otp" in data:
                data["code"] = data["otp"]
        return data

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        v = v.strip()
        if "@" in v:
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
                raise ValueError("Invalid email address format")
            return v
        clean = "".join(c for c in v if c.isdigit())
        if len(clean) < 10 or len(clean) > 15:
            raise ValueError("Identifier must be a valid email or a 10-15 digit phone number")
        return v


class GoogleLogin(BaseModel):
    id_token: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    role: str
    auth_provider: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut | None = None

    model_config = ConfigDict(from_attributes=True)


class UserSessionOut(BaseModel):
    id: uuid.UUID
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    expires_at: datetime
    is_revoked: bool

    model_config = ConfigDict(from_attributes=True)


class CustomRequestCreate(BaseModel):
    description: str = Field(..., max_length=1000)
    color_palette: str | None = Field(None, max_length=255)
    reference_images: list[str] = []


class CustomRequestUpdate(BaseModel):
    status: str | None = None
    estimated_price: float | None = None
    admin_notes: str | None = None


class CustomRequestOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    description: str
    color_palette: str | None = None
    reference_images: list[str] = []
    status: str
    estimated_price: float | None = None
    admin_notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
