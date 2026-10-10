"""
Persistent ChromaDB vector store wrapper for policy knowledge base indexing and retrieval.
Manages idempotent indexing, content hash tracking, stale chunk cleanup, and metadata queries.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging_config import logger
from app.rag.chunker import PolicyChunk
from app.rag.embeddings import BaseEmbeddingProvider, get_embedding_provider


class ChromaPolicyVectorStore:
    """
    Manages persistent ChromaDB vector storage for policy passages.
    Ensures safe initialization, idempotent updates, and strict metadata typing.
    """

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: Optional[str] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.persist_dir = persist_dir or settings.VECTOR_STORE_DIR
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    def _ensure_dir(self) -> None:
        """Ensures the vector store directory exists."""
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    @property
    def client(self) -> chromadb.PersistentClient:
        """Lazily initializes and returns the ChromaDB persistent client."""
        if self._client is None:
            self._ensure_dir()
            logger.info("Initializing ChromaDB PersistentClient at %s", self.persist_dir)
            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        """Gets or creates the Chroma collection configured for cosine similarity."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def count(self) -> int:
        """Returns the total number of chunks currently stored in the collection."""
        try:
            return self.collection.count()
        except Exception as e:
            logger.warning("Error fetching collection count: %s", e)
            return 0

    def index_chunks(self, chunks: List[PolicyChunk], batch_size: int = 50) -> Dict[str, Any]:
        """
        Idempotently indexes policy chunks into ChromaDB.
        Skips unchanged chunks based on content_hash, updates modified chunks,
        and purges obsolete chunks belonging to modified/deleted policies.
        """
        if not chunks:
            return {"added": 0, "updated": 0, "unchanged": 0, "deleted": 0, "total": self.count()}

        coll = self.collection

        # 1. Fetch all existing chunk IDs and content hashes
        existing_data = coll.get(include=["metadatas"])
        existing_ids = set(existing_data.get("ids", []))
        existing_metas = {
            doc_id: meta
            for doc_id, meta in zip(existing_data.get("ids", []), existing_data.get("metadatas", []))
        }

        # 2. Determine chunks to add, update, or keep
        to_upsert: List[PolicyChunk] = []
        unchanged_count = 0
        new_ids_by_policy: Dict[str, set] = {}

        for ch in chunks:
            new_ids_by_policy.setdefault(ch.policy_id, set()).add(ch.chunk_id)

            if ch.chunk_id in existing_ids:
                old_meta = existing_metas.get(ch.chunk_id, {})
                if old_meta.get("content_hash") == ch.content_hash:
                    unchanged_count += 1
                    continue
            to_upsert.append(ch)

        # 3. Detect and delete obsolete chunks for indexed policies
        stale_ids: List[str] = []
        for existing_id, meta in existing_metas.items():
            p_id = meta.get("policy_id")
            if p_id in new_ids_by_policy:
                # If this chunk ID from policy is no longer in the new chunk set, it's stale
                if existing_id not in new_ids_by_policy[p_id]:
                    stale_ids.append(existing_id)

        if stale_ids:
            logger.info("Purging %d stale chunk(s) from collection", len(stale_ids))
            coll.delete(ids=stale_ids)

        # 4. Generate embeddings and upsert in batches
        added_count = 0
        updated_count = 0

        for i in range(0, len(to_upsert), batch_size):
            batch = to_upsert[i : i + batch_size]
            texts = [b.text for b in batch]
            ids = [b.chunk_id for b in batch]
            metadatas = [b.to_metadata() for b in batch]

            embeddings = self.embedding_provider.embed_texts(texts)

            for b in batch:
                if b.chunk_id in existing_ids:
                    updated_count += 1
                else:
                    added_count += 1

            coll.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        logger.info(
            "Vector store sync complete: %d added, %d updated, %d unchanged, %d deleted. Total: %d",
            added_count,
            updated_count,
            unchanged_count,
            len(stale_ids),
            self.count(),
        )

        return {
            "added": added_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "deleted": len(stale_ids),
            "total": self.count(),
        }

    def query(
        self,
        query: str,
        n_results: int = 5,
        seller_id: Optional[str] = None,
        category: Optional[str] = None,
        scope: Optional[str] = None,
        policy_version: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic query on stored vectors with optional metadata filtering.
        Returns list of matched chunks with metadata and distance metrics.
        """
        if not query.strip():
            return []

        coll = self.collection
        if coll.count() == 0:
            return []

        query_embedding = self.embedding_provider.embed_query(query.strip())

        # Construct metadata filters supported by ChromaDB
        filters: List[Dict[str, Any]] = []
        if seller_id:
            normalized_seller = seller_id.replace("SLR-", "SELLER-") if seller_id.startswith("SLR-") else seller_id
            filters.append({"seller_id": normalized_seller})
        if category:
            filters.append({"category": category})
        if scope:
            filters.append({"scope": scope})
        if policy_version:
            filters.append({"policy_version": policy_version})

        where_clause: Optional[Dict[str, Any]] = None
        if len(filters) == 1:
            where_clause = filters[0]
        elif len(filters) > 1:
            where_clause = {"$and": filters}

        # Query collection
        try:
            results = coll.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, coll.count()),
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("ChromaDB query execution error: %s", e)
            return []

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        retrieved: List[Dict[str, Any]] = []
        ids = results["ids"][0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for chunk_id, doc_text, meta, dist in zip(ids, documents, metadatas, distances):
            retrieved.append({
                "chunk_id": chunk_id,
                "text": doc_text,
                "metadata": meta,
                "distance": dist,
                # Cosine distance ranges [0, 2]; similarity = 1 - distance
                "similarity_score": round(max(0.0, 1.0 - dist), 4),
            })

        return retrieved
