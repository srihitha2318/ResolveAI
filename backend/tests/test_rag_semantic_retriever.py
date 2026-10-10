from pathlib import Path
import pytest

from app.core.config import settings
from app.rag.chunker import chunk_policy_document
from app.rag.document_loader import PolicyDocument
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.index_policies import run_indexing
from app.rag.retriever import SemanticPolicyRetriever
from app.rag.vector_store import ChromaPolicyVectorStore
from app.schemas.agent_schemas import PolicySearchInput


@pytest.fixture
def indexed_vector_store(tmp_path):
    """Initializes and indexes real policy documents with mock embeddings in an isolated dir."""
    persist_dir = tmp_path / "test_rag_store"
    res = run_indexing(
        persist_dir=persist_dir,
        use_mock_embeddings=True,
        force_reindex=True,
    )
    assert res["success"] is True

    store = ChromaPolicyVectorStore(
        persist_dir=persist_dir,
        collection_name=settings.CHROMA_COLLECTION_NAME,
        embedding_provider=MockEmbeddingProvider(),
    )
    return store


@pytest.fixture
def semantic_retriever(indexed_vector_store):
    return SemanticPolicyRetriever(
        vector_store=indexed_vector_store,
        embedding_provider=MockEmbeddingProvider(),
        distance_threshold=settings.RAG_DISTANCE_THRESHOLD,
    )


def test_semantic_retrieval_electronics_query(semantic_retriever):
    """Verify semantic retrieval retrieves electronics policy for technical defect query."""
    res = semantic_retriever.retrieve(
        query="dead on arrival hardware defect replacement",
        category="electronics",
    )
    assert res.found_relevant is True
    assert len(res.passages) > 0
    assert "POL-CAT-001" in res.policy_ids
    assert any("electronics" in p.document_name.lower() for p in res.passages)
    assert res.conflict_status == "resolved"


def test_semantic_retrieval_fashion_query(semantic_retriever):
    """Verify semantic retrieval retrieves fashion policy for apparel size mismatch."""
    res = semantic_retriever.retrieve(
        query="size exchange brand tags footwear clothing",
        category="fashion",
    )
    assert res.found_relevant is True
    assert len(res.passages) > 0
    assert any("fashion" in p.document_name.lower() for p in res.passages)


def test_semantic_retrieval_home_appliance_query(semantic_retriever):
    """Verify home appliance query retrieves appliance policy and technician requirements."""
    res = semantic_retriever.retrieve(
        query="transit damage cooling technician inspection",
        category="home_appliances",
    )
    assert res.found_relevant is True
    assert len(res.passages) > 0
    assert any("home_appliances" in p.document_name.lower() for p in res.passages)


def test_semantic_retrieval_seller_filtering(semantic_retriever):
    """Verify seller_id filter restricts results to the specified seller."""
    res = semantic_retriever.retrieve(
        query="Deccan Digital electronics replacement warranty",
        seller_id="SELLER-001",
    )
    assert res.found_relevant is True
    assert "POL-SEL-001" in res.policy_ids


def test_semantic_retrieval_empty_query(semantic_retriever):
    """Verify empty query returns insufficient_evidence without errors."""
    res = semantic_retriever.retrieve(query="   ")
    assert res.found_relevant is False
    assert res.insufficient_evidence is True
    assert len(res.passages) == 0


def test_semantic_retrieval_irrelevant_query(semantic_retriever):
    """Verify query with no semantic relevance returns insufficient evidence."""
    res = semantic_retriever.retrieve(query="quantum teleportation hyperdrive antimatter")
    assert res.found_relevant is False
    assert res.insufficient_evidence is True
    assert len(res.passages) == 0
    assert "no matching policy passages" in res.explanation.lower()


def test_semantic_retrieval_fallback_on_empty_store(tmp_path):
    """Verify retriever falls back to keyword search if vector store is empty."""
    empty_store = ChromaPolicyVectorStore(
        persist_dir=tmp_path / "empty_store",
        collection_name="empty_coll",
        embedding_provider=MockEmbeddingProvider(),
    )
    retriever = SemanticPolicyRetriever(vector_store=empty_store)

    res = retriever.retrieve(query="30 calendar days return window")
    assert res.found_relevant is True
    assert res.retrieval_method == "keyword_fallback"
    assert len(res.passages) > 0


def test_semantic_retrieval_fallback_on_error(monkeypatch, semantic_retriever):
    """Verify vector store query exceptions trigger keyword fallback cleanly."""
    def broken_query(*args, **kwargs):
        raise RuntimeError("Simulated ChromaDB disk failure")

    monkeypatch.setattr(semantic_retriever.vector_store, "query", broken_query)

    res = semantic_retriever.retrieve(query="return window 30 days replacement")
    assert res.found_relevant is True
    assert res.retrieval_method == "keyword_fallback"
    assert len(res.passages) > 0


def test_provenance_and_exact_passages(semantic_retriever):
    """Verify exact policy passages and provenance metadata are preserved."""
    res = semantic_retriever.retrieve(query="return window 30 days")
    assert res.found_relevant is True
    for p in res.passages:
        assert p.document_name.endswith(".md")
        assert len(p.passage) > 20
        assert p.policy_id is not None
        assert p.scope in ("platform", "category", "seller")


def test_indexing_command_module_execution():
    """Verify index_policies run_indexing executes safely and idempotently."""
    res1 = run_indexing(use_mock_embeddings=True)
    assert res1["success"] is True
    assert res1["documents_loaded"] >= 15

    # Run second time to verify idempotency
    res2 = run_indexing(use_mock_embeddings=True)
    assert res2["success"] is True
    assert res2["sync_stats"]["added"] == 0
    assert res2["sync_stats"]["unchanged"] >= 15
