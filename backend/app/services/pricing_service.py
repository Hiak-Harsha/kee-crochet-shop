from decimal import Decimal, ROUND_HALF_UP
import logging
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.order import Coupon, CouponType, CouponRedemption
from app.models.user import User

logger = logging.getLogger(__name__)

GIFT_WRAP_UNIT_FEE = Decimal("50.00")
FREE_SHIPPING_THRESHOLD = Decimal("999.00")
STANDARD_SHIPPING_FEE = Decimal("60.00")


@dataclass
class PricingBreakdown:
    subtotal: Decimal
    item_discounts: Decimal
    coupon_discount: Decimal
    gift_wrap_fee: Decimal
    shipping_fee: Decimal
    tax: Decimal
    total: Decimal
    coupon_id: uuid.UUID | None = None
    coupon_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subtotal": float(self.subtotal),
            "item_discounts": float(self.item_discounts),
            "coupon_discount": float(self.coupon_discount),
            "gift_wrap_fee": float(self.gift_wrap_fee),
            "shipping_fee": float(self.shipping_fee),
            "tax": float(self.tax),
            "total": float(self.total),
            "coupon_id": str(self.coupon_id) if self.coupon_id else None,
            "coupon_code": self.coupon_code,
        }


class PricingService:
    @staticmethod
    def _quantize(val: Decimal) -> Decimal:
        return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    async def calculate_cart_totals(
        cls,
        cart_items: list[CartItem],
        user: User | None = None,
        coupon_code: str | None = None,
        db: AsyncSession | None = None,
    ) -> PricingBreakdown:
        """
        Authoritative server-side financial calculation for cart/checkout.
        Uses Decimal precision for all operations.
        """
        subtotal = Decimal("0.00")
        gift_wrap_count = 0

        for item in cart_items:
            product = item.product
            if not product or not product.is_active:
                continue

            # Variant price takes precedence if explicitly set, else base + price_delta
            if item.variant:
                if item.variant.price is not None:
                    unit_price = Decimal(str(item.variant.price))
                else:
                    unit_price = Decimal(str(product.price)) + Decimal(str(item.variant.price_delta or 0))
            else:
                unit_price = Decimal(str(product.price))

            item_total = unit_price * Decimal(str(item.quantity))
            subtotal += item_total

            if item.gift_wrap:
                gift_wrap_count += item.quantity

        subtotal = cls._quantize(subtotal)
        
        # Dynamic Store Settings lookup with graceful defaults
        gift_unit_fee = GIFT_WRAP_UNIT_FEE
        free_threshold = FREE_SHIPPING_THRESHOLD
        standard_fee = STANDARD_SHIPPING_FEE

        if db:
            try:
                from app.models.user import StoreSetting
                st_res = await db.execute(select(StoreSetting).where(StoreSetting.key == "shipping"))
                st_rec = st_res.scalar_one_or_none()
                if st_rec and isinstance(st_rec.value, dict):
                    if "gift_wrap_unit_fee" in st_rec.value:
                        gift_unit_fee = Decimal(str(st_rec.value["gift_wrap_unit_fee"]))
                    if "free_threshold" in st_rec.value:
                        free_threshold = Decimal(str(st_rec.value["free_threshold"]))
                    if "standard_fee" in st_rec.value:
                        standard_fee = Decimal(str(st_rec.value["standard_fee"]))
            except Exception as e:
                logger.warning(f"Could not load store settings, using defaults: {e}")

        gift_wrap_fee = cls._quantize(gift_unit_fee * Decimal(str(gift_wrap_count)))
        
        # Shipping Calculation
        if subtotal >= free_threshold or subtotal == Decimal("0.00"):
            shipping_fee = Decimal("0.00")
        else:
            shipping_fee = standard_fee

        item_discounts = Decimal("0.00")
        coupon_discount = Decimal("0.00")
        applied_coupon_id: uuid.UUID | None = None
        applied_coupon_code: str | None = None

        # Coupon Calculation
        if coupon_code and db:
            clean_code = coupon_code.strip().upper()
            coupon = await cls.validate_coupon(clean_code, subtotal, user, db)
            if coupon:
                applied_coupon_id = coupon.id
                applied_coupon_code = coupon.code

                if coupon.type == CouponType.percentage:
                    discount = (subtotal * (Decimal(str(coupon.value)) / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if coupon.maximum_discount is not None:
                        max_disc = Decimal(str(coupon.maximum_discount))
                        if discount > max_disc:
                            discount = max_disc
                    coupon_discount = discount
                elif coupon.type == CouponType.fixed:
                    coupon_discount = min(Decimal(str(coupon.value)), subtotal)
                elif coupon.type == CouponType.free_shipping:
                    coupon_discount = shipping_fee

        tax = Decimal("0.00")  # Included in price per Indian consumer standard (MRP)
        
        total = subtotal + gift_wrap_fee + shipping_fee - coupon_discount - item_discounts
        if total < Decimal("0.00"):
            total = Decimal("0.00")
        total = cls._quantize(total)

        return PricingBreakdown(
            subtotal=subtotal,
            item_discounts=item_discounts,
            coupon_discount=coupon_discount,
            gift_wrap_fee=gift_wrap_fee,
            shipping_fee=shipping_fee,
            tax=tax,
            total=total,
            coupon_id=applied_coupon_id,
            coupon_code=applied_coupon_code,
        )

    @classmethod
    async def validate_coupon(
        cls,
        code: str,
        subtotal: Decimal,
        user: User | None,
        db: AsyncSession,
    ) -> Coupon:
        """
        Validate coupon against database rules, limits, and expiration.
        """
        stmt = select(Coupon).where(Coupon.code == code, Coupon.is_active == True)
        res = await db.execute(stmt)
        coupon = res.scalar_one_or_none()

        if not coupon:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Coupon '{code}' is invalid or inactive")

        now = datetime.now(timezone.utc)
        if coupon.start_at and coupon.start_at.replace(tzinfo=timezone.utc) > now:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Coupon '{code}' is not yet active")

        if coupon.expires_at and coupon.expires_at.replace(tzinfo=timezone.utc) < now:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Coupon '{code}' has expired")

        if subtotal < Decimal(str(coupon.minimum_order_value)):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Coupon '{code}' requires a minimum order value of ₹{coupon.minimum_order_value}"
            )

        if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Coupon '{code}' has reached its maximum global usage limit")

        if user and coupon.per_customer_limit > 0:
            redemptions_stmt = select(CouponRedemption).where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.user_id == user.id
            )
            r_res = await db.execute(redemptions_stmt)
            customer_uses = len(r_res.scalars().all())
            if customer_uses >= coupon.per_customer_limit:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"You have already used coupon '{code}' the maximum allowed number of times ({coupon.per_customer_limit})"
                )

        return coupon
