from __future__ import annotations

from src.core.models import Song


class MusicRetriever:
    """Placeholder for RAG-based song retrieval.

    TODO: Future implementation steps:
      1. Generate embeddings for song metadata (title + artist + mood + genre)
      2. Store embeddings in a vector database (FAISS, ChromaDB, etc.)
      3. Accept a natural-language query and retrieve semantically similar songs
      4. Integrate with MusicRecommender to augment content-based filtering
    """

    def __init__(self) -> None:
        self.index = None  # will hold the vector store

    def ingest(self, songs: list[Song]) -> None:
        raise NotImplementedError("RAG ingestion not yet implemented")

    def retrieve(self, query: str, top_k: int = 5) -> list[Song]:
        raise NotImplementedError("RAG retrieval not yet implemented")
