import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.product import ProductOut


class CartItemAdd(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(default=1, gt=0)
    gift_wrap: bool = False
    note: str | None = None


class CartItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    gift_wrap: bool | None = None
    note: str | None = None


class CartItemOut(BaseModel):
    id: uuid.UUID
    cart_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int
    gift_wrap: bool = False
    note: str | None = None
    product: ProductOut | None = None
    unit_price: float = 0.0
    total_price: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CartOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    session_token: str | None = None
    items: list[CartItemOut] = []
    subtotal: float = 0.0
    gift_wrap_fee: float = 0.0
    shipping_fee: float = 0.0
    discount: float = 0.0
    total: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CartQuoteRequest(BaseModel):
    coupon_code: str | None = None


class CartQuoteResponse(BaseModel):
    subtotal: float
    item_discounts: float
    coupon_discount: float
    gift_wrap_fee: float
    shipping_fee: float
    tax: float
    total: float
    coupon_code: str | None = None


class CartMergeRequest(BaseModel):
    guest_session_token: str
