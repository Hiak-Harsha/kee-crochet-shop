import math
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.services.ai.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class VectorSearchEngine:
    provider = GeminiProvider()

    @classmethod
    async def search(
        cls,
        query: str,
        db: AsyncSession,
        category_id: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        in_stock_only: bool = True,
        limit: int = 10,
    ) -> list[Product]:
        """
        Hybrid semantic retrieval:
        1. Fetch active candidate products with SQL metadata filters
        2. Compute query embedding vector
        3. Rank candidates by cosine similarity against cached product embeddings
        """
        stmt = select(Product).options(selectinload(Product.variants)).where(Product.is_active == True)

        if min_price is not None:
            stmt = stmt.where(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.price <= max_price)
        if category_id:
            stmt = stmt.where(Product.category_id == category_id)
        if in_stock_only:
            stmt = stmt.where(Product.stock > 0)

        res = await db.execute(stmt)
        candidates = res.scalars().unique().all()

        if not candidates:
            return []

        # Get query embedding
        query_vector = await cls.provider.get_embedding(query)

        scored_products: list[tuple[float, Product]] = []
        for p in candidates:
            # If product has cached embedding, compare cosine similarity
            if p.embedding and isinstance(p.embedding, list) and len(p.embedding) == len(query_vector):
                score = cosine_similarity(query_vector, p.embedding)
            else:
                # Fallback keyword relevance score
                text_corpus = f"{p.title} {p.description or ''} {' '.join(p.tags or [])} {' '.join(p.colors or [])}".lower()
                matches = sum(1 for word in query.lower().split() if word in text_corpus)
                score = matches / max(1, len(query.split()))

            scored_products.append((score, p))

        # Sort by similarity descending
        scored_products.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored_products[:limit]]

    @classmethod
    async def generate_and_save_product_embedding(cls, product: Product, db: AsyncSession) -> None:
        """Create and cache embedding vector for a product."""
        corpus = f"{product.title}. {product.description or ''}. Tags: {', '.join(product.tags or [])}. Colors: {', '.join(product.colors or [])}."
        vector = await cls.provider.get_embedding(corpus)
        product.embedding = vector
        await db.commit()
