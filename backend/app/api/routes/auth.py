import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
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
from app.services.email_service import send_otp_email, send_welcome_email
from app.services.sms_service import send_otp_sms
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
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    db.add(Cart(user_id=user.id))
    
    # Automatically clean up expired OTP codes to prevent database bloat
    await db.execute(
        delete(OTPCode).where(OTPCode.expires_at < datetime.now(timezone.utc))
    )
    
    # Generate an activation OTP code
    code = generate_otp()
    otp = OTPCode(
        identifier=payload.email,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp)
    await db.commit()
    await db.refresh(user)
    
    # Send a friendly welcome email containing the activation code (with console fallback)
    await send_welcome_email(payload.email, payload.full_name, code)
    
    # Raise a 403 Forbidden to tell the user they need to verify
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Account created successfully. A verification code has been sent to your email to activate your account."
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        
    if not user.is_verified:
        # Automatically clean up expired OTP codes
        await db.execute(
            delete(OTPCode).where(OTPCode.expires_at < datetime.now(timezone.utc))
        )
        
        # Generate new verification code
        code = generate_otp()
        otp = OTPCode(
            identifier=user.email,
            code=code,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
        db.add(otp)
        await db.commit()
        await send_otp_email(user.email, code)
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Email address is not verified. A new verification code has been sent to your email."
        )
        
    return _issue_tokens(user)


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(payload: OTPRequest, db: AsyncSession = Depends(get_db)):
    # Automatically clean up expired OTP codes to prevent database bloat
    await db.execute(
        delete(OTPCode).where(OTPCode.expires_at < datetime.now(timezone.utc))
    )
    
    # Rate limit by identifier: at most 1 OTP request every 60 seconds per email/phone
    last_otp_result = await db.execute(
        select(OTPCode)
        .where(OTPCode.identifier == payload.identifier)
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    )
    last_otp = last_otp_result.scalar_one_or_none()
    if last_otp:
        time_passed = (datetime.now(timezone.utc) - last_otp.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        if time_passed < 60:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Please wait {int(60 - time_passed)} seconds before requesting another code."
            )
            
    code = generate_otp()
    otp = OTPCode(
        identifier=payload.identifier,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp)
    await db.commit()
    
    is_email = "@" in payload.identifier
    if is_email:
        await send_otp_email(payload.identifier, code)
    else:
        await send_otp_sms(payload.identifier, code)
    
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

    is_email = "@" in payload.identifier
    if is_email:
        result = await db.execute(select(User).where(User.email == payload.identifier))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email=payload.identifier, auth_provider=AuthProvider.otp, is_verified=True)
            db.add(user)
            await db.flush()
            db.add(Cart(user_id=user.id))
        else:
            user.is_verified = True
    else:
        result = await db.execute(select(User).where(User.phone == payload.identifier))
        user = result.scalar_one_or_none()
        if not user:
            # For phone OTP signup, set email=None and phone=identifier
            user = User(phone=payload.identifier, email=None, auth_provider=AuthProvider.otp, is_verified=True)
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
    if payload.id_token == "mock_google_token" and settings.ENVIRONMENT != "production":
        info = {
            "email": "google_test_user@example.com",
            "name": "Google Test User"
        }
    else:
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
