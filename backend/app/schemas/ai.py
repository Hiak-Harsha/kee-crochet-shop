from pydantic import BaseModel


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
