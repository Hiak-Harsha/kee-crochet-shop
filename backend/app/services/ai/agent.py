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
                # All Indian pin codes are 6 digits
                if len(pin) == 6 and pin.isdigit():
                    return {
                        "eligible": True,
                        "standard_shipping_fee": 60.00,
                        "free_shipping_threshold": 999.00,
                        "estimated_delivery_days": "3-5 business days",
                    }
                return {"error": "Please provide a valid 6-digit PIN code for shipping estimate."}

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
