import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User


@pytest.mark.asyncio
async def test_review_requires_verified_purchase(
    client: AsyncClient,
    test_user: User,
    user_token: str,
    sample_product: Product,
    db_session: AsyncSession,
):
    """Users who have not purchased the product are rejected with 403 Forbidden."""
    headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Attempt to post review without purchase
    resp = await client.post(
        f"/api/products/{sample_product.id}/reviews",
        headers=headers,
        json={"rating": 5, "comment": "Looks nice, haven't bought though!"},
    )
    assert resp.status_code == 403
    assert "verified purchase" in resp.json()["detail"].lower()

    # 2. Simulate completed order for this product
    order = Order(
        order_number=f"KC{uuid.uuid4().hex[:6].upper()}",
        user_id=test_user.id,
        status=OrderStatus.paid,
        subtotal=650.0,
        total=650.0,
        shipping_address={"full_name": test_user.full_name, "city": "Pune", "phone": "9876543210"},
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add(
        OrderItem(
            order_id=order.id,
            product_id=sample_product.id,
            product_title=sample_product.title,
            unit_price=sample_product.price,
            quantity=1,
        )
    )
    await db_session.commit()

    # 3. Now attempt review -> should succeed
    success_resp = await client.post(
        f"/api/products/{sample_product.id}/reviews",
        headers=headers,
        json={"rating": 5, "comment": "Incredible stitch quality, love this lavender bouquet!"},
    )
    assert success_resp.status_code == 201
    rev_data = success_resp.json()
    assert rev_data["rating"] == 5
    assert rev_data["comment"] == "Incredible stitch quality, love this lavender bouquet!"

    # 4. Attempt duplicate review on same product -> should fail
    dup_resp = await client.post(
        f"/api/products/{sample_product.id}/reviews",
        headers=headers,
        json={"rating": 4, "comment": "Another review"},
    )
    assert dup_resp.status_code == 400
    assert "already reviewed" in dup_resp.json()["detail"].lower()
