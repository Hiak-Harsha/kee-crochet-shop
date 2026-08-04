import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.models.product import Category, Product, ProductVariant
from app.schemas.product import (
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from app.schemas.user import CustomRequestCreate, CustomRequestOut

router = APIRouter(tags=["products"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    return result.scalars().all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate, db: AsyncSession = Depends(get_db), _admin=Depends(get_current_admin)
):
    category = Category(**payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    category_slug: str | None = None,
    q: str | None = Query(None, description="search text over title"),
    min_price: float | None = None,
    max_price: float | None = None,
    featured: bool | None = None,
    limit: int = Query(24, le=100),
    offset: int = 0,
):
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.is_active == True)  # noqa: E712
    if category_slug:
        stmt = stmt.join(Category).where(Category.slug == category_slug)
    if q:
        stmt = stmt.where(Product.title.ilike(f"%{q}%"))
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if featured is not None:
        stmt = stmt.where(Product.is_featured == featured)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().unique().all()


@router.get("/products/{slug}", response_model=ProductOut)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.slug == slug, Product.is_active == True)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate, db: AsyncSession = Depends(get_db), _admin=Depends(get_current_admin)
):
    data = payload.model_dump(exclude={"variants"})
    product = Product(**data)
    db.add(product)
    await db.flush()
    for v in payload.variants:
        db.add(ProductVariant(product_id=product.id, **v.model_dump()))
    await db.commit()
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.id == product.id)
    result = await db.execute(stmt)
    return result.scalar_one()


@router.patch("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.id == product_id)
    result = await db.execute(stmt)
    return result.scalar_one()


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID, db: AsyncSession = Depends(get_db), _admin=Depends(get_current_admin)
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_active = False  # soft delete
    await db.commit()


@router.post("/products/custom-requests", response_model=CustomRequestOut, status_code=status.HTTP_201_CREATED)
async def create_custom_request(
    payload: CustomRequestCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    from app.models.user import CustomRequest
    req = CustomRequest(
        user_id=user.id,
        description=payload.description,
        color_palette=payload.color_palette
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/products/custom-requests/admin", response_model=list[CustomRequestOut])
async def list_custom_requests_admin(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    from app.models.user import CustomRequest
    result = await db.execute(select(CustomRequest))
    return result.scalars().all()
