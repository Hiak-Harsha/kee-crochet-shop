from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class AIResult:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    latency_ms: int = 0
    success: bool = True
    error_message: str | None = None


class AIProvider(ABC):
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        max_output_tokens: int = 1000,
    ) -> AIResult:
        pass

    @abstractmethod
    async def generate_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> AIResult:
        pass

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        pass
