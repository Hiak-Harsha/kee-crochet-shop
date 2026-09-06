import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_user, get_current_user_optional
from app.core.database import get_db
from app.models.product import Product, ProductReview
from app.models.user import AIChatSession, AIChatMessage
from app.models.cart import Cart
from app.models.order import Order
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIColorMatchResponse,
    AIProductDescriptionResponse,
    AIInstagramCaptionResponse,
    AIReviewSummarizerResponse,
    AIFAQResponse,
    AIChatMessageOut,
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


async def _get_or_create_chat_session(db: AsyncSession, user_id: uuid.UUID) -> AIChatSession:
    stmt = (
        select(AIChatSession)
        .options(selectinload(AIChatSession.messages))
        .where(AIChatSession.user_id == user_id)
        .order_by(AIChatSession.created_at.desc())
    )
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        session = AIChatSession(user_id=user_id)
        db.add(session)
        await db.commit()
        await db.refresh(session)
    return session


@router.get("/chat/history", response_model=list[AIChatMessageOut])
async def get_chat_history(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """Retrieve persistent chat history for the logged-in user."""
    session = await _get_or_create_chat_session(db, user.id)
    stmt = select(AIChatMessage).where(AIChatMessage.session_id == session.id).order_by(AIChatMessage.created_at.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/chat/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_history(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """Clear persistent chat history (deletes sessions and starts fresh)."""
    stmt = select(AIChatSession).where(AIChatSession.user_id == user.id)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    for s in sessions:
        await db.delete(s)
    await db.commit()
    return


@router.post("/chat", response_model=AIChatResponse)
async def chat_personal_shopper(
    payload: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user_optional)
):
    """Personal shopper assistant chat endpoint with database session persistence and user context."""
    catalog = await _get_serialized_catalog(db)
    
    if user is not None:
        # Load or create user chat session
        session = await _get_or_create_chat_session(db, user.id)
        
        # Save user message to database
        user_message = payload.messages[-1].content
        db.add(AIChatMessage(session_id=session.id, role="user", content=user_message))
        await db.flush()
        
        # Load full chat history for prompt
        hist_stmt = select(AIChatMessage).where(AIChatMessage.session_id == session.id).order_by(AIChatMessage.created_at.asc())
        hist_res = await db.execute(hist_stmt)
        messages_db = hist_res.scalars().all()
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages_db]
        
        # Compile active cart context
        cart_stmt = select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user.id)
        cart_res = await db.execute(cart_stmt)
        cart = cart_res.scalar_one_or_none()
        
        cart_context = ""
        if cart and cart.items:
            # Query products in cart to get titles
            cart_items_full = []
            for item in cart.items:
                prod_res = await db.execute(select(Product).where(Product.id == item.product_id))
                prod = prod_res.scalar_one_or_none()
                if prod:
                    cart_items_full.append(f"{item.quantity}x {prod.title}")
            if cart_items_full:
                cart_context = f"The customer currently has these items in their active shopping cart: {', '.join(cart_items_full)}."
        
        # Compile past orders history
        order_stmt = select(Order).options(selectinload(Order.items)).where(Order.user_id == user.id).order_by(Order.created_at.desc())
        order_res = await db.execute(order_stmt)
        orders = order_res.scalars().all()
        
        order_context = ""
        if orders:
            orders_desc = []
            for ord in orders:
                items_desc = ", ".join([f"{item.quantity}x {item.product_title}" for item in ord.items])
                orders_desc.append(f"Order on {ord.created_at.strftime('%Y-%b-%d')} (Status: {ord.status.value}) containing [{items_desc}]")
            order_context = f"The customer's past order history is: {'; '.join(orders_desc)}."
            
        # Combine customer context
        customer_context = f"Customer Profile:\n- Name: {user.full_name or 'Valued Customer'}\n"
        if cart_context:
            customer_context += f"- {cart_context}\n"
        if order_context:
            customer_context += f"- {order_context}\n"
            
        reply, recommended_ids = await ai_service.chat_shopper(messages_dict, catalog, customer_context)
        
        # Save assistant message to database
        db.add(AIChatMessage(session_id=session.id, role="assistant", content=reply))
        await db.commit()
    else:
        # Fallback to guest stateless mode
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in payload.messages]
        reply, recommended_ids = await ai_service.chat_shopper(messages_dict, catalog, "")
        
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
async def summarize_product_reviews(product_id: str, db: AsyncSession = Depends(get_db)):
    """Summarizes feedback/reviews for a product based on real database records."""
    import uuid
    try:
        p_uuid = uuid.UUID(product_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid product UUID")
        
    stmt = select(ProductReview).where(ProductReview.product_id == p_uuid)
    result = await db.execute(stmt)
    reviews = result.scalars().all()
    
    if not reviews:
        return AIReviewSummarizerResponse(
            summary="No reviews yet for this product. Be the first to share your thoughts!",
            pros=[],
            cons=[],
            sentiment="Neutral"
        )
        
    review_comments = [r.comment for r in reviews if r.comment]
    if not review_comments:
        return AIReviewSummarizerResponse(
            summary="No reviews yet for this product. Be the first to share your thoughts!",
            pros=[],
            cons=[],
            sentiment="Neutral"
        )
        
    res = await ai_service.summarize_reviews(review_comments)
    return AIReviewSummarizerResponse(
        summary=res.get("summary", ""),
        pros=res.get("pros", []),
        cons=res.get("cons", []),
        sentiment=res.get("sentiment", "Positive")
    )


@router.post("/faq", response_model=AIFAQResponse)
async def dynamic_faq_answer(question: str = Form(...)):
    """Natural language FAQ responder using store policy knowledge base."""
    answer = await ai_service.faq_bot(question)
    return AIFAQResponse(answer=answer)
