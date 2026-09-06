import asyncio
import logging
import time
from typing import Any

from app.core.config import settings
from app.services.ai.base import AIProvider, AIResult, ToolDefinition

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_LIB_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    GEMINI_LIB_AVAILABLE = False


class GeminiProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"
        self._is_configured = False

        if GEMINI_LIB_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)  # type: ignore
                self._is_configured = True
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")

    @property
    def is_available(self) -> bool:
        return self._is_configured and bool(self.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1000,
    ) -> AIResult:
        if not self.is_available:
            if settings.ENVIRONMENT == "production":
                raise RuntimeError("Gemini API is not configured on the production server.")
            # Deterministic development mock response
            return AIResult(
                content="This is a development mock response from Kee AI Assistant.",
                model="mock-dev-model",
                total_tokens=20,
            )

        start_time = time.time()
        try:
            model = genai.GenerativeModel(  # type: ignore
                model_name=self.model_name,
                system_instruction=system_instruction,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
            )
            # Run blocking SDK in executor with timeout
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: model.generate_content(prompt)),
                timeout=15.0
            )
            latency_ms = int((time.time() - start_time) * 1000)
            text_out = response.text.strip() if response and response.text else ""

            return AIResult(
                content=text_out,
                model=self.model_name,
                latency_ms=latency_ms,
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text_out) // 4,
                total_tokens=(len(prompt) + len(text_out)) // 4,
                success=True,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Gemini generate_text error: {e}")
            if settings.ENVIRONMENT == "production":
                raise
            return AIResult(
                content="I'm having a brief connection issue. Please try again.",
                model=self.model_name,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e),
            )

    async def generate_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> AIResult:
        if not self.is_available:
            if settings.ENVIRONMENT == "production":
                raise RuntimeError("Gemini API is not configured on the production server.")
            return AIResult(
                content="Hello! I am your Kee personal shopper (Development Mode). How may I assist your handcrafted crochet selection?",
                model="mock-dev-model",
                total_tokens=25,
            )

        start_time = time.time()
        try:
            model = genai.GenerativeModel(  # type: ignore
                model_name=self.model_name,
                system_instruction=system_instruction,
                generation_config={"temperature": temperature},
            )
            # Format history
            formatted_contents = []
            for m in messages:
                role = "user" if m.get("role") == "user" else "model"
                formatted_contents.append({"role": role, "parts": [m.get("content", "")]})

            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: model.generate_content(formatted_contents)),
                timeout=20.0
            )
            latency_ms = int((time.time() - start_time) * 1000)
            text_out = response.text.strip() if response and response.text else ""

            return AIResult(
                content=text_out,
                model=self.model_name,
                latency_ms=latency_ms,
                success=True,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Gemini generate_chat error: {e}")
            if settings.ENVIRONMENT == "production":
                raise
            return AIResult(
                content="I am momentarily unable to reach my crochet knowledge base. Please try asking again shortly!",
                model=self.model_name,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e),
            )

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector. Fallback to basic term frequency vector in dev.
        """
        if self.is_available:
            try:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: genai.embed_content(  # type: ignore
                            model="models/text-embedding-004",
                            content=text,
                            task_type="retrieval_query",
                        )
                    ),
                    timeout=8.0
                )
                if result and "embedding" in result:
                    return result["embedding"]
            except Exception as e:
                logger.warning(f"Failed to fetch Gemini embedding: {e}")

        # Deterministic lightweight pseudo-embedding (hash-based) for test/dev environments
        import hashlib
        vector = [0.0] * 64
        for token in text.lower().split():
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            vector[h % 64] += 1.0
        # Normalize
        norm = sum(v ** 2 for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector
