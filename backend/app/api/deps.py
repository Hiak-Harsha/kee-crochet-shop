import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_token(creds.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid user identifier format")
    
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


async def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if creds is None:
        return None
    try:
        payload = decode_token(creds.credentials)
        if not payload or payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        user_uuid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None
