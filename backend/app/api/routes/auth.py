import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.models.cart import Cart
from app.models.user import AuthProvider, OTPCode, User
from app.schemas.user import (
    GoogleLogin,
    OTPRequest,
    OTPVerify,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id), role=user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        auth_provider=AuthProvider.email,
    )
    db.add(user)
    await db.flush()
    db.add(Cart(user_id=user.id))
    await db.commit()
    await db.refresh(user)
    return _issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return _issue_tokens(user)


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(payload: OTPRequest, db: AsyncSession = Depends(get_db)):
    code = generate_otp()
    otp = OTPCode(
        identifier=payload.identifier,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp)
    await db.commit()
    # TODO: wire to SMS/email provider. For now the code is returned only in
    # development so the flow is testable end-to-end without a real provider.
    return {"message": "OTP sent", "dev_code": code if settings.ENVIRONMENT == "development" else None}


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OTPCode)
        .where(OTPCode.identifier == payload.identifier, OTPCode.code == payload.code, OTPCode.is_used == False)  # noqa: E712
        .order_by(OTPCode.created_at.desc())
    )
    otp = result.scalars().first()
    if not otp or otp.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OTP")
    otp.is_used = True

    result = await db.execute(select(User).where(User.email == payload.identifier))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=payload.identifier, auth_provider=AuthProvider.otp, is_verified=True)
        db.add(user)
        await db.flush()
        db.add(Cart(user_id=user.id))
    else:
        user.is_verified = True
    await db.commit()
    await db.refresh(user)
    return _issue_tokens(user)


@router.post("/google", response_model=TokenResponse)
async def google_login(payload: GoogleLogin, db: AsyncSession = Depends(get_db)):
    # Verify the Google ID token against Google's tokeninfo endpoint.
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo", params={"id_token": payload.id_token}
        )
    if resp.status_code != 200:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google token")
    info = resp.json()
    if settings.GOOGLE_CLIENT_ID and info.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token audience mismatch")

    email = info["email"]
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            full_name=info.get("name"),
            auth_provider=AuthProvider.google,
            is_verified=True,
        )
        db.add(user)
        await db.flush()
        db.add(Cart(user_id=user.id))
        await db.commit()
        await db.refresh(user)
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    result = await db.execute(select(User).where(User.id == uuid.UUID(data["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return _issue_tokens(user)
