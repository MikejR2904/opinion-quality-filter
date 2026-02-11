import pandas as pd
import uuid
import json
from schema.pydantic.base_schema import *
from schema.connect_db import *
from datetime import datetime

## We want to map business_name,author_name,text,photo,rating,rating_category of the original dataset
## to our defined base schema fields. Then push the mapped data to the database.

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

def push_to_postgres(reviews: list[Review], users: dict[str, User], places: dict[str, Place]) -> None:
    conn = establish_postgres_connection()
    cursor = conn.cursor()
    # Insert places to the place table
    for place in places.values():
        cursor.execute(
            """
            INSERT INTO place (place_id, name, category, address, url, lat, lng, avg_rating, num_reviews)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (place_id) DO UPDATE
            SET avg_rating = EXCLUDED.avg_rating,
                num_reviews = EXCLUDED.num_reviews;
            """, 
            (place.place_id, place.name, place.category, place.address, place.url, place.lat, place.lng, place.avg_rating, place.num_reviews)
        )
    print("Successfully inserted places to the place table")
    # Insert users to the users table
    for user in users.values():
        cursor.execute(
            """
            INSERT INTO users (user_id, name, reviews)
            VALUES (%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE
            SET reviews = EXCLUDED.reviews;
            """, 
            (user.user_id, user.name, json.dumps(user.reviews))
        )
    print("Successfully inserted users to the users table")
    # Insert reviews to the review table
    for review in reviews:
        cursor.execute(
            """
            INSERT INTO review (review_id, place_id, user_id, user_name, rating, text, language, timestamp)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (review_id) DO NOTHING;
            """, 
            (review.review_id, review.place_id, review.user_id, review.user_name, review.rating, review.text_chunk, review.language, review.timestamp)
        )
    print("Successfully inserted reviews to the review table")

if __name__ == "__main__":
    reviews, users, places = ingest_data(file_path="data/raw/kaggle/KaggleReviews.csv")
    push_to_postgres(reviews, users, places)
