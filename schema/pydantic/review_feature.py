from pydantic import BaseModel, Field
from datetime import datetime

class ReviewFeature(BaseModel):
    review_id: str = Field(..., description="Unique review ID")
    place_id: str = Field(..., description="Place ID")
    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    pos_diversity: float = Field(..., description="Part-of-speech diversity score")
    noun_verb_ratio: float = Field(..., description="Ratio of nouns to verbs")
    coverage_score: float = Field(..., description="Coverage score")
    grounding_score: float = Field(..., description="Grounding score")
    token_count: int = Field(..., description="Token count")
    entropy_score: float = Field(..., description="Entropy score")
    exclamation_count: int = Field(..., description="Exclamation count")
    emoji_count: int = Field(..., description="Emoji count")
    sentiment_polarity: float = Field(..., description="Sentiment polarity")
    repetition_score: float = Field(..., description="Repetition score")
    rating: float = Field(..., description="Rating")
    text_chunk: str = Field(..., description="Text chunk")
    language: str = Field(..., description="Language")
    source: str = Field(..., description="Data source, e.g. google_places")
    timestamp: datetime = Field(..., description="Timestamp")

    class Config:
        frozen = True
