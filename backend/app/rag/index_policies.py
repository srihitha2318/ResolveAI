"""
Command-line utility and module for indexing policy documents into persistent ChromaDB.

Usage:
    .\\.venv\\Scripts\\python.exe -m backend.app.rag.index_policies
    or
    python -m app.rag.index_policies (from backend directory)
"""

import argparse
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional

# Ensure project root and backend are in python path if run directly
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.logging_config import logger
from app.rag.chunker import chunk_all_documents
from app.rag.document_loader import load_all_policy_documents
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import ChromaPolicyVectorStore


def run_indexing(
    policies_dir: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    persist_dir: Optional[Path] = None,
    collection_name: Optional[str] = None,
    use_mock_embeddings: bool = False,
    force_reindex: bool = False,
) -> Dict[str, Any]:
    """
    Executes the policy indexing workflow.
    Loads documents, chunks them, generates embeddings, and syncs into ChromaDB.
    """
    p_dir = policies_dir or settings.POLICIES_DIR
    m_path = manifest_path or (p_dir / "manifest.json")
    v_dir = persist_dir or settings.VECTOR_STORE_DIR
    c_name = collection_name or settings.CHROMA_COLLECTION_NAME

    start_time = time.time()
    logger.info("Starting policy knowledge base indexing...")
    logger.info("Policies directory: %s", p_dir)
    logger.info("Manifest path: %s", m_path)
    logger.info("Vector store directory: %s", v_dir)
    logger.info("Collection name: %s", c_name)

    # 1. Load policy documents
    docs, skipped = load_all_policy_documents(policies_dir=p_dir, manifest_path=m_path)
    if not docs:
        logger.error("No valid policy documents found to index.")
        return {
            "success": False,
            "documents_loaded": 0,
            "chunks_indexed": 0,
            "skipped_files": skipped,
            "error": "No valid policy documents found in manifest.",
        }

    # 2. Chunk documents deterministically
    chunks = chunk_all_documents(docs)
    logger.info("Generated %d chunks across %d policy document(s).", len(chunks), len(docs))

    # 3. Setup embedding provider and vector store
    provider_type = "mock" if use_mock_embeddings else "sentence_transformer"
    embedding_provider = get_embedding_provider(provider_type)

    vector_store = ChromaPolicyVectorStore(
        persist_dir=v_dir,
        collection_name=c_name,
        embedding_provider=embedding_provider,
    )

    if force_reindex:
        try:
            logger.info("Force reindex requested. Resetting collection %s...", c_name)
            vector_store.client.delete_collection(c_name)
            vector_store._collection = None
        except Exception as e:
            logger.warning("Could not delete existing collection during force reindex: %s", e)

    # 4. Sync chunks into ChromaDB
    sync_stats = vector_store.index_chunks(chunks)
    elapsed = round(time.time() - start_time, 2)

    logger.info(
        "Indexing complete in %s s: %d added, %d updated, %d unchanged, %d deleted. Total: %d",
        elapsed,
        sync_stats["added"],
        sync_stats["updated"],
        sync_stats["unchanged"],
        sync_stats["deleted"],
        sync_stats["total"],
    )

    return {
        "success": True,
        "documents_loaded": len(docs),
        "total_chunks": len(chunks),
        "sync_stats": sync_stats,
        "skipped_files": skipped,
        "elapsed_seconds": elapsed,
        "persist_dir": str(v_dir),
        "collection_name": c_name,
        "embedding_provider": provider_type,
    }


def main():
    parser = argparse.ArgumentParser(description="Index ResolveAI policy documents into ChromaDB.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use deterministic offline mock embeddings (for testing/CI without downloading models).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full reindex by resetting the target ChromaDB collection.",
    )
    parser.add_argument(
        "--policies-dir",
        type=Path,
        default=None,
        help="Custom path to policy documents directory.",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help="Custom path to ChromaDB vector store directory.",
    )

    args = parser.parse_args()

    print("============================================================")
    print("ResolveAI Policy Knowledge Base Indexing")
    print("============================================================")

    res = run_indexing(
        policies_dir=args.policies_dir,
        persist_dir=args.persist_dir,
        use_mock_embeddings=args.mock,
        force_reindex=args.force,
    )

    if res.get("success"):
        stats = res["sync_stats"]
        print("\n=== Indexing Summary ===")
        print(f" - Source documents processed: {res['documents_loaded']}")
        print(f" - Total chunks generated:    {res['total_chunks']}")
        print(f" - Chunks added:              {stats['added']}")
        print(f" - Chunks updated:            {stats['updated']}")
        print(f" - Chunks unchanged:          {stats['unchanged']}")
        print(f" - Stale chunks deleted:      {stats['deleted']}")
        print(f" - Total chunks in index:     {stats['total']}")
        print(f" - Embedding provider:        {res['embedding_provider']}")
        print(f" - Vector persistence path:   {res['persist_dir']}")
        print(f" - Elapsed time:              {res['elapsed_seconds']}s")
        if res.get("skipped_files"):
            print(f" - Skipped files ({len(res['skipped_files'])}): {', '.join(res['skipped_files'])}")
        print("\nIndexing completed successfully.")
        sys.exit(0)
    else:
        print(f"\nERROR: Indexing failed: {res.get('error')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
