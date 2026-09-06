from decimal import Decimal
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart, CartItem
from app.models.order import Coupon, CouponType
from app.models.product import Product, ProductVariant
from app.services.pricing_service import PricingService


@pytest.mark.asyncio
async def test_subtotal_and_standard_shipping():
    """Cart below ₹999 incurs ₹60 shipping fee."""
    p = Product(title="Rose Keychain", price=350.0, is_active=True)
    item = CartItem(product=p, quantity=2, gift_wrap=False)  # 2 * 350 = 700

    breakdown = await PricingService.calculate_cart_totals([item])
    assert breakdown.subtotal == Decimal("700.00")
    assert breakdown.shipping_fee == Decimal("60.00")
    assert breakdown.gift_wrap_fee == Decimal("0.00")
    assert breakdown.total == Decimal("760.00")


@pytest.mark.asyncio
async def test_free_shipping_threshold():
    """Cart at or above ₹999 has free shipping (₹0)."""
    p = Product(title="Sunflower Hamper", price=1000.0, is_active=True)
    item = CartItem(product=p, quantity=1, gift_wrap=False)

    breakdown = await PricingService.calculate_cart_totals([item])
    assert breakdown.subtotal == Decimal("1000.00")
    assert breakdown.shipping_fee == Decimal("0.00")
    assert breakdown.total == Decimal("1000.00")


@pytest.mark.asyncio
async def test_gift_wrapping_calculation():
    """Gift wrap is ₹50 per wrapped unit."""
    p = Product(title="Plush Bear", price=400.0, is_active=True)
    item1 = CartItem(product=p, quantity=2, gift_wrap=True)   # 2 * 50 = 100
    item2 = CartItem(product=p, quantity=1, gift_wrap=False)  # 0

    breakdown = await PricingService.calculate_cart_totals([item1, item2])
    assert breakdown.subtotal == Decimal("1200.00")  # 3 * 400
    assert breakdown.gift_wrap_fee == Decimal("100.00")
    assert breakdown.shipping_fee == Decimal("0.00")  # subtotal >= 999
    assert breakdown.total == Decimal("1300.00")


@pytest.mark.asyncio
async def test_percentage_coupon_with_maximum_cap(db_session: AsyncSession):
    """Percentage coupon correctly caps at maximum_discount."""
    coupon = Coupon(
        code="SAVE20CAP",
        type=CouponType.percentage,
        value=20.0,  # 20%
        minimum_order_value=500.0,
        maximum_discount=150.0,  # Max cap ₹150
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()

    p = Product(title="Large Blanket", price=1500.0, is_active=True)
    item = CartItem(product=p, quantity=1, gift_wrap=False)

    # 20% of 1500 is 300, but cap is 150
    breakdown = await PricingService.calculate_cart_totals(
        [item],
        coupon_code="SAVE20CAP",
        db=db_session,
    )
    assert breakdown.subtotal == Decimal("1500.00")
    assert breakdown.coupon_discount == Decimal("150.00")
    assert breakdown.total == Decimal("1350.00")


@pytest.mark.asyncio
async def test_expired_coupon_rejected(db_session: AsyncSession):
    """Expired coupon raises HTTPException."""
    expired_coupon = Coupon(
        code="EXPIRED50",
        type=CouponType.fixed,
        value=50.0,
        minimum_order_value=100.0,
        expires_at=datetime.now(timezone.utc) - timedelta(days=2),
        is_active=True,
    )
    db_session.add(expired_coupon)
    await db_session.commit()

    p = Product(title="Cup Cozy", price=200.0, is_active=True)
    item = CartItem(product=p, quantity=1, gift_wrap=False)

    with pytest.raises(HTTPException) as exc_info:
        await PricingService.calculate_cart_totals(
            [item],
            coupon_code="EXPIRED50",
            db=db_session,
        )
    assert exc_info.value.status_code == 400
    assert "expired" in exc_info.value.detail.lower()
