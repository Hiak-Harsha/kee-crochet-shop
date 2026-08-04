import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


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
    unit_price: float
    quantity: int

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: uuid.UUID
    order_number: str
    user_id: uuid.UUID
    status: str
    subtotal: float
    discount: float
    shipping_fee: float
    total: float
    shipping_address: ShippingAddress
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    coupon_code: str | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []

    model_config = ConfigDict(from_attributes=True)
