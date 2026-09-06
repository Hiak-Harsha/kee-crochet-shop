import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.services.ai.agent import ShoppingAgent


@pytest.mark.asyncio
async def test_shopping_agent_shipping_estimate(db_session: AsyncSession):
    # Valid 6-digit Indian PIN
    res_valid = await ShoppingAgent.execute_tool(
        "get_shipping_estimate",
        {"postal_code": "560001"},
        db=db_session,
    )
    assert res_valid["eligible"] is True
    assert "standard_shipping_fee" in res_valid
    assert "free_shipping_threshold" in res_valid

    # Invalid PIN
    res_invalid = await ShoppingAgent.execute_tool(
        "get_shipping_estimate",
        {"postal_code": "ABC"},
        db=db_session,
    )
    assert "error" in res_invalid


@pytest.mark.asyncio
async def test_shopping_agent_cart_tools_lifecycle(
    db_session: AsyncSession,
    test_user: User,
    sample_product: Product,
):
    # Create test cart
    cart = Cart(user_id=test_user.id)
    db_session.add(cart)
    await db_session.commit()
    await db_session.refresh(cart)

    # 1. get_cart (initially empty)
    cart_res = await ShoppingAgent.execute_tool(
        "get_cart",
        {},
        db=db_session,
        user=test_user,
        cart=cart,
    )
    assert cart_res["item_count"] == 0
    assert cart_res["subtotal"] == 0.0

    # 2. add_to_cart
    add_res = await ShoppingAgent.execute_tool(
        "add_to_cart",
        {"product_id": str(sample_product.id), "quantity": 2, "gift_wrap": True},
        db=db_session,
        user=test_user,
        cart=cart,
    )
    assert add_res["success"] is True

    # 3. get_cart (verify items added and totals calculated)
    cart_res2 = await ShoppingAgent.execute_tool(
        "get_cart",
        {},
        db=db_session,
        user=test_user,
        cart=cart,
    )
    assert cart_res2["item_count"] == 2
    assert len(cart_res2["items"]) == 1
    item_id = cart_res2["items"][0]["id"]
    assert cart_res2["subtotal"] == 1300.0  # 2 * 650

    # 4. update_cart (reduce quantity to 1)
    up_res = await ShoppingAgent.execute_tool(
        "update_cart",
        {"item_id": item_id, "quantity": 1},
        db=db_session,
        user=test_user,
        cart=cart,
    )
    assert up_res["success"] is True

    # 5. remove_from_cart
    del_res = await ShoppingAgent.execute_tool(
        "remove_from_cart",
        {"item_id": item_id},
        db=db_session,
        user=test_user,
        cart=cart,
    )
    assert del_res["success"] is True

    # 6. verify empty again
    cart_res3 = await ShoppingAgent.execute_tool(
        "get_cart",
        {},
        db=db_session,
        user=test_user,
        cart=cart,
    )
    assert cart_res3["item_count"] == 0
