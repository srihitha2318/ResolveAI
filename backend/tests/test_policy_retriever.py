from pathlib import Path
import pytest
from app.agents.policy_retriever import PolicyRetrieverAgent
from app.schemas.agent_schemas import PolicySearchInput


@pytest.fixture
def retriever():
    return PolicyRetrieverAgent()


def test_policy_retrieval_relevant_document(retriever):
    """Verify retrieval returns relevant passage from return_policy.md."""
    payload = PolicySearchInput(query="return window 30 days replacement")
    result = retriever.retrieve(payload)

    assert result.found_relevant is True
    assert len(result.passages) > 0
    assert any(p.document_name in ("return_policy.md", "platform_return_refund_policy.md") for p in result.passages)
    assert any("30 calendar days" in p.passage for p in result.passages)


def test_policy_retrieval_no_matching_passage(retriever):
    """Verify query with no matching keywords returns found_relevant=False and explanation."""
    payload = PolicySearchInput(query="quantum teleportation hyperdrive antimatter")
    result = retriever.retrieve(payload)

    assert result.found_relevant is False
    assert len(result.passages) == 0
    assert "no matching policy passages" in result.explanation.lower()


def test_policy_retrieval_missing_directory(tmp_path):
    """Verify policy search handles non-existent policy directory safely."""
    missing_dir = tmp_path / "nonexistent_policies_dir"
    custom_retriever = PolicyRetrieverAgent(policies_dir=missing_dir)

    payload = PolicySearchInput(query="refund policy")
    result = custom_retriever.retrieve(payload)

    assert result.found_relevant is False
    assert len(result.passages) == 0


def test_policy_retrieval_empty_query(retriever):
    """Verify empty query returns safe empty result."""
    payload = PolicySearchInput(query="   ")
    result = retriever.retrieve(payload)

    assert result.found_relevant is False
    assert len(result.passages) == 0


def test_policy_retrieval_multiple_documents(retriever):
    """Verify retrieval across multiple policy documents (return and shipping)."""
    # "carrier" or "shipping" is in shipping_policy.md; "refund" is in both
    payload = PolicySearchInput(query="shipping delayed carrier lost package")
    result = retriever.retrieve(payload)

    assert result.found_relevant is True
    assert any("shipping_policy.md" in p.document_name for p in result.passages)
