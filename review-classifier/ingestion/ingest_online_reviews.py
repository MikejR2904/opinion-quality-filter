import pandas as pd
import uuid
import json
from schema.pydantic.base_schema import *
from schema.connect_db import *
from datetime import datetime

## We want to map name,address,category,overall_rating,review_count,website,google_maps_url,lat,lng,author,review_rating,review_text,relative_time,date_retrieved,calculated_date,review_id to our dataset

def ingest_data(file_path: str) -> tuple[list[Review], dict[str, User], dict[str, Place]]:
    df = pd.read_csv(file_path)
    reviews: list[Review] = []
    users: dict[str, User] = {}
    places: dict[str, Place] = {}
    for _, row in df.iterrows():
        # Generate IDs to be mapped to the schema for SQL ingestion
        place_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, row["name"]))
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, row["author"]))
        review_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, row["review_id"]))
        if pd.isna(row.get("calculated_date")):
            continue
        # Build review object 
        review = Review(
            review_id=review_id,
            place_id=place_id,
            user_id=user_id,
            user_name=row["author"],
            rating=float(row["review_rating"]),
            text_chunk=row["review_text"],
            language="",  # We don't know yet the language, leave it to preprocessing
            timestamp= row["calculated_date"]
        )
        reviews.append(review)
        # Build user object if not exists; user can have multiple reviews
        if user_id not in users:
            users[user_id] = User(user_id=user_id, name=row["author"], reviews=[])
        users[user_id].reviews.append(review_id)
        # Build place object if not exists; we fetch statistics from Google Maps
        if place_id not in places:
            places[place_id] = Place(
                place_id=place_id,
                name=row["name"],
                category=row["category"],
                address=row["address"],
                url=row["website"] if row["website"] else row["google_maps_url"], 
                lat=float(row["lat"]), 
                lng=float(row["lng"]),
                avg_rating=float(row["overall_rating"]),
                num_reviews=int(row["review_count"])
            )
            
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
    reviews, users, places = ingest_data(file_path="data/raw/google_places/google_maps_reviews.csv")
    push_to_postgres(reviews, users, places)
