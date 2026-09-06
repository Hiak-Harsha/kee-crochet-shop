import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_user, get_current_user_optional
from app.core.database import get_db
from app.models.order import Coupon, CouponType, Order, OrderItem, OrderStatus
from app.models.product import Category, Product, ProductReview, ProductVariant
from app.models.user import CustomRequest, User
from app.schemas.order import (
    CouponCreate,
    CouponOut,
    CouponValidateRequest,
    CouponValidateResponse,
)
from app.schemas.product import (
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductOut,
    ProductReviewCreate,
    ProductReviewOut,
    ProductUpdate,
)
from app.schemas.user import CustomRequestCreate, CustomRequestOut
from app.services.pricing_service import PricingService
from app.services.storage_service import StorageService

router = APIRouter(tags=["products"])


# --- Categories ---

@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category))
    categories = result.scalars().all()

    out_categories = []
    for cat in categories:
        price_stmt = select(func.min(Product.price)).where(Product.category_id == cat.id, Product.is_active == True)
        price_res = await db.execute(price_stmt)
        min_price = price_res.scalar()

        cat_out = CategoryOut.model_validate(cat)
        cat_out.starting_price = float(min_price) if min_price is not None else None
        out_categories.append(cat_out)

    return out_categories


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    category = Category(**payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# --- Custom Requests (Registered before /{slug} to prevent path conflict) ---

@router.post("/products/custom-requests", response_model=CustomRequestOut, status_code=status.HTTP_201_CREATED)
async def create_custom_request(
    payload: CustomRequestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = CustomRequest(
        user_id=user.id,
        description=payload.description,
        color_palette=payload.color_palette,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/products/custom-requests/admin", response_model=list[CustomRequestOut])
async def list_custom_requests_admin(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(CustomRequest).order_by(CustomRequest.created_at.desc()))
    return result.scalars().all()


# --- Media Uploads (Sanitized with PIL, converted to WebP) ---

@router.post("/products/upload-image", response_model=dict)
async def upload_product_image(
    file: UploadFile = File(...),
    _admin: User = Depends(get_current_admin),
):
    """
    Sanitizes uploaded image using PIL, strips EXIF metadata, re-encodes to WebP,
    and uploads to Cloudinary, AWS S3, or local storage.
    """
    image_url = await StorageService.process_and_upload_image(file=file, folder="products")
    return {"url": image_url}


# --- Coupons Validation & Admin Management ---

@router.post("/coupons/validate", response_model=CouponValidateResponse)
async def validate_coupon(
    payload: CouponValidateRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """
    Authoritative server-side validation of discount coupon with limits and minimum order values.
    """
    clean_code = payload.code.strip().upper()
    subtotal_dec = Decimal(str(payload.subtotal))
    coupon = await PricingService.validate_coupon(
        code=clean_code,
        subtotal=subtotal_dec,
        user=user,
        db=db,
    )

    if coupon.type == CouponType.percentage:
        discount = (subtotal_dec * (Decimal(str(coupon.value)) / Decimal("100"))).quantize(Decimal("0.01"))
        if coupon.maximum_discount is not None:
            discount = min(discount, Decimal(str(coupon.maximum_discount)))
    elif coupon.type == CouponType.fixed:
        discount = min(Decimal(str(coupon.value)), subtotal_dec)
    elif coupon.type == CouponType.free_shipping:
        discount = Decimal("60.00") if subtotal_dec < Decimal("999.00") else Decimal("0.00")
    else:
        discount = Decimal("0.00")

    return CouponValidateResponse(
        code=coupon.code,
        type=coupon.type.value if hasattr(coupon.type, "value") else str(coupon.type),
        value=float(coupon.value),
        discount_amount=float(discount),
        description=coupon.description,
    )


@router.get("/admin/coupons", response_model=list[CouponOut])
async def admin_list_coupons(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    stmt = select(Coupon).order_by(Coupon.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/admin/coupons", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
async def admin_create_coupon(
    payload: CouponCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    clean_code = payload.code.strip().upper()
    res = await db.execute(select(Coupon).where(Coupon.code == clean_code))
    if res.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Coupon code '{clean_code}' already exists")

    coupon = Coupon(
        code=clean_code,
        description=payload.description,
        type=CouponType(payload.type),
        value=payload.value,
        minimum_order_value=payload.minimum_order_value,
        maximum_discount=payload.maximum_discount,
        usage_limit=payload.usage_limit,
        per_customer_limit=payload.per_customer_limit,
        start_at=payload.start_at,
        expires_at=payload.expires_at,
        is_active=payload.is_active,
    )
    db.add(coupon)
    await db.commit()
    await db.refresh(coupon)
    return coupon


@router.patch("/admin/coupons/{coupon_id}", response_model=CouponOut)
async def admin_update_coupon(
    coupon_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    res = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = res.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Coupon not found")

    for k, v in payload.items():
        if hasattr(coupon, k):
            if k == "type":
                v = CouponType(v)
            setattr(coupon, k, v)

    await db.commit()
    await db.refresh(coupon)
    return coupon


# --- Products Catalog ---

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
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.is_active == True)
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
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
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
    _admin: User = Depends(get_current_admin),
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
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    product.is_active = False  # Soft delete
    await db.commit()


# --- Product Reviews (Enforces Verified Purchases) ---

@router.get("/products/{product_id}/reviews", response_model=list[ProductReviewOut])
async def list_product_reviews(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ProductReview)
        .options(selectinload(ProductReview.user))
        .where(ProductReview.product_id == product_id)
        .order_by(ProductReview.created_at.desc())
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    out_reviews = []
    for r in reviews:
        rout = ProductReviewOut.model_validate(r)
        rout.user_name = r.user.full_name if r.user else "Anonymous"
        out_reviews.append(rout)
    return out_reviews


@router.post("/products/{product_id}/reviews", response_model=ProductReviewOut, status_code=status.HTTP_201_CREATED)
async def create_product_review(
    product_id: uuid.UUID,
    payload: ProductReviewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 1. Product must exist
    product_res = await db.execute(select(Product).where(Product.id == product_id))
    product = product_res.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    # 2. Rating bounds check
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rating must be between 1 and 5 stars")

    # 3. Verified Purchase Enforcement: User must have an order containing this product
    purchase_stmt = (
        select(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.user_id == user.id,
            OrderItem.product_id == product_id,
            Order.status.in_([
                OrderStatus.paid,
                OrderStatus.processing,
                OrderStatus.packed,
                OrderStatus.shipped,
                OrderStatus.delivered,
                OrderStatus.completed,
            ])
        )
    )
    purchase_res = await db.execute(purchase_stmt)
    if not purchase_res.first():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Verified purchase required: You can only review products from a paid or completed order."
        )

    # 4. Duplicate review check
    dup_res = await db.execute(
        select(ProductReview).where(ProductReview.product_id == product_id, ProductReview.user_id == user.id)
    )
    if dup_res.scalar_one_or_none():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You have already reviewed this product.")

    review = ProductReview(
        product_id=product_id,
        user_id=user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    rout = ProductReviewOut.model_validate(review)
    rout.user_name = user.full_name
    return rout
