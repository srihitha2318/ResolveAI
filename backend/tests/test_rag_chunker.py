import pytest
from app.rag.chunker import (
    PolicyChunk,
    chunk_policy_document,
    chunk_all_documents,
    _split_into_sections,
    _split_long_text,
)
from app.rag.document_loader import PolicyDocument


def _make_dummy_doc(body: str, policy_id: str = "POL-TEST-001") -> PolicyDocument:
    return PolicyDocument(
        policy_id=policy_id,
        title="Test Policy",
        version="1.0.0",
        effective_date="2026-01-01",
        scope="platform",
        seller_id="SELLER-001",
        category="electronics",
        document_type="policy",
        synthetic_policy=True,
        file_path="data/policies/test_policy.md",
        raw_content=body,
        body=body,
    )


def test_chunking_preserves_headings_and_metadata():
    """Verify chunks preserve section headings, title, and all metadata fields."""
    body = """## 1. Introduction
This is the introduction section for the test policy.

## 2. Return Window
Customers have 7 calendar days to request a replacement.

### 2.1 Exceptions
Opened software cannot be returned.
"""
    doc = _make_dummy_doc(body)
    chunks = chunk_policy_document(doc)

    assert len(chunks) == 3
    assert chunks[0].section_heading == "1. Introduction"
    assert chunks[1].section_heading == "2. Return Window"
    assert chunks[2].section_heading == "2.1 Exceptions"

    for ch in chunks:
        assert ch.policy_id == "POL-TEST-001"
        assert ch.seller_id == "SELLER-001"
        assert ch.category == "electronics"
        assert ch.policy_version == "1.0.0"
        assert ch.effective_date == "2026-01-01"
        assert ch.scope == "platform"
        assert ch.synthetic_policy is True
        assert "Test Policy" in ch.text


def test_chunk_id_stability_and_determinism():
    """Verify chunk IDs are completely deterministic across separate calls."""
    body = "## 1. Terms\nAll terms are immutable and deterministic."
    doc = _make_dummy_doc(body)

    run_1 = chunk_policy_document(doc)
    run_2 = chunk_policy_document(doc)

    assert len(run_1) == 1
    assert run_1[0].chunk_id == run_2[0].chunk_id
    assert run_1[0].content_hash == run_2[0].content_hash


def test_chunking_splits_long_sections():
    """Verify sections exceeding max_chars are split across sentence boundaries."""
    long_para = "Sentence one about electronics policy. " * 50  # ~2000 chars
    body = f"## 1. Long Details\n{long_para}"
    doc = _make_dummy_doc(body)

    # Use max_chars=500 to trigger sentence splitting
    chunks = chunk_policy_document(doc, max_chars=500)
    assert len(chunks) > 1

    # Verify no chunk exceeds reasonable boundary
    for ch in chunks:
        assert len(ch.text) <= 1200
        assert ch.chunk_id.startswith("POL-TEST-001_c")


def test_empty_sections_handled_safely():
    """Verify empty headings without content do not produce blank chunks."""
    body = """## Empty Heading 1
## Empty Heading 2
## 3. Real Heading
This section contains actual text.
"""
    doc = _make_dummy_doc(body)
    chunks = chunk_policy_document(doc)

    assert len(chunks) == 1
    assert chunks[0].section_heading == "3. Real Heading"


def test_chunk_all_documents():
    """Verify chunk_all_documents batches multiple policy documents correctly."""
    doc1 = _make_dummy_doc("## Sec A\nText A.", policy_id="POL-001")
    doc2 = _make_dummy_doc("## Sec B\nText B.", policy_id="POL-002")

    all_chunks = chunk_all_documents([doc1, doc2])
    assert len(all_chunks) == 2
    assert all_chunks[0].policy_id == "POL-001"
    assert all_chunks[1].policy_id == "POL-002"
