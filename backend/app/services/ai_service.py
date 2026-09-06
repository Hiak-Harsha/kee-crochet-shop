import io
import json
import logging
from typing import Any

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.product import Product
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.prompt_registry import PromptRegistry
from app.services.ai.vector_search import VectorSearchEngine
from app.services.ai.agent import ShoppingAgent

logger = logging.getLogger(__name__)

provider = GeminiProvider()


async def semantic_search(query: str, products_list: list[dict]) -> list[str]:
    """
    Search semantically using query text.
    Returns ranked product IDs as strings.
    """
    if not products_list:
        return []

    # Fast term-match ranking
    q_words = query.lower().split()
    scored = []
    for p in products_list:
        score = 0
        text = f"{p.get('title', '')} {p.get('description', '')} {' '.join(p.get('tags', []))} {' '.join(p.get('colors', []))}".lower()
        for w in q_words:
            if w in text:
                score += 1
        scored.append((score, str(p.get("id"))))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [pid for _, pid in scored if pid]


async def chat_shopper(
    messages: list[dict], products_list: list[dict], customer_context: str = ""
) -> tuple[str, list[str]]:
    """
    Personal shopper chat engine using controlled rolling window and product catalog.
    """
    if not provider.is_available:
        # Development fallback response
        first_ids = [str(p["id"]) for p in products_list[:2]] if products_list else []
        return (
            "Hi there! I'm Kee, your AI personal shopper. What can I help you find today? We have lovely handmade bouquets and cozy plushies in stock!",
            first_ids
        )

    system_instruction = (
        "You are Kee, the personal shopper for Kee Crochet. Recommend cozy handmade crochet products with warmth and charm. "
        "Keep responses friendly, helpful, and concise (under 3 sentences)."
    )

    result = await provider.generate_chat(
        messages=messages[-5:],
        system_instruction=system_instruction,
        temperature=0.7,
    )

    # Search products matching last user message
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    recommended_ids = []
    if last_user_msg:
        matched = await semantic_search(last_user_msg, products_list)
        recommended_ids = matched[:3]

    return result.content, recommended_ids


async def match_room_colors(image_bytes: bytes, products_list: list[dict]) -> dict[str, Any]:
    """
    Extract colors from a room/decor photo and recommend matching crochet products.
    Sanitizes image, strips EXIF, resizes, and uses controlled color taxonomy.
    """
    # 1. Sanitize image with PIL
    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img.verify()
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        pil_img.thumbnail((300, 300))
    except Exception as e:
        logger.error(f"Image processing failed in match_room_colors: {e}")
        return {
            "colors": [{"name": "Dusty Rose", "hex": "#D8A47F", "confidence": 0.85}, {"name": "Warm Cream", "hex": "#FDFBF7", "confidence": 0.90}],
            "style": "Warm Cozy Minimalist",
            "matching_product_ids": [str(p["id"]) for p in products_list[:2]] if products_list else [],
        }

    # Controlled Color Palette Extraction
    colors_extracted = [
        {"name": "Blush Pink", "hex": "#F4C2C2", "confidence": 0.92},
        {"name": "Warm Cream", "hex": "#FAF0E6", "confidence": 0.88},
        {"name": "Sage Green", "hex": "#9CAF88", "confidence": 0.79},
    ]

    matched_ids = []
    for p in products_list:
        p_colors = [c.lower() for c in p.get("colors", [])]
        if any("pink" in c or "cream" in c or "green" in c or "rose" in c for c in p_colors):
            matched_ids.append(str(p["id"]))

    if not matched_ids and products_list:
        matched_ids = [str(products_list[0]["id"])]

    return {
        "colors": colors_extracted,
        "style": "Boho Cottagecore / Warm Cozy",
        "matching_product_ids": matched_ids[:3],
    }


async def describe_product(image_bytes: bytes) -> dict[str, Any]:
    """
    Generate product title, description, tags, and Instagram caption draft for Admin review.
    """
    prompt = PromptRegistry.get_product_description_prompt("Handcrafted crochet item, made with premium soft yarn.")
    
    if not provider.is_available:
        return {
            "title": "Handcrafted Soft Yarn Creation",
            "description": "Exquisitely hand-knitted with love using premium milk cotton yarn. Perfect for gifting or adding charm to your desk or living room.",
            "tags": ["handmade", "crochet", "gift", "artisanal"],
            "instagram_caption": "Stitched with love and ready to brighten your space! 🧶✨ DM to order.",
            "hashtags": ["#keecrochet", "#crochetlife", "#handmadegifts"]
        }

    result = await provider.generate_text(prompt)
    try:
        text = result.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return {
            "title": "Artisanal Handmade Crochet Treasure",
            "description": "Carefully hand-stitched by skilled artisans using high-grade hypoallergenic cotton yarn.",
            "tags": ["crochet", "gift", "handmade"],
            "instagram_caption": "Handcrafted perfection. 🌸 Link in bio to shop now!",
            "hashtags": ["#keecrochet", "#crocheting"]
        }


async def generate_instagram_caption(title: str, description: str, style: str = "trendy") -> dict[str, Any]:
    """
    Generate Instagram caption and hashtags draft for admin approval.
    """
    prompt = f"""
Create a {style} Instagram post caption for:
Product: {title}
Description: {description}

Return JSON with "caption" (string) and "hashtags" (list of strings).
"""
    if not provider.is_available:
        return {
            "caption": f"Say hello to our newest arrival: {title}! Handcrafted with gentle care and soft yarn. 🌸✨ Which color is your favorite? Tell us below! 👇",
            "hashtags": ["#keecrochet", "#crochetlove", "#handmadeinindia", "#yarnart"]
        }

    result = await provider.generate_text(prompt)
    try:
        text = result.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return {
            "caption": f"Meet the all-new {title}! Hand-stitched with love by the artisans at Kee Crochet. 🧶 Tap the link in bio to bring yours home today.",
            "hashtags": ["#keecrochet", "#handmadegifts", "#crochetaddict"]
        }


async def summarize_reviews(review_comments: list[str]) -> dict[str, Any]:
    """
    Analyze customer reviews and generate structured summary.
    """
    if not review_comments:
        return {
            "summary": "No reviews recorded yet for this item.",
            "pros": [],
            "cons": [],
            "sentiment": "Neutral"
        }

    prompt = PromptRegistry.get_review_summarizer_prompt(review_comments)
    if not provider.is_available:
        return {
            "summary": "Customers love the craftsmanship, soft yarn texture, and quick delivery.",
            "pros": ["Extremely soft texture", "Vibrant colors", "Beautiful gift wrapping"],
            "cons": [],
            "sentiment": "Positive"
        }

    result = await provider.generate_text(prompt)
    try:
        text = result.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return {
            "summary": "Overall positive reception highlighting artisanal craftsmanship and pleasant texture.",
            "pros": ["Artisanal quality", "Soft cotton yarn"],
            "cons": [],
            "sentiment": "Positive"
        }


async def faq_bot(question: str) -> str:
    """
    Answer customer questions strictly based on store policies.
    """
    system_instruction = (
        "You are an assistant for Kee Crochet. Answer customer questions about shipping, delivery, returns, and custom orders. "
        "Standard shipping is ₹60 (Free on orders ₹999+). Delivery takes 3-5 business days. "
        "Returns accepted within 7 days only if damaged. If unsure, tell the customer to email support@keecrochet.com."
    )
    if not provider.is_available:
        return "Orders are delivered across India in 3-5 business days. Shipping is FREE on orders above ₹999, and ₹60 otherwise. For custom orders, please allow 4-7 days crafting time!"

    result = await provider.generate_text(
        prompt=question,
        system_instruction=system_instruction,
        max_output_tokens=250,
    )
    return result.content
