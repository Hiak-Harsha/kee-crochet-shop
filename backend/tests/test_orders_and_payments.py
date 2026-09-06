import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart, CartItem
from app.models.order import (
    InventoryReservation,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    ReservationStatus,
)
from app.models.product import Product
from app.models.user import User


@pytest.mark.asyncio
async def test_order_creation_reserves_stock(
    client: AsyncClient,
    test_user: User,
    user_token: str,
    sample_product: Product,
    db_session: AsyncSession,
):
    """Creating an order locks inventory and reserves stock with 15-min TTL."""
    # 1. Add item to cart
    headers = {"Authorization": f"Bearer {user_token}"}
    add_resp = await client.post(
        "/api/cart/items",
        headers=headers,
        json={"product_id": str(sample_product.id), "quantity": 2, "gift_wrap": True},
    )
    assert add_resp.status_code == 201

    # 2. Place order
    order_payload = {
        "shipping_address": {
            "full_name": "Priya Sharma",
            "address_line1": "Flat 101, Sun City",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001",
            "country": "India",
            "phone": "9876543210",
        },
        "delivery_slot": "standard",
    }
    order_resp = await client.post("/api/orders", headers=headers, json=order_payload)
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    order_id = uuid.UUID(order_data["id"])

    # 3. Check that order is in pending_payment
    assert order_data["status"] == "pending_payment"
    assert order_data["gift_wrap_fee"] == 100.0  # 2 * 50

    # 4. Check that inventory was reserved
    stmt = select(InventoryReservation).where(
        InventoryReservation.order_id == order_id,
        InventoryReservation.status == ReservationStatus.ACTIVE,
    )
    res = await db_session.execute(stmt)
    reservations = res.scalars().all()
    assert len(reservations) == 1
    assert reservations[0].quantity == 2


@pytest.mark.asyncio
async def test_payment_verification_commits_reservations(
    client: AsyncClient,
    test_user: User,
    user_token: str,
    sample_product: Product,
    db_session: AsyncSession,
):
    """Successful payment verification transitions order to paid and commits reservation."""
    headers = {"Authorization": f"Bearer {user_token}"}

    # Add item & create order
    await client.post(
        "/api/cart/items",
        headers=headers,
        json={"product_id": str(sample_product.id), "quantity": 1},
    )
    order_resp = await client.post(
        "/api/orders",
        headers=headers,
        json={
            "shipping_address": {
                "full_name": "Priya Sharma",
                "address_line1": "Flat 101",
                "city": "Pune",
                "state": "Maharashtra",
                "postal_code": "411001",
                "phone": "9876543210",
            }
        },
    )
    order_data = order_resp.json()
    order_id = uuid.UUID(order_data["id"])
    rzp_order_id = order_data["razorpay_order_id"]

    # Verify payment (mock verification in test environment)
    verify_resp = await client.post(
        "/api/orders/verify-payment",
        headers=headers,
        json={
            "order_id": str(order_id),
            "razorpay_order_id": rzp_order_id,
            "razorpay_payment_id": f"pay_test_{uuid.uuid4().hex[:8]}",
            "razorpay_signature": "mock_signature",
        },
    )
    assert verify_resp.status_code == 200
    updated_order = verify_resp.json()
    assert updated_order["status"] == "paid"

    # Verify reservation committed
    stmt = select(InventoryReservation).where(
        InventoryReservation.order_id == order_id,
        InventoryReservation.status == ReservationStatus.COMMITTED,
    )
    res = await db_session.execute(stmt)
    committed = res.scalars().all()
    assert len(committed) == 1


@pytest.mark.asyncio
async def test_order_cancellation_releases_stock(
    client: AsyncClient,
    test_user: User,
    user_token: str,
    sample_product: Product,
    db_session: AsyncSession,
):
    """Cancelling an unpaid order releases reservation and restores available stock."""
    headers = {"Authorization": f"Bearer {user_token}"}

    initial_stock = sample_product.stock

    await client.post(
        "/api/cart/items",
        headers=headers,
        json={"product_id": str(sample_product.id), "quantity": 1},
    )
    order_resp = await client.post(
        "/api/orders",
        headers=headers,
        json={
            "shipping_address": {
                "full_name": "Priya Sharma",
                "address_line1": "Flat 101",
                "city": "Pune",
                "state": "Maharashtra",
                "postal_code": "411001",
                "phone": "9876543210",
            }
        },
    )
    order_id = order_resp.json()["id"]

    # Cancel order
    cancel_resp = await client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    cancelled_data = cancel_resp.json()
    assert cancelled_data["status"] == "cancelled"

    # Verify stock restored
    await db_session.refresh(sample_product)
    assert sample_product.stock == initial_stock
