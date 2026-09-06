import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import AIUsage
from app.services.ai.base import AIResult

logger = logging.getLogger(__name__)

# Estimated cost per 1k tokens in USD (e.g. Gemini 1.5 Flash ~$0.00035 / 1k)
ESTIMATED_COST_PER_1K_TOKENS = 0.00035


class AIUsageService:
    @staticmethod
    async def log_usage(
        result: AIResult,
        operation: str,
        db: AsyncSession,
        user_id: uuid.UUID | None = None,
        request_id: str | None = None,
    ) -> None:
        try:
            tokens = result.total_tokens or (result.prompt_tokens + result.completion_tokens)
            estimated_cost = (tokens / 1000.0) * ESTIMATED_COST_PER_1K_TOKENS

            usage = AIUsage(
                user_id=user_id,
                request_id=request_id,
                operation=operation,
                model=result.model or "unknown",
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=tokens,
                estimated_cost=estimated_cost,
                latency_ms=result.latency_ms,
                status="success" if result.success else "failed",
            )
            db.add(usage)
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to record AI usage metric: {e}")
