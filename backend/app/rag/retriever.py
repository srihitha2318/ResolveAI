"""
Semantic policy retriever module.
Coordinates vector similarity search via ChromaDB, relevance threshold filtering,
policy source provenance tracking, policy precedence resolution, and keyword fallback.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.core.policy_rules import resolve_policy_precedence
from app.rag.embeddings import BaseEmbeddingProvider, get_embedding_provider
from app.rag.vector_store import ChromaPolicyVectorStore
from app.schemas.agent_schemas import PolicyPassageSchema, PolicyRetrievalResult
from app.tools.support_tools import search_policy_documents


class SemanticPolicyRetriever:
    """
    Semantic retrieval engine for the ResolveAI policy knowledge base.
    Retrieves verifiable policy passages, applies metadata filters and distance thresholds,
    evaluates policy precedence, and safely falls back to keyword search.
    """

    def __init__(
        self,
        vector_store: Optional[ChromaPolicyVectorStore] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        distance_threshold: Optional[float] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or ChromaPolicyVectorStore(
            embedding_provider=self.embedding_provider
        )
        self.distance_threshold = (
            distance_threshold if distance_threshold is not None else settings.RAG_DISTANCE_THRESHOLD
        )

    def retrieve(
        self,
        query: str,
        seller_id: Optional[str] = None,
        category: Optional[str] = None,
        scope: Optional[str] = None,
        policy_version: Optional[str] = None,
        n_results: int = 5,
        force_keyword: bool = False,
    ) -> PolicyRetrievalResult:
        """
        Executes semantic retrieval with metadata filtering and precedence evaluation.
        Falls back to keyword search if semantic search is unavailable or forced.
        """
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return PolicyRetrievalResult(
                query=query,
                passages=[],
                found_relevant=False,
                retrieval_method="semantic_search",
                explanation="Search query was empty or whitespace only.",
                policy_ids=[],
                source_files=[],
                insufficient_evidence=True,
                needs_review=False,
            )

        # 1. Check if semantic retrieval is bypassed or unavailable
        if force_keyword:
            return self._fallback_keyword(
                query=cleaned_query,
                seller_id=seller_id,
                category=category,
                reason="Forced keyword retrieval",
            )

        try:
            # Check vector collection availability
            if self.vector_store.count() == 0:
                logger.warning("Vector store is empty. Executing keyword search fallback.")
                return self._fallback_keyword(
                    query=cleaned_query,
                    seller_id=seller_id,
                    category=category,
                    reason="Vector store collection is empty",
                )

            # 2. Execute semantic search
            results = self.vector_store.query(
                query=cleaned_query,
                n_results=n_results,
                seller_id=seller_id,
                category=category,
                scope=scope,
                policy_version=policy_version,
            )
        except Exception as e:
            logger.warning("Semantic search error (%s). Falling back to keyword search.", e)
            return self._fallback_keyword(
                query=cleaned_query,
                seller_id=seller_id,
                category=category,
                reason=f"Vector store error: {e}",
            )

        if not results:
            return PolicyRetrievalResult(
                query=cleaned_query,
                passages=[],
                found_relevant=False,
                retrieval_method="semantic_search",
                explanation=f"No matching policy passages found in vector store for '{cleaned_query}'.",
                policy_ids=[],
                source_files=[],
                insufficient_evidence=True,
                needs_review=False,
            )

        # 3. Apply distance threshold to filter out irrelevant matches
        relevant_matches = [
            r for r in results if r.get("distance", 99.0) <= self.distance_threshold
        ]

        if not relevant_matches:
            min_dist = min(r.get("distance", 99.0) for r in results)
            return PolicyRetrievalResult(
                query=cleaned_query,
                passages=[],
                found_relevant=False,
                retrieval_method="semantic_search",
                explanation=(
                    f"No matching policy passages were found for '{cleaned_query}'. "
                    f"Retrieved {len(results)} passage(s) but none met the semantic relevance "
                    f"threshold (closest distance: {min_dist:.3f}, threshold: {self.distance_threshold})."
                ),
                policy_ids=[],
                source_files=[],
                insufficient_evidence=True,
                needs_review=False,
            )

        # 4. Build passages and provenance records
        passages: List[PolicyPassageSchema] = []
        policy_ids: List[str] = []
        source_files: List[str] = []
        candidate_policies: List[Dict[str, Any]] = []

        for item in relevant_matches:
            meta = item.get("metadata", {})
            p_id = meta.get("policy_id", "UNKNOWN")
            s_file = meta.get("source_file", "")
            if p_id not in policy_ids:
                policy_ids.append(p_id)
            if s_file and s_file not in source_files:
                source_files.append(s_file)

            passages.append(PolicyPassageSchema(
                document_name=Path(s_file).name if s_file else "unknown_policy.md",
                passage=item.get("text", ""),
                matched_terms=[f"cosine_dist:{item.get('distance', 0.0):.3f}"],
                line_number=meta.get("chunk_index"),
                policy_id=p_id,
                scope=meta.get("scope"),
            ))

            candidate_policies.append({
                "policy_id": p_id,
                "scope": meta.get("scope", "platform"),
                "category": meta.get("category"),
                "seller_id": meta.get("seller_id"),
                "title": meta.get("policy_title"),
                "rule": item.get("text", "")[:200],
            })

        # 5. Evaluate policy precedence hierarchy across retrieved policies
        norm_seller = seller_id.replace("SLR-", "SELLER-") if (seller_id and seller_id.startswith("SLR-")) else seller_id
        precedence_result = resolve_policy_precedence(
            policies=candidate_policies,
            order_category=category,
            order_seller_id=norm_seller,
        )

        conflict_status = precedence_result.get("status", "resolved")
        needs_review = precedence_result.get("requires_human_review", False)
        explanation = (
            f"Retrieved {len(passages)} relevant policy passage(s) via semantic vector search. "
            f"Precedence status: {conflict_status}. {precedence_result.get('explanation', '')}"
        )

        return PolicyRetrievalResult(
            query=cleaned_query,
            passages=passages,
            found_relevant=True,
            retrieval_method="semantic_search",
            explanation=explanation,
            policy_ids=policy_ids,
            source_files=source_files,
            conflict_status=conflict_status,
            needs_review=needs_review,
            insufficient_evidence=False,
        )

    def _fallback_keyword(
        self,
        query: str,
        seller_id: Optional[str] = None,
        category: Optional[str] = None,
        reason: str = "",
    ) -> PolicyRetrievalResult:
        """
        Executes safe keyword search fallback across local Markdown policy files.
        """
        raw_res = search_policy_documents(
            query=query,
            seller_id=seller_id,
            category=category,
        )

        matches = raw_res.get("matches", [])
        if not matches:
            return PolicyRetrievalResult(
                query=query,
                passages=[],
                found_relevant=False,
                retrieval_method="keyword_fallback",
                explanation=f"Keyword fallback found no matching passages for query '{query}'. ({reason})",
                policy_ids=[],
                source_files=[],
                insufficient_evidence=True,
                needs_review=False,
            )

        passages: List[PolicyPassageSchema] = []
        policy_ids: List[str] = []
        source_files: List[str] = []
        candidate_policies: List[Dict[str, Any]] = []

        for m in matches[:5]:
            p_id = m.get("policy_id") or "POL-PLAT-UNKNOWN"
            d_name = m.get("document_name", "return_policy.md")
            if p_id not in policy_ids:
                policy_ids.append(p_id)
            if d_name not in source_files:
                source_files.append(d_name)

            passages.append(PolicyPassageSchema(
                document_name=d_name,
                passage=m.get("passage", ""),
                matched_terms=m.get("matched_terms", []),
                line_number=m.get("line_number"),
                policy_id=p_id,
                scope=m.get("scope"),
            ))

            candidate_policies.append({
                "policy_id": p_id,
                "scope": m.get("scope", "platform"),
                "category": m.get("category"),
                "seller_id": m.get("seller_id"),
                "rule": m.get("passage", "")[:200],
            })

        precedence_result = resolve_policy_precedence(
            policies=candidate_policies,
            order_category=category,
            order_seller_id=seller_id,
        )

        conflict_status = precedence_result.get("status", "resolved")
        needs_review = precedence_result.get("requires_human_review", False)

        return PolicyRetrievalResult(
            query=query,
            passages=passages,
            found_relevant=True,
            retrieval_method="keyword_fallback",
            explanation=(
                f"Retrieved {len(passages)} passage(s) via keyword fallback ({reason}). "
                f"Precedence status: {conflict_status}."
            ),
            policy_ids=policy_ids,
            source_files=source_files,
            conflict_status=conflict_status,
            needs_review=needs_review,
            insufficient_evidence=False,
        )
