import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AIChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class AIChatRequest(BaseModel):
    messages: list[AIChatMessage]


class AIChatResponse(BaseModel):
    reply: str
    recommended_product_ids: list[str] = []


class AIColorMatchResponse(BaseModel):
    recommended_colors: list[str]
    reasoning: str
    matching_product_ids: list[str] = []


class AIProductDescriptionResponse(BaseModel):
    title: str
    description: str
    tags: list[str]
    instagram_caption: str


class AIInstagramCaptionResponse(BaseModel):
    caption: str
    hashtags: list[str]


class AIReviewSummarizerResponse(BaseModel):
    summary: str
    pros: list[str]
    cons: list[str]
    sentiment: str


class AIFAQResponse(BaseModel):
    answer: str


class AIChatMessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
