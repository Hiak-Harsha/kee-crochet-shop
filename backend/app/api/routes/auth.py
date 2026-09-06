import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_otp,
    hash_password,
    hash_token,
    verify_otp,
    verify_password,
)
from app.models.cart import Cart
from app.models.user import AuthProvider, OTPCode, OTPPurpose, User, UserRole, UserSession
from app.schemas.user import (
    GoogleLogin,
    OTPRequest,
    OTPVerify,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserOut,
    UserRegister,
    UserSessionOut,
)
from app.services.email_service import send_otp_email, send_welcome_email
from app.services.sms_service import send_otp_sms

router = APIRouter(prefix="/auth", tags=["auth"])


async def _create_user_session(
    user: User,
    request: Request,
    response: Response,
    db: AsyncSession,
) -> TokenResponse:
    """Helper to create session record, set HttpOnly refresh cookie, and return token response."""
    session_id = uuid.uuid4()
    user_agent = request.headers.get("user-agent", "")[:500]
    
    # Extract client IP
    client_ip = None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        parts = [p.strip() for p in xff.split(",")]
        if parts:
            client_ip = parts[0][:50]
    if not client_ip and request.client:
        client_ip = request.client.host[:50]

    access_token = create_access_token(str(user.id), role=user.role.value, session_id=str(session_id))
    refresh_token = create_refresh_token(str(user.id), session_id=str(session_id))
    refresh_hash = hash_token(refresh_token)

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        user_agent=user_agent,
        ip_address=client_ip,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(session)
    await db.commit()

    # Set HttpOnly, SameSite cookie
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    if payload.phone:
        existing_phone = await db.execute(select(User).where(User.phone == payload.phone))
        if existing_phone.scalar_one_or_none():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Phone number already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        auth_provider=AuthProvider.email,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    db.add(Cart(user_id=user.id))
    await db.commit()
    await db.refresh(user)

    try:
        await send_welcome_email(payload.email, payload.full_name, "")
    except Exception:
        pass

    return await _create_user_session(user, request, response, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account has been deactivated. Please contact support.")

    if not user.is_verified:
        code = generate_otp()
        hashed_c = hash_otp(code)
        otp = OTPCode(
            identifier=user.email,
            hashed_code=hashed_c,
            purpose=OTPPurpose.login,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
            attempts=0,
            max_attempts=3,
        )
        db.add(otp)
        await db.commit()
        await send_otp_email(user.email, code)
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Email address is not yet verified. A new 6-digit activation code has been sent to your email."
        )

    return await _create_user_session(user, request, response, db)


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(payload: OTPRequest, db: AsyncSession = Depends(get_db)):
    # Rate limit: at most 1 OTP request every 60 seconds per identifier
    last_otp_res = await db.execute(
        select(OTPCode)
        .where(OTPCode.identifier == payload.identifier)
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    )
    last_otp = last_otp_res.scalar_one_or_none()
    if last_otp:
        time_passed = (datetime.now(timezone.utc) - last_otp.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        if time_passed < 60:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Please wait {int(60 - time_passed)} seconds before requesting another code."
            )

    code = generate_otp()
    hashed_c = hash_otp(code)

    otp = OTPCode(
        identifier=payload.identifier,
        hashed_code=hashed_c,
        purpose=OTPPurpose.login,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        attempts=0,
        max_attempts=3,
    )
    db.add(otp)
    await db.commit()

    is_email = "@" in payload.identifier
    if is_email:
        await send_otp_email(payload.identifier, code)
    else:
        await send_otp_sms(payload.identifier, code)

    return {
        "message": "Verification code dispatched successfully",
        "dev_code": code if settings.ENVIRONMENT == "development" else None,
    }


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp_endpoint(
    payload: OTPVerify,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OTPCode)
        .where(OTPCode.identifier == payload.identifier, OTPCode.is_used == False)
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    )
    otp = result.scalar_one_or_none()

    if not otp:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No active verification code found for this identifier")

    if otp.attempts >= otp.max_attempts:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Maximum verification attempts exceeded. Please request a new code.")

    if otp.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Verification code has expired. Please request a new one.")

    if not verify_otp(payload.code, otp.hashed_code):
        otp.attempts += 1
        await db.commit()
        remaining = otp.max_attempts - otp.attempts
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid verification code. {remaining} attempt(s) remaining."
        )

    otp.is_used = True
    otp.consumed_at = datetime.now(timezone.utc)

    is_email = "@" in payload.identifier
    if is_email:
        user_res = await db.execute(select(User).where(User.email == payload.identifier))
        user = user_res.scalar_one_or_none()
        if not user:
            user = User(email=payload.identifier, auth_provider=AuthProvider.otp, is_verified=True)
            db.add(user)
            await db.flush()
            db.add(Cart(user_id=user.id))
        else:
            user.is_verified = True
    else:
        user_res = await db.execute(select(User).where(User.phone == payload.identifier))
        user = user_res.scalar_one_or_none()
        if not user:
            user = User(phone=payload.identifier, email=None, auth_provider=AuthProvider.otp, is_verified=True)
            db.add(user)
            await db.flush()
            db.add(Cart(user_id=user.id))
        else:
            user.is_verified = True

    await db.commit()
    await db.refresh(user)

    return await _create_user_session(user, request, response, db)


@router.post("/google", response_model=TokenResponse)
async def google_login(
    payload: GoogleLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    if payload.id_token == "mock_google_token" and settings.ENVIRONMENT != "production":
        info = {
            "email": "google_test_user@example.com",
            "name": "Google Test User",
            "email_verified": "true",
        }
    else:
        if settings.ENVIRONMENT == "production" and not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Google Sign-In is not configured on the production server.")

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo", params={"id_token": payload.id_token}
            )

        if resp.status_code != 200:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google ID token")

        info = resp.json()

        # Strict validation
        if settings.GOOGLE_CLIENT_ID and info.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token audience mismatch")

        issuer = info.get("iss", "")
        if issuer not in ("accounts.google.com", "https://accounts.google.com"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token issuer")

        if info.get("email_verified") not in (True, "true", "True"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google account email is not verified")

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
    else:
        if not user.is_verified:
            user.is_verified = True
            await db.commit()

    return await _create_user_session(user, request, response, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Check cookie first, fallback to payload
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME) or payload.refresh_token
    if not raw_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token missing")

    data = decode_token(raw_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token structure or expired")

    user_id_str = data.get("sub")
    session_id_str = data.get("sid")
    if not user_id_str or not session_id_str:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed refresh token claims")

    user_uuid = uuid.UUID(user_id_str)
    sess_uuid = uuid.UUID(session_id_str)

    # Check session in database
    s_stmt = select(UserSession).where(UserSession.id == sess_uuid, UserSession.user_id == user_uuid)
    s_res = await db.execute(s_stmt)
    user_session = s_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not user_session or user_session.is_revoked or user_session.expires_at.replace(tzinfo=timezone.utc) < now:
        # Potential token reuse or revoked session: clear cookie
        response.delete_cookie(settings.SESSION_COOKIE_NAME)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or revoked")

    token_hash = hash_token(raw_token)
    if user_session.refresh_token_hash != token_hash:
        # Token rotation violation (token reuse attack detected!)
        # Revoke session immediately!
        user_session.is_revoked = True
        user_session.revoked_at = now
        await db.commit()
        response.delete_cookie(settings.SESSION_COOKIE_NAME)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Security violation: refresh token reuse detected")

    # Fetch user
    u_stmt = select(User).where(User.id == user_uuid)
    u_res = await db.execute(u_stmt)
    user = u_res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive or not found")

    # Refresh token rotation: issue NEW refresh token and update session hash
    new_access_token = create_access_token(str(user.id), role=user.role.value, session_id=str(user_session.id))
    new_refresh_token = create_refresh_token(str(user.id), session_id=str(user_session.id))
    user_session.refresh_token_hash = hash_token(new_refresh_token)
    await db.commit()

    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=new_refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if raw_token:
        data = decode_token(raw_token)
        if data and data.get("sid"):
            try:
                sid = uuid.UUID(data["sid"])
                await db.execute(
                    update(UserSession)
                    .where(UserSession.id == sid)
                    .values(is_revoked=True, revoked_at=datetime.now(timezone.utc))
                )
                await db.commit()
            except Exception:
                pass

    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all_sessions(
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id)
        .values(is_revoked=True, revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"message": "All active sessions have been revoked"}


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.get("/sessions", response_model=list[UserSessionOut])
async def list_user_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.is_revoked == False)
        .order_by(UserSession.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
