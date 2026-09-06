import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product, ProductReview
from app.models.user import User


@pytest.mark.asyncio
async def test_admin_customers_directory(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_admin: User,
    admin_token: str,
    user_token: str,
    sample_product: Product,
):
    # Customer makes an order
    order = Order(
        order_number="KC_CUST_TEST",
        user_id=test_user.id,
        status=OrderStatus.completed,
        subtotal=650.0,
        item_discounts=0.0,
        coupon_discount=0.0,
        gift_wrap_fee=50.0,
        shipping_fee=60.0,
        tax=0.0,
        total=760.0,
        shipping_address={"full_name": test_user.full_name, "phone": test_user.phone or "9876543210", "city": "Bangalore"},
    )
    db_session.add(order)
    await db_session.commit()

    # 1. Non-admin request must be rejected with 403
    forbidden_res = await client.get("/api/admin/customers", headers={"Authorization": f"Bearer {user_token}"})
    assert forbidden_res.status_code == 403

    # 2. Admin request succeeds and returns customer stats
    res = await client.get("/api/admin/customers", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    customers = res.json()
    assert len(customers) >= 1
    cust = next((c for c in customers if c["id"] == str(test_user.id)), None)
    assert cust is not None
    assert cust["total_orders"] >= 1
    assert cust["total_spend"] >= 760.0
    assert cust["full_name"] == test_user.full_name


@pytest.mark.asyncio
async def test_admin_analytics_aggregates(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    admin_token: str,
    sample_product: Product,
):
    # Create order with items
    order = Order(
        order_number="KC_ANALYTICS_TEST",
        user_id=test_user.id,
        status=OrderStatus.delivered,
        subtotal=1300.0,
        item_discounts=0.0,
        coupon_discount=100.0,
        gift_wrap_fee=100.0,
        shipping_fee=0.0,
        tax=0.0,
        total=1300.0,
        shipping_address={"full_name": test_user.full_name, "city": "Mumbai"},
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=sample_product.id,
        product_title=sample_product.title,
        unit_price=650.0,
        quantity=2,
        gift_wrap=True,
    )
    db_session.add(item)
    await db_session.commit()

    res = await client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["gross_revenue"] >= 1300.0
    assert data["total_orders"] >= 1
    assert data["average_order_value"] > 0
    assert data["customer_count"] >= 1
    assert len(data["top_products"]) >= 1
    assert data["top_products"][0]["title"] == sample_product.title


@pytest.mark.asyncio
async def test_admin_store_settings_lifecycle(
    client: AsyncClient,
    admin_token: str,
):
    # 1. Fetch settings
    res = await client.get("/api/admin/settings", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200

    # 2. Update general setting
    new_general = {
        "store_name": "Kee Crochet Luxury Studio",
        "support_email": "hello@keecrochet.com",
        "currency": "INR",
    }
    update_res = await client.put(
        "/api/admin/settings",
        json={"key": "general", "value": new_general, "description": "Updated branding config"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["setting"]["store_name"] == "Kee Crochet Luxury Studio"

    # 3. Check audit log is created
    logs_res = await client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert any(l["action"] == "update_setting" for l in logs)


@pytest.mark.asyncio
async def test_admin_review_moderation(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    admin_token: str,
    sample_product: Product,
):
    # Insert review
    review = ProductReview(
        product_id=sample_product.id,
        user_id=test_user.id,
        rating=5,
        comment="Incredible work, lovely stitch quality!",
        is_approved=False,
        is_flagged=False,
    )
    db_session.add(review)
    await db_session.commit()

    # Moderate: Approve review
    res = await client.patch(
        f"/api/admin/reviews/{review.id}/moderate",
        json={"is_approved": True, "is_flagged": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 200

    await db_session.refresh(review)
    assert review.is_approved is True
