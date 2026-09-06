import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin
from app.core.audit import log_audit_event
from app.core.database import get_db
from app.models.order import (
    Coupon,
    CouponRedemption,
    InventoryReservation,
    InventoryTransaction,
    Order,
    OrderItem,
    OrderStatus,
    ReservationStatus,
)
from app.models.product import Category, Product, ProductReview, ProductVariant
from app.models.user import AuditLog, StorePolicy, StoreSetting, User, UserRole

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Schemas ---

class CustomerRecordOut(BaseModel):
    id: str
    email: str | None
    phone: str | None
    full_name: str | None
    total_orders: int
    total_spend: float
    last_order_date: str | None
    account_date: str
    is_active: bool


class TopProductRecord(BaseModel):
    product_id: str
    title: str
    units_sold: int
    revenue: float


class AnalyticsOut(BaseModel):
    gross_revenue: float
    net_revenue: float
    refunds: float
    total_orders: int
    average_order_value: float
    customer_count: int
    coupon_usage_count: int
    total_coupon_discounts: float
    gift_wrap_count: int
    top_products: list[TopProductRecord]


class SettingUpdatePayload(BaseModel):
    key: str
    value: dict[str, Any]
    description: str | None = None


class ReviewModeratePayload(BaseModel):
    is_approved: bool | None = None
    is_flagged: bool | None = None


# --- Endpoints ---

@router.get("/customers", response_model=list[CustomerRecordOut])
async def list_customers(
    q: str | None = Query(None, description="Search by name, email, or phone"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """
    Authoritative server-side customer directory aggregated from users and orders.
    """
    stmt = (
        select(
            User.id,
            User.email,
            User.phone,
            User.full_name,
            User.created_at,
            User.is_active,
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(Order.total), 0.0).label("total_spend"),
            func.max(Order.created_at).label("last_order_date"),
        )
        .outerjoin(
            Order,
            (Order.user_id == User.id) & Order.status.in_([
                OrderStatus.paid,
                OrderStatus.processing,
                OrderStatus.packed,
                OrderStatus.shipped,
                OrderStatus.delivered,
                OrderStatus.completed,
            ])
        )
        .where(User.role == UserRole.customer)
        .group_by(User.id)
    )

    if q:
        search_pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            User.full_name.ilike(search_pattern) |
            User.email.ilike(search_pattern) |
            User.phone.ilike(search_pattern)
        )

    stmt = stmt.order_by(desc("total_spend")).offset(offset).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        CustomerRecordOut(
            id=str(r[0]),
            email=r[1],
            phone=r[2],
            full_name=r[3] or "Customer",
            account_date=r[4].strftime("%b %d, %Y") if r[4] else "",
            is_active=r[5],
            total_orders=int(r[6] or 0),
            total_spend=float(r[7] or 0.0),
            last_order_date=r[8].strftime("%b %d, %Y") if r[8] else None,
        )
        for r in rows
    ]


@router.get("/analytics", response_model=AnalyticsOut)
async def get_store_analytics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """
    Full store financial and volume analytics aggregated server-side via SQL.
    """
    completed_statuses = [
        OrderStatus.paid,
        OrderStatus.processing,
        OrderStatus.packed,
        OrderStatus.shipped,
        OrderStatus.delivered,
        OrderStatus.completed,
    ]

    # Gross revenue
    gross_stmt = select(func.coalesce(func.sum(Order.total), 0.0)).where(Order.status.in_(completed_statuses))
    gross_revenue = float((await db.execute(gross_stmt)).scalar() or 0.0)

    # Net revenue (subtotal minus discounts)
    net_stmt = select(func.coalesce(func.sum(Order.subtotal - Order.coupon_discount - Order.item_discounts), 0.0)).where(
        Order.status.in_(completed_statuses)
    )
    net_revenue = float((await db.execute(net_stmt)).scalar() or 0.0)

    # Refunds
    refund_stmt = select(func.coalesce(func.sum(Order.total), 0.0)).where(Order.status == OrderStatus.refunded)
    refunds = float((await db.execute(refund_stmt)).scalar() or 0.0)

    # Order count
    count_stmt = select(func.count(Order.id)).where(Order.status.in_(completed_statuses))
    total_orders = int((await db.execute(count_stmt)).scalar() or 0)

    # Average Order Value
    aov = (gross_revenue / total_orders) if total_orders > 0 else 0.0

    # Customer count
    cust_stmt = select(func.count(User.id)).where(User.role == UserRole.customer)
    customer_count = int((await db.execute(cust_stmt)).scalar() or 0)

    # Coupon redemptions
    coup_stmt = select(
        func.count(CouponRedemption.id),
        func.coalesce(func.sum(CouponRedemption.discount_amount), 0.0),
    )
    c_res = (await db.execute(coup_stmt)).one()
    coupon_count = int(c_res[0] or 0)
    coupon_discounts = float(c_res[1] or 0.0)

    # Gift wrap count
    gw_stmt = select(func.count(OrderItem.id)).where(OrderItem.gift_wrap == True)
    gift_wrap_count = int((await db.execute(gw_stmt)).scalar() or 0)

    # Top products by sales
    top_stmt = (
        select(
            OrderItem.product_id,
            OrderItem.product_title,
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_(completed_statuses))
        .group_by(OrderItem.product_id, OrderItem.product_title)
        .order_by(desc("units_sold"))
        .limit(5)
    )
    top_rows = (await db.execute(top_stmt)).all()
    top_products = [
        TopProductRecord(
            product_id=str(r[0]),
            title=r[1],
            units_sold=int(r[2] or 0),
            revenue=float(r[3] or 0.0),
        )
        for r in top_rows
    ]

    return AnalyticsOut(
        gross_revenue=gross_revenue,
        net_revenue=net_revenue,
        refunds=refunds,
        total_orders=total_orders,
        average_order_value=aov,
        customer_count=customer_count,
        coupon_usage_count=coupon_count,
        total_coupon_discounts=coupon_discounts,
        gift_wrap_count=gift_wrap_count,
        top_products=top_products,
    )


@router.get("/inventory")
async def get_inventory_ledger(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """
    Detailed inventory breakdown with stock on hand, active reservations, and recent ledger entries.
    """
    # 1. Product and variant stock
    p_stmt = select(Product).options(selectinload(Product.variants)).where(Product.is_active == True)
    products = (await db.execute(p_stmt)).scalars().unique().all()

    # 2. Active reservations
    res_stmt = (
        select(
            InventoryReservation.product_id,
            InventoryReservation.variant_id,
            func.sum(InventoryReservation.quantity).label("reserved_qty")
        )
        .where(InventoryReservation.status == ReservationStatus.ACTIVE)
        .group_by(InventoryReservation.product_id, InventoryReservation.variant_id)
    )
    res_rows = (await db.execute(res_stmt)).all()
    res_map: dict[str, int] = {}
    for r in res_rows:
        key = f"{r[0]}_{r[1]}"
        res_map[key] = int(r[2] or 0)

    # 3. Recent inventory transactions
    tx_stmt = select(InventoryTransaction).order_by(InventoryTransaction.created_at.desc()).limit(20)
    tx_records = (await db.execute(tx_stmt)).scalars().all()

    catalog_stock = []
    for p in products:
        p_res = res_map.get(f"{p.id}_None", 0)
        catalog_stock.append({
            "id": str(p.id),
            "title": p.title,
            "slug": p.slug,
            "stock_on_hand": p.stock,
            "reserved_stock": p_res,
            "available_stock": max(0, p.stock - p_res),
            "variants": [
                {
                    "id": str(v.id),
                    "name": v.name,
                    "value": v.value,
                    "sku": v.sku,
                    "stock_on_hand": v.stock,
                    "reserved_stock": res_map.get(f"{p.id}_{v.id}", 0),
                    "available_stock": max(0, v.stock - res_map.get(f"{p.id}_{v.id}", 0)),
                }
                for v in p.variants
            ],
        })

    return {
        "catalog": catalog_stock,
        "recent_transactions": [
            {
                "id": str(t.id),
                "type": t.transaction_type.value if hasattr(t.transaction_type, "value") else str(t.transaction_type),
                "quantity_delta": t.quantity_delta,
                "reference_type": t.reference_type,
                "reference_id": t.reference_id,
                "note": t.note,
                "created_at": t.created_at.strftime("%b %d, %Y %H:%M"),
            }
            for t in tx_records
        ],
    }


@router.get("/reviews")
async def list_all_reviews(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """
    Review moderation queue for admin review and approval.
    """
    stmt = (
        select(ProductReview)
        .options(selectinload(ProductReview.user), selectinload(ProductReview.product))
        .order_by(ProductReview.created_at.desc())
    )
    reviews = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": str(r.id),
            "product_id": str(r.product_id),
            "product_title": r.product.title if r.product else "Unknown",
            "user_name": r.user.full_name if r.user else "Anonymous",
            "rating": r.rating,
            "comment": r.comment,
            "is_verified_purchase": r.is_verified_purchase,
            "is_approved": r.is_approved,
            "is_flagged": r.is_flagged,
            "created_at": r.created_at.strftime("%b %d, %Y"),
        }
        for r in reviews
    ]


@router.patch("/reviews/{review_id}/moderate")
async def moderate_review(
    review_id: uuid.UUID,
    payload: ReviewModeratePayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Approve, unapprove, or flag customer reviews.
    """
    stmt = select(ProductReview).where(ProductReview.id == review_id)
    review = (await db.execute(stmt)).scalar_one_or_none()
    if not review:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")

    old_state = {"is_approved": review.is_approved, "is_flagged": review.is_flagged}

    if payload.is_approved is not None:
        review.is_approved = payload.is_approved
    if payload.is_flagged is not None:
        review.is_flagged = payload.is_flagged

    await log_audit_event(
        db=db,
        action="review_moderate",
        entity_type="product_review",
        entity_id=str(review.id),
        actor=admin,
        old_values=old_state,
        new_values={"is_approved": review.is_approved, "is_flagged": review.is_flagged},
        request=request,
    )

    await db.commit()
    return {"message": "Review moderated successfully", "review_id": str(review.id)}


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """
    View immutable administrative and security audit trail.
    """
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    logs = (await db.execute(stmt)).scalars().all()

    return [
        {
            "id": str(l.id),
            "actor_id": str(l.actor_id) if l.actor_id else None,
            "actor_role": l.actor_role,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "old_values": l.old_values,
            "new_values": l.new_values,
            "ip_address": l.ip_address,
            "created_at": l.created_at.strftime("%b %d, %Y %H:%M:%S"),
        }
        for l in logs
    ]


@router.get("/settings")
async def get_store_settings(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """
    Retrieve all store configuration settings.
    """
    stmt = select(StoreSetting)
    settings_records = (await db.execute(stmt)).scalars().all()
    return {s.key: s.value for s in settings_records}


@router.put("/settings")
async def update_store_setting(
    payload: SettingUpdatePayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """
    Update or create a store configuration setting (e.g. shipping fees, contact details).
    """
    stmt = select(StoreSetting).where(StoreSetting.key == payload.key)
    st = (await db.execute(stmt)).scalar_one_or_none()

    old_val = st.value if st else None

    if st:
        st.value = payload.value
        if payload.description:
            st.description = payload.description
    else:
        st = StoreSetting(
            key=payload.key,
            value=payload.value,
            description=payload.description,
        )
        db.add(st)

    await log_audit_event(
        db=db,
        action="update_setting",
        entity_type="store_setting",
        entity_id=payload.key,
        actor=admin,
        old_values=old_val,
        new_values=payload.value,
        request=request,
    )

    await db.commit()
    return {"message": f"Setting '{payload.key}' updated successfully", "setting": st.value}
