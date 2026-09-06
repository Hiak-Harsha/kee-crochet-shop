import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, DateTime, Enum, func, JSON, UUID, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    paid = "paid"
    processing = "processing"
    packed = "packed"
    shipped = "shipped"
    delivered = "delivered"
    completed = "completed"
    cancelled = "cancelled"
    refunded = "refunded"


# Valid state transitions
VALID_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending_payment: {OrderStatus.paid, OrderStatus.cancelled},
    OrderStatus.paid: {OrderStatus.processing, OrderStatus.cancelled, OrderStatus.refunded},
    OrderStatus.processing: {OrderStatus.packed, OrderStatus.cancelled, OrderStatus.refunded},
    OrderStatus.packed: {OrderStatus.shipped, OrderStatus.cancelled, OrderStatus.refunded},
    OrderStatus.shipped: {OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.refunded},
    OrderStatus.delivered: {OrderStatus.completed, OrderStatus.refunded},
    OrderStatus.completed: {OrderStatus.refunded},
    OrderStatus.cancelled: set(),
    OrderStatus.refunded: set(),
}


def can_transition_order_status(current_status: OrderStatus, new_status: OrderStatus) -> bool:
    """Check whether transition from current_status to new_status is permitted."""
    if current_status == new_status:
        return True
    return new_status in VALID_ORDER_TRANSITIONS.get(current_status, set())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.pending_payment, index=True)
    
    # Financial breakdown using Decimal precision
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    item_discounts: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True)
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    coupon_discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    gift_wrap_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    shipping_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    tax: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    shipping_address: Mapped[dict] = mapped_column(JSON, nullable=False)
    delivery_slot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    reservations = relationship("InventoryReservation", back_populates="order", cascade="all, delete-orphan")

    @property
    def discount(self) -> float:
        return float(self.coupon_discount or 0.0) + float(self.item_discounts or 0.0)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True)
    product_title: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    gift_wrap: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    order = relationship("Order", back_populates="items")

    @property
    def total_price(self) -> float:
        return float(self.unit_price) * self.quantity


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(Enum(ReservationStatus), default=ReservationStatus.ACTIVE, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="reservations")


class InventoryTransactionType(str, enum.Enum):
    RESERVATION_LOCK = "RESERVATION_LOCK"
    RESERVATION_COMMIT = "RESERVATION_COMMIT"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"
    RESTOCK = "RESTOCK"
    RETURN = "RETURN"


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_type: Mapped[InventoryTransactionType] = mapped_column(Enum(InventoryTransactionType), nullable=False, index=True)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "order", "admin", "supplier"
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class CouponType(str, enum.Enum):
    percentage = "percentage"
    fixed = "fixed"
    free_shipping = "free_shipping"


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    type: Mapped[CouponType] = mapped_column(Enum(CouponType), default=CouponType.percentage)
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)  # e.g. 10 for 10%, or 100 for 100 Rs
    minimum_order_value: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    maximum_discount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_customer_limit: Mapped[int] = mapped_column(Integer, default=1)
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    redemptions = relationship("CouponRedemption", back_populates="coupon", cascade="all, delete-orphan")


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coupon_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    coupon = relationship("Coupon", back_populates="redemptions")


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    captured = "captured"
    failed = "failed"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), default="razorpay")
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending, index=True)
    razorpay_order_id: Mapped[str] = mapped_column(String(100), index=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    razorpay_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    order = relationship("Order", back_populates="payments")


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
