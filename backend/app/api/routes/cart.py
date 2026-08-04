import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartOut

router = APIRouter(prefix="/cart", tags=["cart"])


async def _get_or_create_cart(db: AsyncSession, user: User) -> Cart:
    stmt = (
        select(Cart)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.product)
            .selectinload(Product.variants)
        )
        .where(Cart.user_id == user.id)
    )
    result = await db.execute(stmt)
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
    return cart


def _serialize(cart: Cart) -> CartOut:
    out = CartOut.model_validate(cart)
    out.subtotal = sum(
        float(item.product.price) * item.quantity for item in cart.items if item.product
    )
    return out


@router.get("", response_model=CartOut)
async def get_cart(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    cart = await _get_or_create_cart(db, user)
    return _serialize(cart)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    payload: CartItemAdd, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = result.scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    cart = await _get_or_create_cart(db, user)
    existing = next(
        (i for i in cart.items if i.product_id == payload.product_id and i.variant_id == payload.variant_id),
        None,
    )
    
    new_qty = payload.quantity
    if existing:
        new_qty += existing.quantity
        
    if payload.variant_id:
        v_res = await db.execute(
            select(ProductVariant).where(ProductVariant.id == payload.variant_id, ProductVariant.product_id == product.id)
        )
        variant = v_res.scalar_one_or_none()
        if not variant:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product variant not found")
        if variant.stock < new_qty:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock. Available: {variant.stock}")
    else:
        if product.stock < new_qty:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock. Available: {product.stock}")

    if existing:
        existing.quantity = new_qty
    else:
        db.add(CartItem(cart_id=cart.id, **payload.model_dump()))
        
    await db.commit()
    cart = await _get_or_create_cart(db, user)
    return _serialize(cart)


@router.patch("/items/{item_id}", response_model=CartOut)
async def update_item(
    item_id: uuid.UUID,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cart = await _get_or_create_cart(db, user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
        
    if payload.quantity is not None:
        if item.variant_id:
            v_res = await db.execute(select(ProductVariant).where(ProductVariant.id == item.variant_id))
            variant = v_res.scalar_one_or_none()
            if not variant:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Variant not found")
            if variant.stock < payload.quantity:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock. Available: {variant.stock}")
        else:
            product_res = await db.execute(select(Product).where(Product.id == item.product_id))
            product = product_res.scalar_one_or_none()
            if not product:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
            if product.stock < payload.quantity:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock. Available: {product.stock}")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    cart = await _get_or_create_cart(db, user)
    return _serialize(cart)


@router.delete("/items/{item_id}", response_model=CartOut)
async def remove_item(
    item_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    cart = await _get_or_create_cart(db, user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
    await db.delete(item)
    await db.commit()
    cart = await _get_or_create_cart(db, user)
    return _serialize(cart)
