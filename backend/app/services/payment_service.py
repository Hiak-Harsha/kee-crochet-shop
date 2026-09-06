import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
import razorpay
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.order import (
    Order,
    OrderStatus,
    Payment,
    PaymentEvent,
    PaymentStatus,
    Coupon,
    CouponRedemption,
)
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class PaymentService:
    @staticmethod
    def get_razorpay_client() -> razorpay.Client:
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Payment gateway is not configured on the server."
            )
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    @classmethod
    async def create_payment_order(cls, order: Order, db: AsyncSession) -> str:
        """
        Create Razorpay order for an order.
        Amount is converted to paise (integer).
        In production, failure raises an error; NEVER falls back to fake payment IDs.
        """
        amount_paise = int(Decimal(str(order.total)) * 100)
        
        # Check if gateway keys exist
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            try:
                client = cls.get_razorpay_client()
                rzp_order = client.order.create({
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": order.order_number,
                    "notes": {
                        "order_id": str(order.id),
                        "customer_id": str(order.user_id),
                    }
                })
                rzp_order_id = rzp_order["id"]
            except Exception as e:
                logger.error(f"Failed to create Razorpay order for order {order.order_number}: {e}")
                if settings.ENVIRONMENT == "production":
                    raise HTTPException(
                        status.HTTP_502_BAD_GATEWAY,
                        "Payment gateway communication failed. Please try again in a few moments."
                    )
                # Development/sandbox fallback
                rzp_order_id = f"rzp_mock_{uuid.uuid4().hex[:12]}"
        else:
            if settings.ENVIRONMENT == "production":
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "Payment gateway credentials are missing in production. Payments cannot be processed."
                )
            # Development/sandbox mock
            rzp_order_id = f"rzp_mock_{uuid.uuid4().hex[:12]}"

        order.razorpay_order_id = rzp_order_id
        return rzp_order_id

    @classmethod
    async def verify_payment(
        cls,
        order: Order,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        db: AsyncSession,
    ) -> Payment:
        """
        Verify payment signature and authorize order completion.
        Ensures supplied razorpay_order_id matches the application order's razorpay_order_id.
        """
        # 1. Verify that the supplied Razorpay order ID matches the application order
        if not order.razorpay_order_id or order.razorpay_order_id != razorpay_order_id:
            logger.warning(
                f"Order ID mismatch on verification: order has '{order.razorpay_order_id}', payload has '{razorpay_order_id}'"
            )
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Payment order ID does not match this order."
            )

        # 2. Check if this is a mock payment in development environment
        is_mock = (
            settings.ENVIRONMENT != "production"
            and (
                razorpay_signature == "mock_signature"
                or (order.razorpay_order_id and order.razorpay_order_id.startswith("rzp_mock"))
            )
        )

        if not is_mock:
            if not settings.RAZORPAY_KEY_SECRET:
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Razorpay secret key not configured")

            body = f"{razorpay_order_id}|{razorpay_payment_id}"
            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
                body.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, razorpay_signature):
                logger.error(f"Razorpay signature mismatch for order {order.order_number}")
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment signature verification failed")

        # 3. Create or update Payment record
        stmt = select(Payment).where(Payment.razorpay_order_id == razorpay_order_id)
        p_res = await db.execute(stmt)
        payment = p_res.scalar_one_or_none()

        if not payment:
            payment = Payment(
                order_id=order.id,
                payment_method="razorpay",
                amount=order.total,
                currency="INR",
                status=PaymentStatus.captured,
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
            )
            db.add(payment)
        else:
            payment.status = PaymentStatus.captured
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature

        # 4. Transition order status to paid
        order.status = OrderStatus.paid
        order.razorpay_payment_id = razorpay_payment_id

        # 5. Commit inventory reservations
        await InventoryService.commit_reservations(order.id, db)

        # 6. Record coupon redemption if coupon used
        if order.coupon_id:
            c_stmt = select(Coupon).where(Coupon.id == order.coupon_id)
            c_res = await db.execute(c_stmt)
            coupon = c_res.scalar_one_or_none()
            if coupon:
                coupon.times_used += 1
                db.add(
                    CouponRedemption(
                        coupon_id=coupon.id,
                        user_id=order.user_id,
                        order_id=order.id,
                        discount_amount=order.coupon_discount,
                    )
                )

        await db.commit()
        logger.info(f"Payment verified and order {order.order_number} marked as PAID.")
        return payment

    @classmethod
    async def process_webhook(
        cls,
        payload_bytes: bytes,
        signature: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Process incoming Razorpay webhook event with idempotency.
        """
        if not signature:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing signature header")

        is_mock = signature == "mock_webhook_signature" and settings.ENVIRONMENT != "production"

        if not is_mock:
            if not settings.RAZORPAY_KEY_SECRET:
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Razorpay secret key not configured")

            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, signature):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook signature")

        try:
            event_data = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON webhook payload")

        event_id = event_data.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
        event_type = event_data.get("event", "unknown")

        # Idempotency check: check if event_id already exists and is processed
        stmt = select(PaymentEvent).where(PaymentEvent.event_id == event_id)
        res = await db.execute(stmt)
        existing_event = res.scalar_one_or_none()

        if existing_event and existing_event.is_processed:
            logger.info(f"Webhook event {event_id} ({event_type}) was already processed. Skipping duplicate.")
            return {"status": "already_processed", "event_id": event_id}

        payment_entity = event_data.get("payload", {}).get("payment", {}).get("entity", {})
        rzp_order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if not existing_event:
            existing_event = PaymentEvent(
                event_id=event_id,
                event_type=event_type,
                razorpay_order_id=rzp_order_id,
                razorpay_payment_id=payment_id,
                payload=event_data,
                is_processed=False,
            )
            db.add(existing_event)
            await db.flush()

        # Handle event types
        if event_type == "payment.captured" and rzp_order_id:
            o_stmt = select(Order).where(Order.razorpay_order_id == rzp_order_id)
            o_res = await db.execute(o_stmt)
            order = o_res.scalar_one_or_none()

            if order and order.status in (OrderStatus.pending_payment, OrderStatus.processing):
                order.status = OrderStatus.paid
                order.razorpay_payment_id = payment_id
                await InventoryService.commit_reservations(order.id, db)
                logger.info(f"Webhook payment.captured processed for order {order.order_number}")

        elif event_type == "payment.failed" and rzp_order_id:
            o_stmt = select(Order).where(Order.razorpay_order_id == rzp_order_id)
            o_res = await db.execute(o_stmt)
            order = o_res.scalar_one_or_none()

            if order and order.status == OrderStatus.pending_payment:
                # Release reserved inventory on payment failure
                await InventoryService.release_reservations(order.id, db, reason="payment_failed")
                order.status = OrderStatus.cancelled
                logger.info(f"Webhook payment.failed processed for order {order.order_number}. Reservations released.")

        existing_event.is_processed = True
        await db.commit()

        return {"status": "ok", "event_id": event_id}
