from dotenv import load_dotenv
import os
import psycopg2
from qdrant_client import QdrantClient

load_dotenv() # Load environment variables from .env file from the root directory

BASE_DIR = os.path.dirname(__file__)
sql_path = os.path.join(BASE_DIR, 'postgresql', 'tables.sql')

def establish_postgres_connection():
    # Establish a connection to the PostgreSQL database run in Docker
    # These parameters should match those set in the docker-compose.yml from config folder
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT")
    )
    return conn

def establish_qdrant_connection():
    # Establish a connection to the Qdrant database run in Docker
    # These parameters should match those set in the docker-compose.yml from config folder
    host = os.getenv("QDRANT_HOST")
    port = int(os.getenv("QDRANT_PORT"))
    client = QdrantClient(host=host, port=port)
    return client

# Test connections
def init_connection():
    postgre_connection = establish_postgres_connection()
    postgre_connection.close()
    qdrant_client = establish_qdrant_connection()
    qdrant_client.close()
    print("Connection initialized successfully.")

if __name__ == "__main__":
    init_connection()