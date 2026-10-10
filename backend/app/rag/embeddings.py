"""
Embedding provider abstraction for semantic retrieval.
Supports lazy-loaded SentenceTransformer on CPU with in-process reuse,
and a deterministic offline MockEmbeddingProvider for testing without downloads.
"""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import List, Optional

from app.core.config import settings
from app.core.logging_config import logger


class BaseEmbeddingProvider(ABC):
    """Abstract contract for generating vector embeddings."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of strings."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generates an embedding vector for a single query string."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Returns the dimensionality of the generated vectors."""
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic pseudo-embedding provider for testing.
    Produces stable, normalized 384-dimensional vectors using SHA256 hashes.
    Requires ZERO network calls and NO model downloads.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_to_vector(self, text: str) -> List[float]:
        import re
        stop_words = {"the", "a", "an", "is", "for", "and", "or", "in", "to", "of", "with", "my", "on", "at", "it", "this", "by", "as"}
        vec = [0.0] * self.dimension
        tokens = set(re.findall(r"\w+", (text or "").lower())) - stop_words
        if not tokens:
            return [1.0 / math.sqrt(self.dimension)] * self.dimension

        # Feature hashing for unique words: words map to specific dimensions
        for t in tokens:
            idx = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % self.dimension
            vec[idx] += 1.0

        # Normalize to unit length for cosine similarity
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._hash_to_vector(query)

    def get_dimension(self) -> int:
        return self.dimension


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """
    Production embedding provider using SentenceTransformers on CPU.
    Loads the model lazily and maintains an in-process singleton instance.
    """

    _cached_model = None
    _cached_model_name: Optional[str] = None

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME

    def _get_model(self):
        """Lazily initializes the SentenceTransformer model on CPU."""
        if (
            SentenceTransformerEmbeddingProvider._cached_model is not None
            and SentenceTransformerEmbeddingProvider._cached_model_name == self.model_name
        ):
            return SentenceTransformerEmbeddingProvider._cached_model

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Initializing SentenceTransformer model: %s on CPU", self.model_name)
            model = SentenceTransformer(self.model_name, device="cpu")
            SentenceTransformerEmbeddingProvider._cached_model = model
            SentenceTransformerEmbeddingProvider._cached_model_name = self.model_name
            return model
        except Exception as e:
            logger.error("Failed to load SentenceTransformer model '%s': %s", self.model_name, e)
            raise RuntimeError(
                f"Embedding model initialization failed for '{self.model_name}'. "
                f"Ensure sentence-transformers is installed and weights are accessible. Error: {e}"
            ) from e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        # Returns numpy array, convert to list of floats for ChromaDB
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [arr.tolist() for arr in embeddings]

    def embed_query(self, query: str) -> List[float]:
        model = self._get_model()
        embedding = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    def get_dimension(self) -> int:
        model = self._get_model()
        return model.get_sentence_embedding_dimension()


_active_provider: Optional[BaseEmbeddingProvider] = None


def get_embedding_provider(provider_type: Optional[str] = None) -> BaseEmbeddingProvider:
    """
    Factory function for retrieving the configured embedding provider.
    Reuses instances across calls to prevent re-instantiation overhead.
    """
    global _active_provider
    if _active_provider is not None and provider_type is None:
        return _active_provider

    chosen = provider_type or "sentence_transformer"
    if chosen == "mock":
        return MockEmbeddingProvider()

    provider = SentenceTransformerEmbeddingProvider()
    if provider_type is None:
        _active_provider = provider
    return provider


def set_global_embedding_provider(provider: Optional[BaseEmbeddingProvider]) -> None:
    """Overrides global embedding provider (useful for test fixtures)."""
    global _active_provider
    _active_provider = provider
