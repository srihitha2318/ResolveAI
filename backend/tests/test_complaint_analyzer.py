import pytest
from app.agents.complaint_analyzer import ComplaintAnalyzerAgent
from app.schemas.agent_schemas import ComplaintAnalysisInput


@pytest.fixture
def analyzer():
    return ComplaintAnalyzerAgent()


def test_analyze_delayed_delivery(analyzer):
    """Verify delayed delivery classification with extracted order number."""
    payload = ComplaintAnalysisInput(
        complaint_text="My order ORD-2026-001 has been delayed for 4 days. Where is my delivery?"
    )
    result = analyzer.analyze(payload)
    assert result.category == "delayed_delivery"
    assert result.order_number == "ORD-2026-001"
    assert result.image_relevant is False
    assert result.analysis_method == "rule_based"


def test_analyze_damaged_product(analyzer):
    """Verify damaged product classification and image relevance."""
    payload = ComplaintAnalysisInput(
        complaint_text="I opened the box and the monitor screen is completely cracked and broken.",
        order_number="ORD-2026-003",
    )
    result = analyzer.analyze(payload)
    assert result.category == "damaged_product"
    assert result.order_number == "ORD-2026-003"
    assert result.image_relevant is True
    assert "replacement" in result.desired_outcome.lower() or "compensation" in result.desired_outcome.lower()


def test_analyze_refund_request(analyzer):
    """Verify refund request classification."""
    payload = ComplaintAnalysisInput(
        complaint_text="I would like a full refund for my recent purchase.",
        order_number="ORD-2026-004",
    )
    result = analyzer.analyze(payload)
    assert result.category == "refund_request"
    assert "refund" in result.desired_outcome.lower()


def test_analyze_missing_order_number(analyzer):
    """Verify missing order number flags additional_info_required."""
    payload = ComplaintAnalysisInput(
        complaint_text="I am waiting for my package but tracking is not updating."
    )
    result = analyzer.analyze(payload)
    assert result.order_number is None
    assert result.additional_info_required is True
    assert "no order number" in result.limitations.lower()


def test_analyze_empty_or_whitespace_input(analyzer):
    """Verify empty or whitespace text is safely handled."""
    payload = ComplaintAnalysisInput(complaint_text="   \n\t  ")
    result = analyzer.analyze(payload)
    assert result.category == "other"
    assert result.additional_info_required is True
    assert "empty" in result.limitations.lower()


def test_analyze_unknown_or_unsupported_category(analyzer):
    """Verify unsupported inquiry falls back to other."""
    payload = ComplaintAnalysisInput(
        complaint_text="Can you tell me what the weather is like in Chicago today?",
        order_number="ORD-2026-999",
    )
    result = analyzer.analyze(payload)
    assert result.category == "other"
    assert result.order_number == "ORD-2026-999"
