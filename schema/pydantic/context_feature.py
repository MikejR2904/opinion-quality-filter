from pydantic import BaseModel, Field
from datetime import datetime

class ContextFeature(BaseModel):
    chunk_id: str = Field(..., description="Unique chunk ID")
    place_id: str = Field(..., description="Place ID")
    name: str = Field(..., description="Name of the place")
    category: str = Field(..., description="Category of the place")
    address: str = Field(..., description="Address of the place")
    lat: float = Field(..., description="Latitude of the place")
    lng: float = Field(..., description="Longitude of the place")
    avg_rating: float = Field(..., description="Average rating of the place")
    num_reviews: int = Field(..., description="Number of reviews for the place")
    text_chunk: str = Field(..., description="Text chunk associated with the context")
    coverage_score: float = Field(..., description="Coverage score for the context")
    grounding_score: float = Field(..., description="Grounding score for the context")
    token_count: int = Field(..., description="Token count in the text chunk")
    source_type: str = Field(..., description="Type of source (e.g., google_places)")
    source_url: str = Field(..., description="URL of the source")
    section_title: str = Field(..., description="Title of the section")
    retrieval_timestamp: datetime = Field(..., description="Timestamp of retrieval")

    class Config:
        frozen = True
