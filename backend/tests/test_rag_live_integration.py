"""
Live integration test for ResolveAI Level 3 Semantic RAG.
Verifies real SentenceTransformers embeddings and ChromaDB persistent storage.
Note: Requires downloaded model weights in local cache (huggingface cache).
"""

from pathlib import Path
import pytest

from app.core.config import settings
from app.rag.embeddings import SentenceTransformerEmbeddingProvider
from app.rag.retriever import SemanticPolicyRetriever
from app.rag.vector_store import ChromaPolicyVectorStore


@pytest.mark.integration
def test_live_sentence_transformer_and_chroma_semantic_retrieval():
    """
    Live end-to-end integration test executing real SentenceTransformer inference
    against the persistent ChromaDB collection.
    """
    # 1. Initialize real embedding provider and persistent store
    provider = SentenceTransformerEmbeddingProvider()
    store = ChromaPolicyVectorStore(
        persist_dir=settings.VECTOR_STORE_DIR,
        collection_name=settings.CHROMA_COLLECTION_NAME,
        embedding_provider=provider,
    )

    assert store.count() > 0, "Persistent vector store must contain indexed chunks"

    retriever = SemanticPolicyRetriever(
        vector_store=store,
        embedding_provider=provider,
        distance_threshold=settings.RAG_DISTANCE_THRESHOLD,
    )

    # 2. Test live semantic search for damaged electronics
    result = retriever.retrieve(
        query="customer unboxed defective laptop with broken display wanting replacement",
        category="electronics",
    )

    assert result.found_relevant is True
    assert result.retrieval_method == "semantic_search"
    assert len(result.passages) > 0
    assert "POL-CAT-001" in result.policy_ids
    assert result.conflict_status == "resolved"

    first_passage = result.passages[0]
    assert first_passage.passage is not None
    assert len(first_passage.passage) > 20
    assert first_passage.document_name == "category_electronics_policy.md"
    assert first_passage.scope == "category"
    assert "cosine_dist:" in first_passage.matched_terms[0]

    # 3. Test irrelevant query produces insufficient evidence
    irrelevant_result = retriever.retrieve(
        query="quantum teleportation hyperdrive antimatter warp core",
    )
    assert irrelevant_result.found_relevant is False
    assert len(irrelevant_result.passages) == 0
    assert irrelevant_result.insufficient_evidence is True
