import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.product import Product
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIColorMatchResponse,
    AIProductDescriptionResponse,
    AIInstagramCaptionResponse,
    AIReviewSummarizerResponse,
    AIFAQResponse,
)
from app.services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


async def _get_serialized_catalog(db: AsyncSession) -> list[dict]:
    """Helper to query all active products and return them as basic dictionaries for AI context."""
    stmt = select(Product).options(selectinload(Product.variants)).where(Product.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    products = result.scalars().unique().all()
    
    catalog = []
    for p in products:
        catalog.append({
            "id": str(p.id),
            "title": p.title,
            "description": p.description,
            "price": float(p.price),
            "slug": p.slug,
            "tags": p.tags,
            "colors": p.colors,
            "stock": p.stock,
            "variants": [{"name": v.name, "value": v.value, "price_delta": float(v.price_delta)} for v in p.variants]
        })
    return catalog


@router.get("/search", response_model=list[str])
async def search_products(q: str, db: AsyncSession = Depends(get_db)):
    """Semantic search endpoint returning list of product IDs."""
    catalog = await _get_serialized_catalog(db)
    if not catalog:
        return []
    matching_ids = await ai_service.semantic_search(q, catalog)
    return matching_ids


@router.post("/chat", response_model=AIChatResponse)
async def chat_personal_shopper(payload: AIChatRequest, db: AsyncSession = Depends(get_db)):
    """Personal shopper assistant chat endpoint."""
    catalog = await _get_serialized_catalog(db)
    messages_dict = [{"role": msg.role, "content": msg.content} for msg in payload.messages]
    
    reply, recommended_ids = await ai_service.chat_shopper(messages_dict, catalog)
    return AIChatResponse(reply=reply, recommended_product_ids=recommended_ids)


@router.post("/color-match", response_model=AIColorMatchResponse)
async def color_match_room(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload an image of a room/setting to suggest matching crochet items and accent colors."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image")
    
    MAX_SIZE = 5 * 1024 * 1024
    image_bytes = await file.read(MAX_SIZE + 1)
    if len(image_bytes) > MAX_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large. Maximum size is 5MB.")
        
    catalog = await _get_serialized_catalog(db)
    
    result = await ai_service.suggest_colors(image_bytes, catalog)
    return AIColorMatchResponse(
        recommended_colors=result.get("recommended_colors", []),
        reasoning=result.get("reasoning", ""),
        matching_product_ids=result.get("matching_product_ids", [])
    )


@router.post("/describe-product", response_model=AIProductDescriptionResponse)
async def upload_and_describe_product(
    file: UploadFile = File(...),
    _admin=Depends(get_current_admin)
):
    """Upload product image to generate title, description, tags, and Instagram caption (Admin)."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must be an image")
        
    MAX_SIZE = 5 * 1024 * 1024
    image_bytes = await file.read(MAX_SIZE + 1)
    if len(image_bytes) > MAX_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large. Maximum size is 5MB.")
        
    result = await ai_service.describe_product(image_bytes)
    return AIProductDescriptionResponse(
        title=result.get("title", ""),
        description=result.get("description", ""),
        tags=result.get("tags", []),
        instagram_caption=result.get("instagram_caption", "")
    )


@router.post("/instagram-caption", response_model=AIInstagramCaptionResponse)
async def instagram_caption_generator(
    product_id: str = Form(...),
    style: str = Form("trendy"),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """Generate tailored Instagram captions for a specific product."""
    import uuid
    try:
        p_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid product UUID")
        
    result = await db.execute(select(Product).where(Product.id == p_uuid))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
        
    result = await ai_service.generate_instagram_caption(
        product.title, product.description or "", style
    )
    return AIInstagramCaptionResponse(
        caption=result.get("caption", ""),
        hashtags=result.get("hashtags", [])
    )


@router.post("/summarize-reviews", response_model=AIReviewSummarizerResponse)
async def summarize_product_reviews(product_id: str):
    """Summarizes feedback/reviews for a product. Currently utilizes dummy reviews or mock input."""
    # In a fully-fledged app, reviews would be fetched from database table.
    # For now we supply standard dummy reviews to summarize.
    dummy_reviews = [
        "So cute and incredibly soft! Gifted it to my sister and she absolutely loved it.",
        "Beautiful craftsmanship. The stitch detail is amazing. It took a few days longer to ship than expected, but it was worth the wait.",
        "Very nice packaging, came with a cute custom note. Highly recommend for handmade gifts!",
        "A bit smaller than I imagined but still very cute. Love the pastel pink color."
    ]
    result = await ai_service.summarize_reviews(dummy_reviews)
    return AIReviewSummarizerResponse(
        summary=result.get("summary", ""),
        pros=result.get("pros", []),
        cons=result.get("cons", []),
        sentiment=result.get("sentiment", "Positive")
    )


@router.post("/faq", response_model=AIFAQResponse)
async def dynamic_faq_answer(question: str = Form(...)):
    """Natural language FAQ responder using store policy knowledge base."""
    answer = await ai_service.faq_bot(question)
    return AIFAQResponse(answer=answer)
