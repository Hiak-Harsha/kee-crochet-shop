import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import Notification, NotificationChannel
from app.services.email_service import send_otp_email, send_welcome_email

logger = logging.getLogger(__name__)


class NotificationService:
    @classmethod
    async def dispatch_event_notification(
        cls,
        user_id: uuid.UUID,
        event_type: str,
        title: str,
        body: str,
        db: AsyncSession,
        channel: NotificationChannel = NotificationChannel.in_app,
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        """
        Record and queue in-app and external notification.
        """
        notification = Notification(
            user_id=user_id,
            channel=channel,
            event_type=event_type,
            title=title,
            body=body,
            is_read=False,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        logger.info(f"Notification [{event_type}] created for user {user_id}: {title}")
        return notification

    @staticmethod
    async def async_send_order_paid_email(user_email: str, order_number: str, total: float) -> None:
        """Background job to send order confirmation email without blocking checkout."""
        logger.info(f"Sending order confirmation email for {order_number} to {user_email} (Total: ₹{total})")
        # Can use Resend or SMTP here in background
