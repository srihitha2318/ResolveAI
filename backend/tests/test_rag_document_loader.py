from pathlib import Path
import pytest

from app.core.config import settings
from app.rag.document_loader import (
    PolicyDocument,
    load_manifest,
    load_policy_document,
    load_all_policy_documents,
    parse_markdown_frontmatter,
)


def test_load_manifest_valid():
    """Verify manifest.json is loaded and contains 15 required policies."""
    data = load_manifest()
    assert "policies" in data
    assert len(data["policies"]) >= 15
    for p in data["policies"]:
        assert "policy_id" in p
        assert "file_path" in p


def test_load_manifest_missing_file(tmp_path):
    """Verify load_manifest raises FileNotFoundError for non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "nonexistent_manifest.json")


def test_load_manifest_invalid_json(tmp_path):
    """Verify load_manifest raises ValueError for invalid JSON syntax."""
    bad_manifest = tmp_path / "bad_manifest.json"
    bad_manifest.write_text("{not_valid_json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(bad_manifest)


def test_load_policy_document_valid():
    """Verify loading an active policy extracts metadata and prose body."""
    target_file = settings.POLICIES_DIR / "category_electronics_policy.md"
    doc = load_policy_document(target_file)

    assert doc is not None
    assert doc.policy_id == "POL-CAT-001"
    assert doc.category == "electronics"
    assert doc.scope == "category"
    assert doc.synthetic_policy is True
    assert "Return & Replacement Window" in doc.body
    # Ensure front matter is stripped from doc.body
    assert not doc.body.startswith("---")


def test_load_policy_document_skips_compatibility_pointer():
    """Verify return_policy.md (compatibility pointer) is safely skipped."""
    pointer_file = settings.POLICIES_DIR / "return_policy.md"
    doc = load_policy_document(pointer_file)
    assert doc is None


def test_load_policy_document_outside_allowed_dir(tmp_path):
    """Verify security check prevents loading files outside allowed policy directory."""
    outside_file = tmp_path / "malicious_policy.md"
    outside_file.write_text(
        "---\npolicy_id: POL-HACK-001\ntitle: Hack\nversion: 1.0\neffective_date: 2026-01-01\nscope: platform\n---\nBody",
        encoding="utf-8",
    )
    doc = load_policy_document(outside_file, allowed_dir=settings.POLICIES_DIR)
    assert doc is None


def test_load_policy_document_missing_file():
    """Verify loader handles non-existent policy file without crashing."""
    missing_file = settings.POLICIES_DIR / "missing_file_xyz.md"
    doc = load_policy_document(missing_file)
    assert doc is None


def test_load_all_policy_documents():
    """Verify loading all policies returns 15 valid documents and tracks skipped pointers."""
    docs, skipped = load_all_policy_documents()
    assert len(docs) >= 15
    policy_ids = {d.policy_id for d in docs}
    assert "POL-PLAT-001" in policy_ids
    assert "POL-SEL-001" in policy_ids
    assert "POL-CAT-001" in policy_ids
    # Legacy pointer must not be in active docs
    assert "POL-PLAT-002-LEGACY" not in policy_ids
