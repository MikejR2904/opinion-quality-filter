import pandas as pd
import uuid
from schema.pydantic.base_schema import *
from datetime import datetime

## We want to map business_name,author_name,text,photo,rating,rating_category of the original dataset
## to our defined base schema fields.

def ingest_data(file_path: str) -> tuple[list[Review], dict[str, User], dict[str, Place]]:
    df = pd.read_csv(file_path)
    reviews: list[Review] = []
    users: dict[str, User] = {}
    places: dict[str, Place] = {}
    for _, row in df.iterrows():
        # Generate IDs to be mapped to the schema for SQL ingestion
        place_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, row["business_name"]))
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, row["author_name"]))
        review_id = str(uuid.uuid4())
        # Build review object 
        review = Review(
            review_id=review_id,
            place_id=place_id,
            user_id=user_id,
            user_name=row["author_name"],
            rating=float(row["rating"]),
            text_chunk=row["text"],
            language="en",  # This dataset is 100% English
            timestamp=datetime.now() # Take now as timestamp
        )
        reviews.append(review)
        # Build user object if not exists; user can have multiple reviews
        if user_id not in users:
            users[user_id] = User(user_id=user_id, name=row["author_name"], reviews=[])
        users[user_id].reviews.append(review_id)
        # Build place object if not exists; place can have multiple reviews
        if place_id not in places:
            places[place_id] = Place(
                place_id=place_id,
                name=row["business_name"],
                category=row.get("rating_category", ""),
                address="", url="", lat=0.0, lng=0.0,
                avg_rating=float(row["rating"]),
                num_reviews=1
            )
        else:
            # Update place stats if reviewed before
            places[place_id].num_reviews += 1
            places[place_id].avg_rating = (
                places[place_id].avg_rating * (places[place_id].num_reviews - 1) + float(row["rating"])
            ) / places[place_id].num_reviews

    return reviews, users, places

