import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ShippingAddress(BaseModel):
    full_name: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "India"
    phone: str


class OrderCreate(BaseModel):
    shipping_address: ShippingAddress
    coupon_code: str | None = None
    delivery_slot: str | None = None
    customer_notes: str | None = None


class RazorpayVerify(BaseModel):
    order_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class OrderItemOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    product_title: str
    variant_name: str | None = None
    sku: str | None = None
    unit_price: float
    quantity: int
    total_price: float = 0.0
    gift_wrap: bool = False
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    user_id: uuid.UUID
    status: str
    subtotal: float
    item_discounts: float = 0.0
    coupon_discount: float = 0.0
    discount: float = 0.0
    gift_wrap_fee: float = 0.0
    shipping_fee: float = 0.0
    tax: float = 0.0
    total: float
    shipping_address: ShippingAddress
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    coupon_code: str | None = None
    delivery_slot: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []

    model_config = ConfigDict(from_attributes=True)


class CouponValidateRequest(BaseModel):
    code: str
    subtotal: float = 0.0


class CouponValidateResponse(BaseModel):
    code: str
    type: str
    value: float
    discount_amount: float
    description: str | None = None


class CouponCreate(BaseModel):
    code: str
    description: str | None = None
    type: str = "percentage"
    value: float
    minimum_order_value: float = 0.0
    maximum_discount: float | None = None
    usage_limit: int | None = None
    per_customer_limit: int = 1
    start_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool = True


class CouponOut(BaseModel):
    id: uuid.UUID
    code: str
    description: str | None = None
    type: str
    value: float
    minimum_order_value: float
    maximum_discount: float | None = None
    usage_limit: int | None = None
    times_used: int
    per_customer_limit: int
    is_active: bool
    start_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
