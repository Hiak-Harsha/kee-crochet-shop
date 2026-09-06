import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hash a refresh token using SHA-256 for secure database lookup."""
    return hashlib.sha256(f"{token}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()


def hash_otp(code: str) -> str:
    """Hash a numeric OTP code using salted SHA-256."""
    return hashlib.sha256(f"otp:{code}:{settings.SECRET_KEY}".encode("utf-8")).hexdigest()


def verify_otp(plain_code: str, hashed_code: str) -> bool:
    """Verify incoming OTP against salted SHA-256 hash."""
    expected = hash_otp(plain_code)
    return secrets.compare_digest(expected, hashed_code)


def create_access_token(subject: str, role: str, session_id: str | None = None, expires_delta: timedelta | None = None) -> str:
    """Generate a short-lived JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "role": role,
        "sid": session_id,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, session_id: str | None = None, expires_delta: timedelta | None = None) -> str:
    """Generate a JWT refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode = {
        "sub": str(subject),
        "sid": session_id,
        "type": "refresh",
        "jti": secrets.token_hex(16),
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit numeric OTP."""
    return "".join(secrets.choice(string.digits) for _ in range(6))
