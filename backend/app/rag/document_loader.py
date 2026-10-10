"""
Document loader for the ResolveAI policy knowledge base.
Reads and validates Markdown policy files listed in manifest.json, parses
YAML front matter metadata, and prepares documents for deterministic chunking.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from app.core.config import settings
from app.core.logging_config import logger


@dataclass
class PolicyDocument:
    """Represents a validated policy document loaded from disk."""
    policy_id: str
    title: str
    version: str
    effective_date: str
    scope: str
    seller_id: Optional[str]
    category: Optional[str]
    document_type: str
    synthetic_policy: bool
    file_path: str  # Relative path to project root
    raw_content: str
    body: str  # Markdown text excluding front matter
    metadata: Dict[str, Any] = field(default_factory=dict)


def parse_markdown_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Extracts YAML front matter and body from a Markdown document.
    Returns (metadata_dict, body_str).
    """
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_yaml = parts[1].strip()
            body = parts[2].strip()
            try:
                meta = yaml.safe_load(raw_yaml) or {}
                if isinstance(meta, dict):
                    return meta, body
            except Exception as e:
                logger.warning("Failed to parse YAML front matter: %s", e)
    return {}, content.strip()


def load_manifest(manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Loads and validates the policy knowledge base manifest.json.
    """
    path = manifest_path or (settings.POLICIES_DIR / "manifest.json")
    if not path.exists():
        raise FileNotFoundError(f"Policy manifest not found at: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to read or parse manifest.json: {e}")

    if "policies" not in data or not isinstance(data["policies"], list):
        raise ValueError("Invalid manifest structure: 'policies' list is required.")

    return data


def load_policy_document(
    file_path: Path,
    manifest_meta: Optional[Dict[str, Any]] = None,
    allowed_dir: Optional[Path] = None,
) -> Optional[PolicyDocument]:
    """
    Loads, validates, and parses a single policy Markdown file.
    Skips compatibility pointers and files outside allowed directory.
    """
    check_dir = allowed_dir or settings.POLICIES_DIR

    # Security check: ensure path is inside allowed directory
    resolved_path = file_path.resolve()
    try:
        resolved_path.relative_to(check_dir.resolve())
    except ValueError:
        logger.error("Security violation: path %s is outside allowed policy directory %s", file_path, check_dir)
        return None

    if not resolved_path.exists() or not resolved_path.is_file():
        logger.warning("Policy file not found: %s", resolved_path)
        return None

    try:
        raw_content = resolved_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("Could not read policy file %s: %s", resolved_path, e)
        return None

    frontmatter, body = parse_markdown_frontmatter(raw_content)

    # Merge metadata: frontmatter takes precedence, backed by manifest entry
    meta: Dict[str, Any] = {}
    if manifest_meta:
        meta.update(manifest_meta)
    meta.update(frontmatter)

    # Check for compatibility pointers or legacy indicators
    doc_type = meta.get("document_type", "policy")
    policy_id = meta.get("policy_id", "")
    if doc_type == "compatibility_pointer" or "LEGACY" in policy_id or resolved_path.name == "return_policy.md":
        logger.info("Skipping compatibility pointer document: %s (%s)", resolved_path.name, policy_id)
        return None

    # Validate mandatory metadata fields
    required_keys = ["policy_id", "title", "version", "effective_date", "scope"]
    missing = [k for k in required_keys if not meta.get(k)]
    if missing:
        logger.warning("Skipping policy %s due to missing mandatory metadata: %s", resolved_path.name, missing)
        return None

    # Compute relative path to project root
    try:
        rel_path = str(resolved_path.relative_to(settings.project_root)).replace("\\", "/")
    except ValueError:
        rel_path = str(resolved_path).replace("\\", "/")

    return PolicyDocument(
        policy_id=str(meta["policy_id"]).strip(),
        title=str(meta["title"]).strip(),
        version=str(meta["version"]).strip(),
        effective_date=str(meta["effective_date"]).strip(),
        scope=str(meta["scope"]).strip(),
        seller_id=meta.get("seller_id"),
        category=meta.get("category"),
        document_type=str(doc_type),
        synthetic_policy=bool(meta.get("synthetic_policy", True)),
        file_path=rel_path,
        raw_content=raw_content,
        body=body,
        metadata=meta,
    )


def load_all_policy_documents(
    policies_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> Tuple[List[PolicyDocument], List[str]]:
    """
    Loads all active policy documents according to the manifest.
    Returns: (list_of_documents, list_of_skipped_files)
    """
    p_dir = policies_dir or settings.POLICIES_DIR
    m_path = manifest_path or (p_dir / "manifest.json")

    documents: List[PolicyDocument] = []
    skipped: List[str] = []

    if not m_path.exists():
        logger.warning("Manifest not found at %s. Scanning policy directory directly.", m_path)
        for md_file in sorted(p_dir.glob("*.md")):
            doc = load_policy_document(md_file, allowed_dir=p_dir)
            if doc:
                documents.append(doc)
            else:
                skipped.append(md_file.name)
        return documents, skipped

    try:
        manifest_data = load_manifest(m_path)
    except Exception as e:
        logger.error("Error reading manifest: %s", e)
        return [], [str(e)]

    for entry in manifest_data.get("policies", []):
        file_path_str = entry.get("file_path")
        if not file_path_str:
            continue

        target_path = settings.project_root / file_path_str
        doc = load_policy_document(target_path, manifest_meta=entry, allowed_dir=p_dir)
        if doc:
            documents.append(doc)
        else:
            skipped.append(file_path_str)

    return documents, skipped
