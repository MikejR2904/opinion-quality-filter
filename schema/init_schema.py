from dotenv import load_dotenv
import os, json
from connect_db import establish_postgres_connection, establish_qdrant_connection
from qdrant_client.http.models import VectorParams, PayloadSchemaType

BASE_DIR = os.path.dirname(__file__)
sql_path = os.path.join(BASE_DIR, 'postgresql', 'tables.sql')
qdrant_path = os.path.join(BASE_DIR, 'qdrant')

def init_postgres_schema():
    conn = establish_postgres_connection()
    cursor = conn.cursor()
    with open(sql_path, 'r') as f:
        cursor.execute(f.read())
    conn.commit()
    cursor.close()
    conn.close()
    print("PostgreSQL schema initialized successfully.")

def init_qdrant_schema():
    client = establish_qdrant_connection()
    for schema_file in ["context_feature.json", "review_feature.json"]: # List of Qdrant schema files
        schema_path = os.path.join(qdrant_path, schema_file)
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        # Recreate collection based on schema
        collection_name = schema["name"]
        vectors_config = {
            name: VectorParams(size=cfg["size"], distance=cfg["distance"])
            for name, cfg in schema["vectors"].items()
        }
        payload_schema = {
            field: PayloadSchemaType(value_type)
            for field, value_type in schema["payload_schema"].items()
        } # Currently not supported by QdrantClient directly
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=vectors_config
        )
        print(f"Initialized Qdrant collection: {collection_name}")
    client.close()
    print("Qdrant schema initialized successfully.")    

if __name__ == "__main__":
    init_postgres_schema()
    init_qdrant_schema()