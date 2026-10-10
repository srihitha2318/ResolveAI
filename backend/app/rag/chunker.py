"""
Deterministic policy-aware chunking module.
Splits Markdown policy documents along section headings, preserves metadata,
maintains heading context, bounds chunk size, and generates deterministic chunk IDs.
"""

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Dict, List

from app.rag.document_loader import PolicyDocument


@dataclass
class PolicyChunk:
    """Represents an indexed policy chunk with full provenance metadata."""
    chunk_id: str
    policy_id: str
    policy_title: str
    policy_version: str
    effective_date: str
    scope: str
    seller_id: str  # Non-null string for ChromaDB compatibility ("" if None)
    category: str   # Non-null string for ChromaDB compatibility ("" if None)
    document_type: str
    synthetic_policy: bool
    source_file: str
    section_heading: str
    chunk_index: int
    text: str  # The actual policy passage
    content_hash: str

    def to_metadata(self) -> Dict[str, Any]:
        """Converts chunk metadata to ChromaDB-compatible types (str, int, float, bool)."""
        return {
            "policy_id": self.policy_id,
            "policy_title": self.policy_title,
            "policy_version": self.policy_version,
            "effective_date": self.effective_date,
            "scope": self.scope,
            "seller_id": self.seller_id,
            "category": self.category,
            "document_type": self.document_type,
            "synthetic_policy": self.synthetic_policy,
            "source_file": self.source_file,
            "section_heading": self.section_heading,
            "chunk_index": self.chunk_index,
            "content_hash": self.content_hash,
        }


def _split_into_sections(body: str) -> List[Dict[str, str]]:
    """
    Splits markdown body by level 2 and level 3 headings.
    Returns list of dicts: [{"heading": "...", "content": "..."}].
    """
    lines = body.split("\n")
    sections: List[Dict[str, str]] = []
    current_heading = "Overview"
    current_lines: List[str] = []

    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$")

    for line in lines:
        match = heading_pattern.match(line.strip())
        if match:
            # Save previous section if it has non-empty text
            content_str = "\n".join(current_lines).strip()
            if content_str:
                sections.append({
                    "heading": current_heading,
                    "content": content_str,
                })
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Add last section
    content_str = "\n".join(current_lines).strip()
    if content_str:
        sections.append({
            "heading": current_heading,
            "content": content_str,
        })

    return sections


def _split_long_text(text: str, max_chars: int = 1800, overlap_chars: int = 200) -> List[str]:
    """
    Subdivides long text along paragraph or sentence boundaries with bounded overlap.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        if len(para_clean) > max_chars:
            # Subdivide large paragraph by sentences
            sentences = re.split(r"(?<=[.!?])\s+", para_clean)
            for sentence in sentences:
                if current_len + len(sentence) > max_chars and current_chunk:
                    chunks.append("\n\n".join(current_chunk).strip())
                    # Keep overlap from the end
                    overlap_text = current_chunk[-1] if current_chunk else ""
                    if len(overlap_text) > overlap_chars:
                        overlap_text = overlap_text[-overlap_chars:]
                    current_chunk = [overlap_text] if overlap_text else []
                    current_len = len(overlap_text)

                current_chunk.append(sentence)
                current_len += len(sentence)
        else:
            if current_len + len(para_clean) > max_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk).strip())
                overlap_text = current_chunk[-1] if current_chunk else ""
                if len(overlap_text) > overlap_chars:
                    overlap_text = overlap_text[-overlap_chars:]
                current_chunk = [overlap_text] if overlap_text else []
                current_len = len(overlap_text)

            current_chunk.append(para_clean)
            current_len += len(para_clean)

    if current_chunk:
        chunk_str = "\n\n".join(current_chunk).strip()
        if chunk_str and (not chunks or chunk_str != chunks[-1]):
            chunks.append(chunk_str)

    return chunks


def chunk_policy_document(doc: PolicyDocument, max_chars: int = 1800) -> List[PolicyChunk]:
    """
    Generates deterministic chunks from a validated policy document.
    """
    sections = _split_into_sections(doc.body)
    chunks: List[PolicyChunk] = []
    chunk_index = 0

    for sec in sections:
        heading = sec["heading"]
        content = sec["content"]

        sub_texts = _split_long_text(content, max_chars=max_chars)
        for sub_text in sub_texts:
            clean_text = sub_text.strip()
            if not clean_text or len(clean_text) < 5:
                continue

            # Contextualized text preserves document title and section heading
            contextual_passage = f"## {doc.title} — {heading}\n\n{clean_text}"

            content_hash = hashlib.sha256(contextual_passage.encode("utf-8")).hexdigest()
            # Deterministic chunk ID: {policy_id}_c{index}_{hash[:8]}
            chunk_id = f"{doc.policy_id}_c{chunk_index:03d}_{content_hash[:8]}"

            chunks.append(PolicyChunk(
                chunk_id=chunk_id,
                policy_id=doc.policy_id,
                policy_title=doc.title,
                policy_version=doc.version,
                effective_date=doc.effective_date,
                scope=doc.scope,
                seller_id=doc.seller_id or "",
                category=doc.category or "",
                document_type=doc.document_type,
                synthetic_policy=doc.synthetic_policy,
                source_file=doc.file_path,
                section_heading=heading,
                chunk_index=chunk_index,
                text=contextual_passage,
                content_hash=content_hash,
            ))
            chunk_index += 1

    return chunks


def chunk_all_documents(documents: List[PolicyDocument]) -> List[PolicyChunk]:
    """Chunks an entire list of policy documents deterministically."""
    all_chunks: List[PolicyChunk] = []
    for doc in documents:
        all_chunks.extend(chunk_policy_document(doc))
    return all_chunks
