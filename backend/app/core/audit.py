import logging
from typing import Any
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog, User

logger = logging.getLogger(__name__)


async def log_audit_event(
    db: AsyncSession,
    action: str,
    entity_type: str,
    entity_id: str,
    actor: User | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    """
    Persist an audit log record for administrative and system mutations.
    """
    ip_addr = None
    user_agent = None

    if request:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            ip_addr = xff.split(",")[0].strip()[:50]
        elif request.client:
            ip_addr = request.client.host[:50]
        user_agent = request.headers.get("user-agent", "")[:500]

    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_role=actor.role.value if actor and hasattr(actor.role, "value") else (str(actor.role) if actor else "system"),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_addr,
        user_agent=user_agent,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception as e:
        logger.warning(f"Failed to flush audit log entry: {e}")
    return entry
