import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# Variant Schemas
class ProductVariantBase(BaseModel):
    name: str
    value: str
    price_delta: float = 0.0
    stock: int = 0


class ProductVariantOut(ProductVariantBase):
    id: uuid.UUID
    product_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# Category Schemas
class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None


class CategoryOut(CategoryCreate):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# Product Schemas
class ProductCreate(BaseModel):
    title: str
    slug: str
    description: str | None = None
    price: float
    compare_at_price: float | None = None
    category_id: uuid.UUID | None = None
    images: list[str] = []
    tags: list[str] = []
    colors: list[str] = []
    stock: int = 0
    is_featured: bool = False
    variants: list[ProductVariantBase] = []


class ProductUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    compare_at_price: float | None = None
    category_id: uuid.UUID | None = None
    images: list[str] | None = None
    tags: list[str] | None = None
    colors: list[str] | None = None
    stock: int | None = None
    is_active: bool | None = None
    is_featured: bool | None = None


class ProductOut(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str | None = None
    price: float
    compare_at_price: float | None = None
    category_id: uuid.UUID | None = None
    images: list[str]
    tags: list[str]
    colors: list[str]
    stock: int
    is_active: bool
    is_featured: bool
    variants: list[ProductVariantOut]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
