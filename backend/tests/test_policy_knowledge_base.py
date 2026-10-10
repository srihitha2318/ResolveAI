import json
from pathlib import Path
import pytest
from app.core.config import settings
from app.tools.support_tools import (
    search_policy_documents,
    parse_policy_frontmatter,
)

REQUIRED_POLICY_FILES = [
    "platform_customer_support_policy.md",
    "platform_return_refund_policy.md",
    "platform_cancellation_policy.md",
    "platform_payment_billing_policy.md",
    "platform_escalation_policy.md",
    "platform_customer_communication_policy.md",
    "platform_fraud_dispute_review_policy.md",
    "category_electronics_policy.md",
    "category_fashion_policy.md",
    "category_home_appliances_policy.md",
    "category_general_merchandise_policy.md",
    "seller_deccan_digital_policy.md",
    "seller_vastrakart_policy.md",
    "seller_grihamart_policy.md",
    "shipping_policy.md",
]


def test_all_required_policy_files_exist():
    """Verify all 15 required policy documents exist in data/policies."""
    policies_dir = Path(settings.POLICIES_DIR)
    assert policies_dir.exists(), f"Policies directory {policies_dir} does not exist"

    for filename in REQUIRED_POLICY_FILES:
        filepath = policies_dir / filename
        assert filepath.exists(), f"Required policy file {filename} is missing"
        assert filepath.stat().st_size > 500, f"Policy file {filename} is too small / placeholder"


def test_canonical_and_legacy_return_policy_compatibility():
    """Verify return_policy.md exists and references canonical platform_return_refund_policy.md."""
    policies_dir = Path(settings.POLICIES_DIR)
    legacy_file = policies_dir / "return_policy.md"
    canonical_file = policies_dir / "platform_return_refund_policy.md"

    assert legacy_file.exists()
    assert canonical_file.exists()

    content = legacy_file.read_text(encoding="utf-8")
    assert "platform_return_refund_policy.md" in content or "POL-PLAT-002" in content
    assert "30 calendar days" in content  # Preserved backward compatible standard


def test_manifest_json_validity():
    """Verify manifest.json exists, is valid JSON, and indexes all required policies."""
    policies_dir = Path(settings.POLICIES_DIR)
    manifest_file = policies_dir / "manifest.json"
    assert manifest_file.exists()

    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert "policies" in data
    assert isinstance(data["policies"], list)
    assert len(data["policies"]) >= 15

    indexed_files = {Path(p["file_path"]).name for p in data["policies"]}
    for req_file in REQUIRED_POLICY_FILES:
        assert req_file in indexed_files, f"{req_file} missing from manifest.json"


def test_policy_metadata_frontmatter():
    """Verify every policy file has valid YAML front matter with required metadata keys."""
    policies_dir = Path(settings.POLICIES_DIR)
    required_keys = [
        "policy_id",
        "title",
        "version",
        "effective_date",
        "scope",
        "synthetic_policy",
        "document_type",
    ]

    for filename in REQUIRED_POLICY_FILES:
        filepath = policies_dir / filename
        content = filepath.read_text(encoding="utf-8")
        meta, body = parse_policy_frontmatter(content)

        assert meta, f"{filename} is missing YAML front matter"
        for key in required_keys:
            assert key in meta, f"{filename} front matter is missing key: {key}"

        assert meta["synthetic_policy"] is True
        assert len(body.split()) >= 200, f"{filename} has insufficient word count ({len(body.split())} words)"


def test_seller_policies_distinct_and_correct_ids():
    """Verify the 3 fictional seller policies have distinct IDs, categories, and content."""
    policies_dir = Path(settings.POLICIES_DIR)

    s1_path = policies_dir / "seller_deccan_digital_policy.md"
    s2_path = policies_dir / "seller_vastrakart_policy.md"
    s3_path = policies_dir / "seller_grihamart_policy.md"

    m1, b1 = parse_policy_frontmatter(s1_path.read_text(encoding="utf-8"))
    m2, b2 = parse_policy_frontmatter(s2_path.read_text(encoding="utf-8"))
    m3, b3 = parse_policy_frontmatter(s3_path.read_text(encoding="utf-8"))

    # Seller IDs
    assert m1["seller_id"] == "SELLER-001"
    assert m2["seller_id"] == "SELLER-002"
    assert m3["seller_id"] == "SELLER-003"

    # Distinct policy IDs
    assert m1["policy_id"] == "POL-SEL-001"
    assert m2["policy_id"] == "POL-SEL-002"
    assert m3["policy_id"] == "POL-SEL-003"

    # Meaningfully distinct content
    assert "Deccan Digital" in b1
    assert "VastraKart" in b2
    assert "GrihaMart" in b3

    assert b1 != b2
    assert b2 != b3
    assert b1 != b3


def test_search_policy_documents_filtering():
    """Verify search_policy_documents supports filtering by seller_id, category, and scope."""
    # Search by seller
    seller_results = search_policy_documents(
        query="warranty replacement",
        seller_id="SELLER-001",
    )
    assert seller_results["count"] > 0
    for p in seller_results["passages"]:
        assert p.get("seller_id") == "SELLER-001" or p.get("scope") in ("platform", "category")

    # Search by category
    cat_results = search_policy_documents(
        query="size exchange",
        category="fashion",
    )
    assert cat_results["count"] > 0
    assert any("fashion" in p.get("document_name", "").lower() for p in cat_results["passages"])
