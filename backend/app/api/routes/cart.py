import uuid
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.cart import (
    CartItemAdd,
    CartItemOut,
    CartItemUpdate,
    CartMergeRequest,
    CartOut,
    CartQuoteRequest,
    CartQuoteResponse,
)
from app.schemas.product import ProductOut
from app.services.pricing_service import PricingBreakdown, PricingService

router = APIRouter(prefix="/cart", tags=["cart"])


def _cart_load_options():
    return [
        selectinload(Cart.items).selectinload(CartItem.product).selectinload(Product.variants),
        selectinload(Cart.items).selectinload(CartItem.variant),
    ]


async def _get_or_create_cart(
    db: AsyncSession,
    user: User | None = None,
    session_token: str | None = None,
) -> tuple[Cart, str | None]:
    """
    Retrieve or create a cart for an authenticated user or anonymous guest.
    Returns (cart, active_session_token).
    """
    if user:
        stmt = select(Cart).options(*_cart_load_options()).where(Cart.user_id == user.id)
        result = await db.execute(stmt)
        cart = result.scalar_one_or_none()
        if not cart:
            cart = Cart(user_id=user.id)
            db.add(cart)
            await db.commit()
            # Re-query with eager loading
            res = await db.execute(select(Cart).options(*_cart_load_options()).where(Cart.id == cart.id))
            cart = res.scalar_one()
        return cart, None

    # Guest cart flow
    if session_token:
        stmt = select(Cart).options(*_cart_load_options()).where(Cart.session_token == session_token)
        result = await db.execute(stmt)
        cart = result.scalar_one_or_none()
        if cart:
            return cart, session_token

    # Create new guest cart
    new_token = f"gst_{uuid.uuid4().hex}"
    cart = Cart(session_token=new_token)
    db.add(cart)
    await db.commit()
    res = await db.execute(select(Cart).options(*_cart_load_options()).where(Cart.id == cart.id))
    return res.scalar_one(), new_token


async def _serialize_cart(
    cart: Cart,
    user: User | None = None,
    breakdown: PricingBreakdown | None = None,
    db: AsyncSession | None = None,
) -> CartOut:
    """Format cart with accurate server-side price calculations."""
    if not breakdown:
        breakdown = await PricingService.calculate_cart_totals(cart.items, user=user, db=db)

    item_outs: list[CartItemOut] = []
    for item in cart.items:
        p = item.product
        if not p:
            continue

        if item.variant:
            if item.variant.price is not None:
                unit_price = float(item.variant.price)
            else:
                unit_price = float(p.price) + float(item.variant.price_delta or 0.0)
        else:
            unit_price = float(p.price)

        total_price = unit_price * item.quantity

        item_outs.append(
            CartItemOut(
                id=item.id,
                cart_id=item.cart_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=item.quantity,
                gift_wrap=item.gift_wrap,
                note=item.note,
                product=ProductOut.model_validate(p),
                unit_price=unit_price,
                total_price=total_price,
            )
        )

    return CartOut(
        id=cart.id,
        user_id=cart.user_id,
        session_token=cart.session_token,
        items=item_outs,
        subtotal=float(breakdown.subtotal),
        gift_wrap_fee=float(breakdown.gift_wrap_fee),
        shipping_fee=float(breakdown.shipping_fee),
        discount=float(breakdown.coupon_discount + breakdown.item_discounts),
        total=float(breakdown.total),
    )


@router.get("", response_model=CartOut)
async def get_cart(
    response: Response,
    x_session_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    cart, new_token = await _get_or_create_cart(db, user, x_session_token)
    if new_token:
        response.headers["X-Session-Token"] = new_token
        response.set_cookie("kc_cart_token", new_token, max_age=86400 * 30, httponly=True, samesite="lax")
    return await _serialize_cart(cart, user=user, db=db)


@router.post("/items", response_model=CartOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    payload: CartItemAdd,
    response: Response,
    x_session_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    # Validate product
    result = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = result.scalar_one_or_none()
    if not product or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found or inactive")

    cart, new_token = await _get_or_create_cart(db, user, x_session_token)
    if new_token:
        response.headers["X-Session-Token"] = new_token
        response.set_cookie("kc_cart_token", new_token, max_age=86400 * 30, httponly=True, samesite="lax")

    existing = next(
        (i for i in cart.items if i.product_id == payload.product_id and i.variant_id == payload.variant_id),
        None,
    )

    new_qty = payload.quantity
    if existing:
        new_qty += existing.quantity

    # Stock availability verification
    if payload.variant_id:
        v_res = await db.execute(
            select(ProductVariant).where(ProductVariant.id == payload.variant_id, ProductVariant.product_id == product.id)
        )
        variant = v_res.scalar_one_or_none()
        if not variant or not variant.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Product variant not found or inactive")
        if variant.stock < new_qty:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock. Available: {variant.stock}")
    else:
        if product.stock < new_qty:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Insufficient stock. Available: {product.stock}")

    if existing:
        existing.quantity = new_qty
        if payload.gift_wrap:
            existing.gift_wrap = payload.gift_wrap
        if payload.note:
            existing.note = payload.note
    else:
        db.add(CartItem(cart_id=cart.id, **payload.model_dump()))

    await db.commit()

    res = await db.execute(select(Cart).options(*_cart_load_options()).where(Cart.id == cart.id))
    fresh_cart = res.scalar_one()
    return await _serialize_cart(fresh_cart, user=user, db=db)


@router.patch("/items/{item_id}", response_model=CartOut)
async def update_item(
    item_id: uuid.UUID,
    payload: CartItemUpdate,
    x_session_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    cart, _ = await _get_or_create_cart(db, user, x_session_token)
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
    res = await db.execute(select(Cart).options(*_cart_load_options()).where(Cart.id == cart.id))
    fresh_cart = res.scalar_one()
    return await _serialize_cart(fresh_cart, user=user, db=db)


@router.delete("/items/{item_id}", response_model=CartOut)
async def remove_item(
    item_id: uuid.UUID,
    x_session_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    cart, _ = await _get_or_create_cart(db, user, x_session_token)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")

    await db.delete(item)
    await db.commit()

    res = await db.execute(select(Cart).options(*_cart_load_options()).where(Cart.id == cart.id))
    fresh_cart = res.scalar_one()
    return await _serialize_cart(fresh_cart, user=user, db=db)


@router.post("/quote", response_model=CartQuoteResponse)
async def get_cart_quote(
    payload: CartQuoteRequest,
    x_session_token: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """
    Get live server-authoritative financial calculation for cart items with optional coupon.
    """
    cart, _ = await _get_or_create_cart(db, user, x_session_token)
    breakdown = await PricingService.calculate_cart_totals(
        cart.items,
        user=user,
        coupon_code=payload.coupon_code,
        db=db,
    )
    return CartQuoteResponse(
        subtotal=float(breakdown.subtotal),
        item_discounts=float(breakdown.item_discounts),
        coupon_discount=float(breakdown.coupon_discount),
        gift_wrap_fee=float(breakdown.gift_wrap_fee),
        shipping_fee=float(breakdown.shipping_fee),
        tax=float(breakdown.tax),
        total=float(breakdown.total),
        coupon_code=breakdown.coupon_code,
    )


@router.post("/merge", response_model=CartOut)
async def merge_guest_cart(
    payload: CartMergeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Merge items from an anonymous guest cart into the authenticated user's cart upon login.
    """
    if not payload.guest_session_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Guest session token is required")

    # Fetch guest cart
    stmt = select(Cart).options(*_cart_load_options()).where(Cart.session_token == payload.guest_session_token)
    res = await db.execute(stmt)
    guest_cart = res.scalar_one_or_none()

    if not guest_cart or not guest_cart.items:
        # Nothing to merge; return current user cart
        user_cart, _ = await _get_or_create_cart(db, user)
        return await _serialize_cart(user_cart, user=user, db=db)

    # Fetch or create user's cart
    user_cart, _ = await _get_or_create_cart(db, user)

    for g_item in guest_cart.items:
        u_existing = next(
            (
                u for u in user_cart.items
                if u.product_id == g_item.product_id and u.variant_id == g_item.variant_id
            ),
            None,
        )
        if u_existing:
            u_existing.quantity += g_item.quantity
            if g_item.gift_wrap:
                u_existing.gift_wrap = True
            if g_item.note and not u_existing.note:
                u_existing.note = g_item.note
        else:
            db.add(
                CartItem(
                    cart_id=user_cart.id,
                    product_id=g_item.product_id,
                    variant_id=g_item.variant_id,
                    quantity=g_item.quantity,
                    gift_wrap=g_item.gift_wrap,
                    note=g_item.note,
                )
            )

    # Delete the guest cart
    await db.delete(guest_cart)
    await db.commit()

    res = await db.execute(select(Cart).options(*_cart_load_options()).where(Cart.id == user_cart.id))
    fresh_user_cart = res.scalar_one()
    return await _serialize_cart(fresh_user_cart, user=user, db=db)
