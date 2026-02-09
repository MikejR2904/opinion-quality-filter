from pydantic import BaseModel, Field
from datetime import datetime

class Place(BaseModel):
    place_id: str = Field(..., description="Unique place ID")
    name: str = Field(..., description="Name of the place")
    category: str = Field(..., description="Category of the place")
    address: str = Field(..., description="Address of the place")
    url: str = Field(..., description="URL of the place")
    lat: float = Field(..., description="Latitude of the place")
    lng: float = Field(..., description="Longitude of the place")
    avg_rating: float = Field(..., description="Average rating of the place")
    num_reviews: int = Field(..., description="Number of reviews for the place")

class User(BaseModel):
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="Name of the user")
    reviews: list = Field(..., description="List of review IDs")

class Review(BaseModel):
    review_id: str = Field(..., description="Unique review ID")
    place_id: str = Field(..., description="Place ID")
    user_id: str = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    rating: float = Field(..., description="Rating")
    text_chunk: str = Field(..., description="Text chunk")
    language: str = Field(..., description="Language")
    timestamp: datetime = Field(..., description="Timestamp")