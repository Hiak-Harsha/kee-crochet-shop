import asyncio
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import CartItem
from app.models.order import (
    InventoryReservation,
    InventoryTransaction,
    InventoryTransactionType,
    ReservationStatus,
)
from app.models.product import Product
from app.services.inventory_service import InventoryService


@pytest.mark.asyncio
async def test_concurrent_checkout_last_item_race_condition(db_session: AsyncSession):
    """
    CRITICAL CONCURRENCY RACE-CONDITION TEST:
    10 concurrent checkout requests for the last remaining unit (stock = 1).
    Requirement: Exactly 1 succeeds, 9 fail with HTTP 400.
    Database stock MUST end up at exactly 0 and NEVER negative.
    """
    # 1. Create a product with exactly 1 unit of stock
    prod = Product(
        id=uuid.uuid4(),
        title="Exclusive Unicorn Amigurumi",
        slug=f"unicorn-amigurumi-{uuid.uuid4().hex[:6]}",
        price=850.0,
        stock=1,  # Only 1 in stock!
        is_active=True,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)

    # 2. Define the isolated reservation worker
    async def try_reserve(worker_id: int):
        from tests.conftest import TestingSessionLocal

        order_id = uuid.uuid4()
        async with TestingSessionLocal() as session:
            try:
                item = CartItem(
                    product_id=prod.id,
                    quantity=1,
                )
                reservations = await InventoryService.reserve_stock_for_order(
                    order_id=order_id,
                    cart_items=[item],
                    db=session,
                )
                await session.commit()
                return {"success": True, "worker_id": worker_id, "order_id": order_id}
            except HTTPException as e:
                await session.rollback()
                return {"success": False, "worker_id": worker_id, "error": e.detail, "status": e.status_code}
            except Exception as e:
                await session.rollback()
                return {"success": False, "worker_id": worker_id, "error": str(e), "status": 500}

    # 3. Fire 10 simultaneous concurrent checkout attempts
    tasks = [try_reserve(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # 4. Verify results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    assert len(successful) == 1, f"Expected exactly 1 checkout to succeed, got {len(successful)}"
    assert len(failed) == 9, f"Expected 9 checkouts to fail, got {len(failed)}"

    for f in failed:
        assert f["status"] == 400
        assert "insufficient stock" in str(f["error"]).lower()

    # 5. Verify database state using a fresh session to read committed state
    from tests.conftest import TestingSessionLocal
    async with TestingSessionLocal() as verify_session:
        stmt = select(Product).where(Product.id == prod.id)
        res = await verify_session.execute(stmt)
        updated_prod = res.scalar_one()

        assert updated_prod.stock == 0, f"Stock must be exactly 0, got {updated_prod.stock}"
        assert updated_prod.stock >= 0, "Stock must never be negative!"

        # Verify exactly 1 active reservation
        r_stmt = select(InventoryReservation).where(
            InventoryReservation.product_id == prod.id,
            InventoryReservation.status == ReservationStatus.ACTIVE,
        )
        r_res = await verify_session.execute(r_stmt)
        active_reservations = r_res.scalars().all()
        assert len(active_reservations) == 1
        assert active_reservations[0].quantity == 1

        # Verify ledger audit log
        t_stmt = select(InventoryTransaction).where(
            InventoryTransaction.product_id == prod.id,
            InventoryTransaction.transaction_type == InventoryTransactionType.RESERVATION_LOCK,
        )
        t_res = await verify_session.execute(t_stmt)
        transactions = t_res.scalars().all()
        assert len(transactions) == 1
        assert transactions[0].quantity_delta == -1
