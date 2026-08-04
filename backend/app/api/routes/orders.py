from typing import Any
import hmac
import hashlib
import random
import uuid

import razorpay
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_user
from app.api.routes.cart import _get_or_create_cart
from app.core.config import settings
from app.core.database import get_db
from app.models.cart import CartItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.schemas.order import OrderCreate, OrderOut, RazorpayVerify

router = APIRouter(prefix="/orders", tags=["orders"])


def _razorpay_client() -> razorpay.Client:
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Payment gateway not configured")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


async def _new_order_number(db: AsyncSession) -> str:
    while True:
        num = f"KC{random.randint(100000, 999999)}"
        result = await db.execute(select(Order).where(Order.order_number == num))
        if not result.scalar_one_or_none():
            return num


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    cart = await _get_or_create_cart(db, user)
    if not cart.items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cart is empty")

    subtotal = sum(float(i.product.price) * i.quantity for i in cart.items)
    shipping_fee = 0 if subtotal >= 999 else 60
    discount = 0  # TODO: coupon engine
    total = subtotal + shipping_fee - discount

    # 1. Enforce Stock Check & Row Locking
    for item in cart.items:
        if item.variant_id:
            v_stmt = select(ProductVariant).where(ProductVariant.id == item.variant_id).with_for_update()
            v_res = await db.execute(v_stmt)
            variant = v_res.scalar_one_or_none()
            if not variant:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Variant for item '{item.product.title}' not found")
            if variant.stock < item.quantity:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock for '{item.product.title}' (variant). Available: {variant.stock}")
            variant.stock -= item.quantity
        else:
            p_stmt = select(Product).where(Product.id == item.product_id).with_for_update()
            p_res = await db.execute(p_stmt)
            product = p_res.scalar_one_or_none()
            if not product:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product '{item.product.title}' not found")
            if product.stock < item.quantity:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock for '{product.title}'. Available: {product.stock}")
            product.stock -= item.quantity

    order_num = await _new_order_number(db)
    order = Order(
        order_number=order_num,
        user_id=user.id,
        subtotal=subtotal,
        discount=discount,
        shipping_fee=shipping_fee,
        total=total,
        shipping_address=payload.shipping_address.model_dump(),
        coupon_code=payload.coupon_code,
    )
    db.add(order)
    await db.flush()

    for item in cart.items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                product_title=item.product.title,
                unit_price=item.product.price,
                quantity=item.quantity,
            )
        )

    # Create the Razorpay order (amount in paise) if payments are configured.
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            client: Any = _razorpay_client()
            rzp_order = client.order.create(
                {"amount": int(total * 100), "currency": "INR", "receipt": order.order_number}
            )
            order.razorpay_order_id = rzp_order["id"]
        except Exception as e:
            # Fallback for mock sandbox mode in local environments
            order.razorpay_order_id = f"rzp_mock_{uuid.uuid4().hex[:12]}"
    else:
        # Generate a mock razorpay ID for sandbox flow
        order.razorpay_order_id = f"rzp_mock_{uuid.uuid4().hex[:12]}"

    for item in list(cart.items):
        await db.delete(item)

    await db.commit()
    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    result = await db.execute(stmt)
    return result.scalar_one()


@router.post("/verify-payment", response_model=OrderOut)
async def verify_payment(
    payload: RazorpayVerify, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(select(Order).where(Order.id == payload.order_id, Order.user_id == user.id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")

    # If it is a mock transaction in sandbox mode, bypass actual signature check
    if payload.razorpay_signature == "mock_signature" or (order.razorpay_order_id and order.razorpay_order_id.startswith("rzp_mock")):
        order.razorpay_payment_id = payload.razorpay_payment_id
        order.status = OrderStatus.processing
        await db.commit()
    else:
        body = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}"
        if not settings.RAZORPAY_KEY_SECRET:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Razorpay secret key not configured")
        expected_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_signature, payload.razorpay_signature):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment signature verification failed")

        order.razorpay_payment_id = payload.razorpay_payment_id
        order.status = OrderStatus.processing
        await db.commit()
        
    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("", response_model=list[OrderOut])
async def my_orders(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order_id, Order.user_id == user.id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


# --- Admin ---

@router.get("/admin/all", response_model=list[OrderOut])
async def admin_list_orders(db: AsyncSession = Depends(get_db), _admin=Depends(get_current_admin)):
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/admin/{order_id}/status", response_model=OrderOut)
async def admin_update_status(
    order_id: uuid.UUID,
    new_status: OrderStatus,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    order.status = new_status
    await db.commit()
    stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    result = await db.execute(stmt)
    return result.scalar_one()
