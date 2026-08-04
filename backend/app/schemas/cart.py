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
    gift_wrap: bool
    note: str | None = None
    product: ProductOut | None = None

    model_config = ConfigDict(from_attributes=True)


class CartOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    items: list[CartItemOut] = []
    subtotal: float = 0.0

    model_config = ConfigDict(from_attributes=True)
