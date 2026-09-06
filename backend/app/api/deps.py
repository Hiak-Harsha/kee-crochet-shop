import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole, UserSession

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = None
    if creds and creds.credentials:
        token = creds.credentials
    else:
        # Fallback check for access_token cookie
        token = request.cookies.get("kc_access_token")

    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token")

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid user identifier format")

    # Session revocation check if session ID is present in token
    session_id = payload.get("sid")
    if session_id:
        try:
            s_uuid = uuid.UUID(session_id)
            s_stmt = select(UserSession).where(UserSession.id == s_uuid)
            s_res = await db.execute(s_stmt)
            sess = s_res.scalar_one_or_none()
            if not sess or sess.is_revoked:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session has been revoked or expired")
        except (ValueError, TypeError):
            pass

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User account not found or deactivated")

    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrative privileges required")
    return user


async def get_current_user_optional(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    try:
        return await get_current_user(request=request, creds=creds, db=db)
    except Exception:
        return None
