import random
import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_user
from app.api.routes.cart import _get_or_create_cart
from app.core.database import get_db
from app.models.order import (
    Order,
    OrderItem,
    OrderStatus,
    can_transition_order_status,
)
from app.models.user import User
from app.schemas.order import OrderCreate, OrderOut, RazorpayVerify
from app.services.inventory_service import InventoryService
from app.services.payment_service import PaymentService
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/orders", tags=["orders"])


async def _new_order_number(db: AsyncSession) -> str:
    """Generate collision-free order number like KC123456."""
    while True:
        num = f"KC{random.randint(100000, 999999)}"
        result = await db.execute(select(Order).where(Order.order_number == num))
        if not result.scalar_one_or_none():
            return num


def _order_load_options():
    return [
        selectinload(Order.items),
        selectinload(Order.payments),
    ]


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create an authoritative order from current cart:
    1. Validates and prices cart with Decimal precision (PricingService)
    2. Atomically locks and reserves inventory (InventoryService)
    3. Initiates payment with Razorpay gateway (PaymentService)
    4. Clears user cart
    """
    cart, _ = await _get_or_create_cart(db, user)
    if not cart.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cart is empty")

    # 1. Authoritative Pricing
    breakdown = await PricingService.calculate_cart_totals(
        cart.items,
        user=user,
        coupon_code=payload.coupon_code,
        db=db,
    )

    # 2. Build Order Record
    order_num = await _new_order_number(db)
    order = Order(
        order_number=order_num,
        user_id=user.id,
        status=OrderStatus.pending_payment,
        subtotal=float(breakdown.subtotal),
        item_discounts=float(breakdown.item_discounts),
        coupon_id=breakdown.coupon_id,
        coupon_code=breakdown.coupon_code,
        coupon_discount=float(breakdown.coupon_discount),
        gift_wrap_fee=float(breakdown.gift_wrap_fee),
        shipping_fee=float(breakdown.shipping_fee),
        tax=float(breakdown.tax),
        total=float(breakdown.total),
        shipping_address=payload.shipping_address.model_dump(),
        delivery_slot=payload.delivery_slot,
    )
    db.add(order)
    await db.flush()

    # 3. Create OrderItems
    for item in cart.items:
        p = item.product
        if not p:
            continue

        if item.variant:
            if item.variant.price is not None:
                unit_price = float(item.variant.price)
            else:
                unit_price = float(p.price) + float(item.variant.price_delta or 0.0)
            variant_name = f"{item.variant.name}: {item.variant.value}"
            sku = item.variant.sku
        else:
            unit_price = float(p.price)
            variant_name = None
            sku = p.slug

        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                product_title=p.title,
                variant_name=variant_name,
                sku=sku,
                unit_price=unit_price,
                quantity=item.quantity,
                gift_wrap=item.gift_wrap,
                note=item.note,
            )
        )

    # 4. Atomically Lock & Reserve Inventory
    await InventoryService.reserve_stock_for_order(order.id, cart.items, db)

    # 5. Create Razorpay Payment Order
    await PaymentService.create_payment_order(order, db)

    # 6. Clear Cart Items
    for item in list(cart.items):
        await db.delete(item)

    await db.commit()

    # Return order with eager-loaded items
    stmt = select(Order).options(*_order_load_options()).where(Order.id == order.id)
    res = await db.execute(stmt)
    return res.scalar_one()


@router.post("/verify-payment", response_model=OrderOut)
async def verify_payment(
    payload: RazorpayVerify,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Verify payment signature, mark order as paid, and commit inventory reservations.
    """
    stmt = select(Order).where(Order.id == payload.order_id, Order.user_id == user.id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    await PaymentService.verify_payment(
        order=order,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        db=db,
    )

    res = await db.execute(select(Order).options(*_order_load_options()).where(Order.id == order.id))
    return res.scalar_one()


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Secure and idempotent webhook endpoint for Razorpay asynchronous payment events.
    """
    body = await request.body()
    return await PaymentService.process_webhook(body, x_razorpay_signature, db)


@router.get("", response_model=list[OrderOut])
async def my_orders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Order)
        .options(*_order_load_options())
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Cancel an unpaid or processing order, releasing reserved stock back to inventory.
    """
    stmt = select(Order).options(*_order_load_options()).where(Order.id == order_id, Order.user_id == user.id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    if order.status not in (OrderStatus.pending_payment, OrderStatus.processing):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot cancel order in '{order.status.value}' status. Please contact support."
        )

    # Release reservations
    await InventoryService.release_reservations(order.id, db, reason="user_cancelled")
    order.status = OrderStatus.cancelled
    await db.commit()

    res = await db.execute(select(Order).options(*_order_load_options()).where(Order.id == order.id))
    return res.scalar_one()


# --- Admin Routes (Registered before generic /{order_id} to prevent path conflicts) ---

@router.get("/admin/all", response_model=list[OrderOut])
async def admin_list_orders(
    page: int = 1,
    limit: int = 20,
    status_filter: OrderStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    offset = (page - 1) * limit
    stmt = select(Order).options(*_order_load_options())
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/admin/stats")
async def admin_get_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    completed_statuses = [
        OrderStatus.paid,
        OrderStatus.processing,
        OrderStatus.packed,
        OrderStatus.shipped,
        OrderStatus.delivered,
        OrderStatus.completed,
    ]

    # Total Sales
    sales_stmt = select(func.sum(Order.total)).where(Order.status.in_(completed_statuses))
    sales_res = await db.execute(sales_stmt)
    total_sales = sales_res.scalar() or 0.0

    # Total Orders
    orders_stmt = select(func.count(Order.id))
    orders_res = await db.execute(orders_stmt)
    total_orders = orders_res.scalar() or 0

    # Average Order Value
    if total_orders > 0:
        avg_stmt = select(func.avg(Order.total)).where(Order.status.in_(completed_statuses))
        avg_res = await db.execute(avg_stmt)
        average_order_value = avg_res.scalar() or 0.0
    else:
        average_order_value = 0.0

    return {
        "total_sales": float(total_sales),
        "total_orders": int(total_orders),
        "average_order_value": float(average_order_value),
    }


@router.patch("/admin/{order_id}/status", response_model=OrderOut)
async def admin_update_status(
    order_id: uuid.UUID,
    new_status: OrderStatus,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Order).options(*_order_load_options()).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    if not can_transition_order_status(order.status, new_status):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid transition from '{order.status.value}' to '{new_status.value}'"
        )

    # If transitioning to cancelled/refunded, release reserved stock
    if new_status in (OrderStatus.cancelled, OrderStatus.refunded) and order.status not in (OrderStatus.cancelled, OrderStatus.refunded):
        await InventoryService.release_reservations(order.id, db, reason=f"admin_{new_status.value}")

    order.status = new_status
    await db.commit()

    res = await db.execute(select(Order).options(*_order_load_options()).where(Order.id == order_id))
    return res.scalar_one()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Order).options(*_order_load_options()).where(Order.id == order_id, Order.user_id == user.id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order
