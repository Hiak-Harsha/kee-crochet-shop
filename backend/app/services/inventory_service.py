import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import CartItem
from app.models.order import (
    InventoryReservation,
    InventoryTransaction,
    InventoryTransactionType,
    ReservationStatus,
)
from app.models.product import Product, ProductVariant

logger = logging.getLogger(__name__)

RESERVATION_TTL_MINUTES = 15


class InventoryService:
    @classmethod
    async def reserve_stock_for_order(
        cls,
        order_id: uuid.UUID,
        cart_items: list[CartItem],
        db: AsyncSession,
    ) -> list[InventoryReservation]:
        """
        Transactional inventory reservation with atomic conditional updates.
        Locks and decrements stock only if available stock >= requested quantity.
        Guaranteed safe against race conditions across SQLite, PostgreSQL, and MySQL.
        """
        reservations: list[InventoryReservation] = []
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESERVATION_TTL_MINUTES)

        for item in cart_items:
            product = item.product
            if not product:
                # Load product if not attached
                p_res = await db.execute(select(Product).where(Product.id == item.product_id))
                product = p_res.scalar_one_or_none()

            if not product or not product.is_active:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Product '{item.product_id}' is unavailable or inactive")

            if item.variant_id:
                # Atomic conditional decrement at variant SKU level
                update_stmt = (
                    update(ProductVariant)
                    .where(
                        ProductVariant.id == item.variant_id,
                        ProductVariant.stock >= item.quantity,
                        ProductVariant.is_active == True,
                    )
                    .values(stock=ProductVariant.stock - item.quantity)
                )
                u_res = await db.execute(update_stmt)

                if u_res.rowcount == 0:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        f"Insufficient stock for variant of '{product.title}'. Requested: {item.quantity}"
                    )

                reservation = InventoryReservation(
                    order_id=order_id,
                    product_id=product.id,
                    variant_id=item.variant_id,
                    quantity=item.quantity,
                    status=ReservationStatus.ACTIVE,
                    expires_at=expires_at,
                )
                db.add(reservation)
                reservations.append(reservation)

                # Record ledger transaction
                db.add(
                    InventoryTransaction(
                        product_id=product.id,
                        variant_id=item.variant_id,
                        transaction_type=InventoryTransactionType.RESERVATION_LOCK,
                        quantity_delta=-item.quantity,
                        reference_type="order_reservation",
                        reference_id=str(order_id),
                        note=f"Stock locked for order {order_id}",
                    )
                )
            else:
                # Atomic conditional decrement at product level
                update_stmt = (
                    update(Product)
                    .where(
                        Product.id == item.product_id,
                        Product.stock >= item.quantity,
                        Product.is_active == True,
                    )
                    .values(stock=Product.stock - item.quantity)
                )
                u_res = await db.execute(update_stmt)

                if u_res.rowcount == 0:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        f"Insufficient stock for '{product.title}'. Requested: {item.quantity}"
                    )

                reservation = InventoryReservation(
                    order_id=order_id,
                    product_id=product.id,
                    variant_id=None,
                    quantity=item.quantity,
                    status=ReservationStatus.ACTIVE,
                    expires_at=expires_at,
                )
                db.add(reservation)
                reservations.append(reservation)

                # Record ledger transaction
                db.add(
                    InventoryTransaction(
                        product_id=product.id,
                        variant_id=None,
                        transaction_type=InventoryTransactionType.RESERVATION_LOCK,
                        quantity_delta=-item.quantity,
                        reference_type="order_reservation",
                        reference_id=str(order_id),
                        note=f"Stock locked for order {order_id}",
                    )
                )

        return reservations

    @classmethod
    async def commit_reservations(cls, order_id: uuid.UUID, db: AsyncSession) -> None:
        """
        Commit active inventory reservations upon verified successful payment.
        """
        stmt = select(InventoryReservation).where(
            InventoryReservation.order_id == order_id,
            InventoryReservation.status == ReservationStatus.ACTIVE,
        )
        res = await db.execute(stmt)
        reservations = res.scalars().all()

        for r in reservations:
            r.status = ReservationStatus.COMMITTED
            db.add(
                InventoryTransaction(
                    product_id=r.product_id,
                    variant_id=r.variant_id,
                    transaction_type=InventoryTransactionType.RESERVATION_COMMIT,
                    quantity_delta=0,
                    reference_type="payment_confirmed",
                    reference_id=str(order_id),
                    note=f"Reservation committed for paid order {order_id}",
                )
            )

    @classmethod
    async def release_reservations(cls, order_id: uuid.UUID, db: AsyncSession, reason: str = "cancelled") -> None:
        """
        Release reserved stock and restore quantity back to inventory.
        """
        stmt = select(InventoryReservation).where(
            InventoryReservation.order_id == order_id,
            InventoryReservation.status.in_([ReservationStatus.ACTIVE, ReservationStatus.COMMITTED]),
        ).with_for_update()
        res = await db.execute(stmt)
        reservations = res.scalars().all()

        now = datetime.now(timezone.utc)
        for r in reservations:
            if r.variant_id:
                v_stmt = select(ProductVariant).where(ProductVariant.id == r.variant_id).with_for_update()
                v_res = await db.execute(v_stmt)
                variant = v_res.scalar_one_or_none()
                if variant:
                    variant.stock += r.quantity
            elif r.product_id:
                p_stmt = select(Product).where(Product.id == r.product_id).with_for_update()
                p_res = await db.execute(p_stmt)
                prod = p_res.scalar_one_or_none()
                if prod:
                    prod.stock += r.quantity

            r.status = ReservationStatus.RELEASED
            r.released_at = now

            db.add(
                InventoryTransaction(
                    product_id=r.product_id,
                    variant_id=r.variant_id,
                    transaction_type=InventoryTransactionType.RESERVATION_RELEASE,
                    quantity_delta=r.quantity,
                    reference_type=reason,
                    reference_id=str(order_id),
                    note=f"Stock restored due to {reason} for order {order_id}",
                )
            )

    @classmethod
    async def cleanup_expired_reservations(cls, db: AsyncSession) -> int:
        """
        Background cleanup job: finds expired ACTIVE reservations, restores inventory, and marks EXPIRED.
        """
        now = datetime.now(timezone.utc)
        stmt = select(InventoryReservation).where(
            InventoryReservation.status == ReservationStatus.ACTIVE,
            InventoryReservation.expires_at < now,
        ).with_for_update()
        res = await db.execute(stmt)
        expired_reservations = res.scalars().all()

        count = 0
        for r in expired_reservations:
            if r.variant_id:
                v_stmt = select(ProductVariant).where(ProductVariant.id == r.variant_id).with_for_update()
                v_res = await db.execute(v_stmt)
                variant = v_res.scalar_one_or_none()
                if variant:
                    variant.stock += r.quantity
            elif r.product_id:
                p_stmt = select(Product).where(Product.id == r.product_id).with_for_update()
                p_res = await db.execute(p_stmt)
                prod = p_res.scalar_one_or_none()
                if prod:
                    prod.stock += r.quantity

            r.status = ReservationStatus.EXPIRED
            r.released_at = now
            count += 1

            db.add(
                InventoryTransaction(
                    product_id=r.product_id,
                    variant_id=r.variant_id,
                    transaction_type=InventoryTransactionType.RESERVATION_RELEASE,
                    quantity_delta=r.quantity,
                    reference_type="expired_cleanup",
                    reference_id=str(r.order_id),
                    note=f"Stock auto-restored from expired reservation {r.id}",
                )
            )

        if count > 0:
            await db.commit()
            logger.info(f"Released {count} expired inventory reservations.")

        return count
