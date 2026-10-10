"""
Semantic RAG (Retrieval-Augmented Generation) package for ResolveAI.
Provides document loading, deterministic chunking, embedding generation,
persistent ChromaDB storage, and semantic policy retrieval with keyword fallback.
"""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.rag.document_loader import PolicyDocument, load_all_policy_documents
from app.rag.chunker import PolicyChunk, chunk_policy_document, chunk_all_documents
from app.rag.embeddings import (
    BaseEmbeddingProvider,
    MockEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    get_embedding_provider,
)
from app.rag.vector_store import ChromaPolicyVectorStore
from app.rag.retriever import SemanticPolicyRetriever

__all__ = [
    "PolicyDocument",
    "load_all_policy_documents",
    "PolicyChunk",
    "chunk_policy_document",
    "chunk_all_documents",
    "BaseEmbeddingProvider",
    "MockEmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
    "get_embedding_provider",
    "ChromaPolicyVectorStore",
    "SemanticPolicyRetriever",
]
