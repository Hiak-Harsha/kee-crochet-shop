import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cart import Cart, CartItem
from app.models.order import Order
from app.models.product import Product, ProductVariant
from app.models.user import CustomRequest, User
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.prompt_registry import PromptRegistry
from app.services.ai.vector_search import VectorSearchEngine

logger = logging.getLogger(__name__)


class ShoppingAgent:
    provider = GeminiProvider()

    @classmethod
    async def execute_tool(
        cls,
        tool_name: str,
        arguments: dict[str, Any],
        db: AsyncSession,
        user: User | None = None,
        cart: Cart | None = None,
    ) -> dict[str, Any]:
        """
        Server-side validation and execution of agent tools.
        The LLM never mutates the database directly.
        """
        try:
            if tool_name == "search_products":
                q = arguments.get("query", "")
                min_p = arguments.get("min_price")
                max_p = arguments.get("max_price")
                products = await VectorSearchEngine.search(
                    query=q, db=db, min_price=min_p, max_price=max_p, limit=5
                )
                return {
                    "products": [
                        {
                            "id": str(p.id),
                            "title": p.title,
                            "price": float(p.price),
                            "slug": p.slug,
                            "stock": p.stock,
                            "in_stock": p.stock > 0,
                            "image": p.images[0] if p.images else None,
                        }
                        for p in products
                    ]
                }

            elif tool_name == "get_product":
                slug_or_id = arguments.get("slug_or_id", "")
                stmt = select(Product).options(selectinload(Product.variants)).where(
                    (Product.slug == slug_or_id) | (Product.id == uuid.UUID(slug_or_id) if len(slug_or_id) == 36 else False)
                )
                res = await db.execute(stmt)
                p = res.scalar_one_or_none()
                if not p:
                    return {"error": "Product not found"}
                return {
                    "id": str(p.id),
                    "title": p.title,
                    "description": p.description,
                    "price": float(p.price),
                    "stock": p.stock,
                    "variants": [{"id": str(v.id), "name": v.name, "value": v.value, "stock": v.stock} for v in p.variants],
                }

            elif tool_name == "check_inventory":
                product_id = arguments.get("product_id")
                variant_id = arguments.get("variant_id")
                if variant_id:
                    v_res = await db.execute(select(ProductVariant).where(ProductVariant.id == uuid.UUID(variant_id)))
                    v = v_res.scalar_one_or_none()
                    return {"available_stock": v.stock if v else 0, "in_stock": bool(v and v.stock > 0)}
                elif product_id:
                    p_res = await db.execute(select(Product).where(Product.id == uuid.UUID(product_id)))
                    p = p_res.scalar_one_or_none()
                    return {"available_stock": p.stock if p else 0, "in_stock": bool(p and p.stock > 0)}
                return {"error": "Missing product_id or variant_id"}

            elif tool_name == "get_shipping_estimate":
                pin = str(arguments.get("postal_code", "")).strip()
                # Indian PIN codes must be 6 digits
                if len(pin) == 6 and pin.isdigit():
                    std_fee = 60.00
                    free_thresh = 999.00
                    del_days = "3-5 business days"
                    try:
                        from app.models.user import StoreSetting
                        st_res = await db.execute(select(StoreSetting).where(StoreSetting.key == "shipping"))
                        st_rec = st_res.scalar_one_or_none()
                        if st_rec and isinstance(st_rec.value, dict):
                            std_fee = float(st_rec.value.get("standard_fee", std_fee))
                            free_thresh = float(st_rec.value.get("free_threshold", free_thresh))
                            del_days = str(st_rec.value.get("delivery_estimate", del_days))
                    except Exception:
                        pass

                    return {
                        "eligible": True,
                        "standard_shipping_fee": std_fee,
                        "free_shipping_threshold": free_thresh,
                        "estimated_delivery_days": del_days,
                    }
                return {"error": "Please provide a valid 6-digit PIN code for shipping estimate."}

            elif tool_name == "get_cart":
                if not cart:
                    return {"items": [], "subtotal": 0.0, "total": 0.0, "item_count": 0}
                
                # Query CartItem records directly with eager loading
                stmt = select(CartItem).options(
                    selectinload(CartItem.product),
                    selectinload(CartItem.variant),
                ).where(CartItem.cart_id == cart.id)
                res = await db.execute(stmt)
                cart_items = res.scalars().all()

                from app.services.pricing_service import PricingService
                breakdown = await PricingService.calculate_cart_totals(cart_items, user=user, db=db)
                return {
                    "items": [
                        {
                            "id": str(it.id),
                            "product_title": it.product.title if it.product else "Unknown",
                            "variant_name": it.variant.value if it.variant else None,
                            "quantity": it.quantity,
                            "gift_wrap": it.gift_wrap,
                        }
                        for it in cart_items
                    ],
                    "subtotal": float(breakdown.subtotal),
                    "shipping_fee": float(breakdown.shipping_fee),
                    "gift_wrap_fee": float(breakdown.gift_wrap_fee),
                    "total": float(breakdown.total),
                    "item_count": sum(it.quantity for it in cart_items),
                }

            elif tool_name == "add_to_cart":
                if not cart:
                    return {"error": "Active cart session is required to add items."}

                product_id_str = arguments.get("product_id")
                if not product_id_str:
                    return {"error": "product_id is required."}

                try:
                    prod_uuid = uuid.UUID(product_id_str)
                except Exception:
                    return {"error": f"Invalid product_id: '{product_id_str}'"}

                # Check product
                p_res = await db.execute(
                    select(Product).options(selectinload(Product.variants)).where(Product.id == prod_uuid)
                )
                product = p_res.scalar_one_or_none()
                if not product or not product.is_active:
                    return {"error": "Product is unavailable or inactive."}

                qty = max(1, min(int(arguments.get("quantity", 1)), 10))
                variant_uuid = None
                variant_id_str = arguments.get("variant_id")
                if variant_id_str:
                    try:
                        variant_uuid = uuid.UUID(variant_id_str)
                        variant = next((v for v in product.variants if v.id == variant_uuid), None)
                        if not variant or not variant.is_active:
                            return {"error": "Selected variant is unavailable or inactive."}
                        if variant.stock < qty:
                            return {"error": f"Insufficient stock for variant '{variant.value}'. Available: {variant.stock}."}
                    except Exception:
                        return {"error": f"Invalid variant_id: '{variant_id_str}'"}
                else:
                    if product.stock < qty:
                        return {"error": f"Insufficient stock for '{product.title}'. Available: {product.stock}."}

                # Check if item exists in cart
                gift_wrap = bool(arguments.get("gift_wrap", False))
                note = arguments.get("note")

                existing_item_stmt = select(CartItem).where(
                    CartItem.cart_id == cart.id,
                    CartItem.product_id == prod_uuid,
                    CartItem.variant_id == variant_uuid,
                )
                ex_res = await db.execute(existing_item_stmt)
                existing_item = ex_res.scalar_one_or_none()

                if existing_item:
                    existing_item.quantity += qty
                    if gift_wrap:
                        existing_item.gift_wrap = True
                    if note:
                        existing_item.note = note
                else:
                    new_item = CartItem(
                        cart_id=cart.id,
                        product_id=prod_uuid,
                        variant_id=variant_uuid,
                        quantity=qty,
                        gift_wrap=gift_wrap,
                        note=note,
                    )
                    db.add(new_item)

                await db.commit()
                return {
                    "success": True,
                    "message": f"Added {qty}x '{product.title}' to cart.",
                    "product_id": str(product.id),
                    "quantity": qty,
                }

            elif tool_name == "update_cart":
                if not cart:
                    return {"error": "Active cart session is required."}

                item_id_str = arguments.get("item_id")
                if not item_id_str:
                    return {"error": "item_id is required."}

                try:
                    item_uuid = uuid.UUID(item_id_str)
                except Exception:
                    return {"error": f"Invalid item_id: '{item_id_str}'"}

                it_res = await db.execute(
                    select(CartItem).where(CartItem.id == item_uuid, CartItem.cart_id == cart.id)
                )
                cart_item = it_res.scalar_one_or_none()
                if not cart_item:
                    return {"error": "Cart item not found."}

                if "quantity" in arguments:
                    new_qty = int(arguments["quantity"])
                    if new_qty <= 0:
                        await db.delete(cart_item)
                        await db.commit()
                        return {"success": True, "message": "Item removed from cart."}
                    else:
                        cart_item.quantity = min(new_qty, 10)

                if "gift_wrap" in arguments:
                    cart_item.gift_wrap = bool(arguments["gift_wrap"])

                await db.commit()
                return {"success": True, "message": "Cart item updated successfully."}

            elif tool_name == "remove_from_cart":
                if not cart:
                    return {"error": "Active cart session is required."}

                item_id_str = arguments.get("item_id")
                if not item_id_str:
                    return {"error": "item_id is required."}

                try:
                    item_uuid = uuid.UUID(item_id_str)
                except Exception:
                    return {"error": f"Invalid item_id: '{item_id_str}'"}

                it_res = await db.execute(
                    select(CartItem).where(CartItem.id == item_uuid, CartItem.cart_id == cart.id)
                )
                cart_item = it_res.scalar_one_or_none()
                if not cart_item:
                    return {"error": "Cart item not found in cart."}

                await db.delete(cart_item)
                await db.commit()
                return {"success": True, "message": "Item removed from cart."}

            elif tool_name == "get_order_status":
                num = arguments.get("order_number", "").strip().upper()
                if not num:
                    return {"error": "Missing order number"}
                stmt = select(Order).where(Order.order_number == num)
                if user:
                    stmt = stmt.where(Order.user_id == user.id)
                res = await db.execute(stmt)
                ord_rec = res.scalar_one_or_none()
                if not ord_rec:
                    return {"error": f"Order {num} not found"}
                return {
                    "order_number": ord_rec.order_number,
                    "status": ord_rec.status.value,
                    "total": float(ord_rec.total),
                    "created_at": ord_rec.created_at.strftime("%b %d, %Y"),
                }

            elif tool_name == "create_custom_request":
                desc = arguments.get("description")
                palette = arguments.get("color_palette")
                if not user:
                    return {"error": "Please sign in to submit a custom crochet request."}
                if not desc:
                    return {"error": "Description is required"}
                req = CustomRequest(
                    user_id=user.id,
                    description=desc,
                    color_palette=palette,
                )
                db.add(req)
                await db.commit()
                return {"success": True, "request_id": str(req.id), "message": "Custom design request submitted!"}

            return {"error": f"Unknown tool '{tool_name}'"}
        except Exception as e:
            logger.error(f"Error executing agent tool {tool_name}: {e}")
            return {"error": str(e)}

    @classmethod
    async def chat(
        cls,
        messages: list[dict[str, Any]],
        db: AsyncSession,
        user: User | None = None,
        cart: Cart | None = None,
    ) -> tuple[str, list[str]]:
        """
        Process chat interaction using rolling window and validated tools.
        Returns: (assistant_text, recommended_product_ids)
        """
        system_instruction = await PromptRegistry.get_system_instruction(db)

        # Truncate to rolling 5 messages window for token safety
        recent_messages = messages[-5:] if len(messages) > 5 else messages

        # Extract latest user message
        last_msg = recent_messages[-1]["content"] if recent_messages else ""

        # Check if user query matches product search intent
        search_results = await VectorSearchEngine.search(query=last_msg, db=db, limit=3)
        recommended_ids = [str(p.id) for p in search_results]

        context_brief = ""
        if search_results:
            context_brief = "\nRelevant products available right now:\n" + "\n".join(
                f"- {p.title} (Price: ₹{p.price}, In Stock: {p.stock > 0})" for p in search_results
            )

        enhanced_messages = list(recent_messages)
        enhanced_messages.append({
            "role": "user",
            "content": f"[SYSTEM CONTEXT: {context_brief}]\nCustomer question: {last_msg}"
        })

        ai_result = await cls.provider.generate_chat(
            messages=enhanced_messages,
            system_instruction=system_instruction,
            temperature=0.7,
        )

        return ai_result.content, recommended_ids
