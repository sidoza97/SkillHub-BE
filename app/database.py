import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from .config import settings

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
employee_collection = chroma_client.get_or_create_collection(
    name="employee_profiles",
    embedding_function=DefaultEmbeddingFunction(),
)
