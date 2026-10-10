from pathlib import Path
import pytest

from app.rag.chunker import chunk_policy_document
from app.rag.document_loader import PolicyDocument
from app.rag.embeddings import MockEmbeddingProvider
from app.rag.vector_store import ChromaPolicyVectorStore


@pytest.fixture
def temp_vector_store(tmp_path):
    """Provides an isolated ChromaPolicyVectorStore in a temporary directory."""
    provider = MockEmbeddingProvider()
    store = ChromaPolicyVectorStore(
        persist_dir=tmp_path / "test_chroma",
        collection_name="test_collection",
        embedding_provider=provider,
    )
    return store


def _create_sample_doc(policy_id: str, body: str, seller_id: str = "SELLER-001", category: str = "electronics") -> PolicyDocument:
    return PolicyDocument(
        policy_id=policy_id,
        title=f"Title {policy_id}",
        version="1.0.0",
        effective_date="2026-01-01",
        scope="seller" if seller_id else "platform",
        seller_id=seller_id,
        category=category,
        document_type="policy",
        synthetic_policy=True,
        file_path=f"data/policies/{policy_id}.md",
        raw_content=body,
        body=body,
    )


def test_empty_collection_initialization(temp_vector_store):
    """Verify vector store initializes cleanly with count 0."""
    assert temp_vector_store.count() == 0


def test_idempotent_indexing_and_updates(temp_vector_store):
    """Verify initial indexing adds chunks, second indexing is idempotent, and update syncs cleanly."""
    doc = _create_sample_doc("POL-TEST-001", "## Section 1\nOriginal text content.")
    chunks = chunk_policy_document(doc)

    # 1. First indexing run
    stats1 = temp_vector_store.index_chunks(chunks)
    assert stats1["added"] == 1
    assert stats1["updated"] == 0
    assert stats1["unchanged"] == 0
    assert stats1["deleted"] == 0
    assert temp_vector_store.count() == 1

    # 2. Repeated run with identical chunks -> 100% idempotent
    stats2 = temp_vector_store.index_chunks(chunks)
    assert stats2["added"] == 0
    assert stats2["updated"] == 0
    assert stats2["unchanged"] == 1
    assert stats2["deleted"] == 0
    assert temp_vector_store.count() == 1

    # 3. Policy update (modified body)
    updated_doc = _create_sample_doc("POL-TEST-001", "## Section 1\nUpdated text content with modified terms.")
    updated_chunks = chunk_policy_document(updated_doc)
    stats3 = temp_vector_store.index_chunks(updated_chunks)
    # The updated chunk has a different ID/hash, so stale chunk is deleted and new chunk is added
    assert stats3["total"] == 1
    assert temp_vector_store.count() == 1


def test_stale_chunk_purged_when_section_removed(temp_vector_store):
    """Verify obsolete chunks are deleted when a section is removed from a policy."""
    doc_two_sec = _create_sample_doc(
        "POL-TEST-002",
        "## Section A\nKeep this section.\n\n## Section B\nDelete this section later.",
    )
    chunks_initial = chunk_policy_document(doc_two_sec)
    temp_vector_store.index_chunks(chunks_initial)
    assert temp_vector_store.count() == 2

    # Now re-index with Section B removed
    doc_one_sec = _create_sample_doc("POL-TEST-002", "## Section A\nKeep this section.")
    chunks_reduced = chunk_policy_document(doc_one_sec)
    stats = temp_vector_store.index_chunks(chunks_reduced)

    assert stats["deleted"] == 1
    assert stats["unchanged"] == 1
    assert temp_vector_store.count() == 1


def test_query_with_metadata_filters(temp_vector_store):
    """Verify vector search applies seller_id and category filters."""
    doc_elec = _create_sample_doc(
        "POL-ELEC-001", "## Electronics\nLaptop screen replacement policy.",
        seller_id="SELLER-001", category="electronics"
    )
    doc_fash = _create_sample_doc(
        "POL-FASH-001", "## Fashion\nShirt size exchange policy.",
        seller_id="SELLER-002", category="fashion"
    )

    chunks = chunk_policy_document(doc_elec) + chunk_policy_document(doc_fash)
    temp_vector_store.index_chunks(chunks)

    # Query with seller filter
    res_seller = temp_vector_store.query("policy", seller_id="SELLER-001")
    assert len(res_seller) >= 1
    for r in res_seller:
        assert r["metadata"]["seller_id"] == "SELLER-001"

    # Query with category filter
    res_cat = temp_vector_store.query("policy", category="fashion")
    assert len(res_cat) >= 1
    for r in res_cat:
        assert r["metadata"]["category"] == "fashion"
