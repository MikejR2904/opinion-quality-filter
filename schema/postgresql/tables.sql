CREATE EXTENSION IF NOT EXISTS vector;

-- Place table
CREATE TABLE place (
    place_id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    address TEXT,
    url TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    avg_rating DOUBLE PRECISION,
    num_reviews INT
);

-- User table
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    reviews JSONB
);

-- Review table
CREATE TABLE review (
    review_id UUID PRIMARY KEY,
    place_id UUID REFERENCES place(place_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    user_name TEXT,
    rating DOUBLE PRECISION,
    text TEXT,
    language TEXT,
    timestamp TIMESTAMP
);

-- Review Feature Store
CREATE TABLE review_feature_store (
    review_id UUID PRIMARY KEY REFERENCES review(review_id) ON DELETE CASCADE,
    place_id UUID REFERENCES place(place_id) ON DELETE CASCADE,
    pos_diversity DOUBLE PRECISION,
    noun_verb_ratio DOUBLE PRECISION,
    coverage_score DOUBLE PRECISION,
    grounding_score DOUBLE PRECISION,
    token_count INT,
    entropy_score DOUBLE PRECISION,
    exclamation_count INT,
    emoji_count INT,
    sentiment_polarity DOUBLE PRECISION,
    repetition_score DOUBLE PRECISION,
    semantic_embedding VECTOR(768),
    hybrid_vector VECTOR(768), 
    rating DOUBLE PRECISION,
    text_chunk TEXT,
    language TEXT,
    source TEXT,
    timestamp TIMESTAMP,
    result JSONB
);

-- Context Feature Store
CREATE TABLE context_feature_store (
    chunk_id UUID PRIMARY KEY,
    place_id UUID REFERENCES place(place_id) ON DELETE CASCADE,
    name TEXT,
    category TEXT,
    address TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    avg_rating DOUBLE PRECISION,
    num_reviews INT,
    text_chunk TEXT,
    coverage_score DOUBLE PRECISION,
    grounding_score DOUBLE PRECISION,
    token_count INT,
    source_type TEXT,
    section_title TEXT,
    timestamp TIMESTAMP,
    embedding VECTOR(768)
);
