"""
Policy Retriever Agent for ResolveAI.
Coordinates policy document search across local markdown knowledge base using
semantic vector retrieval with persistent ChromaDB and graceful keyword search fallback.
"""

from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging_config import logger
from app.rag.retriever import SemanticPolicyRetriever
from app.schemas.agent_schemas import (
    PolicyPassageSchema,
    PolicyRetrievalResult,
    PolicySearchInput,
)
from app.tools.support_tools import search_policy_documents


class PolicyRetrieverAgent:
    """
    Agent responsible for searching local support policy documents and returning
    verifiable passages without hallucinating citations or terms.
    Integrates semantic vector search when available, falling back to keyword search.
    """

    def __init__(
        self,
        policies_dir: Optional[Path] = None,
        semantic_retriever: Optional[SemanticPolicyRetriever] = None,
    ):
        self.policies_dir = policies_dir
        self._semantic_retriever = semantic_retriever

    @property
    def semantic_retriever(self) -> Optional[SemanticPolicyRetriever]:
        """Lazily initializes the semantic retriever if no custom policies_dir is set."""
        if self._semantic_retriever is None and self.policies_dir is None:
            try:
                self._semantic_retriever = SemanticPolicyRetriever()
            except Exception as e:
                logger.warning("Could not initialize SemanticPolicyRetriever: %s", e)
                self._semantic_retriever = None
        return self._semantic_retriever

    def retrieve(self, input_data: PolicySearchInput) -> PolicyRetrievalResult:
        """
        Executes policy retrieval.
        Prefers semantic vector retrieval when indexed; falls back to deterministic keyword search.
        """
        raw_query = (input_data.query or "").strip()
        if not raw_query:
            return PolicyRetrievalResult(
                query=input_data.query,
                passages=[],
                found_relevant=False,
                retrieval_method="local_keyword_search",
                explanation=f"No matching policy passages were found for '{input_data.query}'. Policy review is required before committing to customer resolutions.",
                insufficient_evidence=True,
            )

        # If a custom policy directory was explicitly provided or method is explicitly 'keyword',
        # execute keyword search directly
        if self.policies_dir is not None or input_data.method == "keyword":
            return self._keyword_search(input_data)

        # Attempt semantic retrieval if vector store is ready
        retriever = self.semantic_retriever
        if retriever is not None:
            try:
                if retriever.vector_store.count() > 0:
                    sem_result = retriever.retrieve(
                        query=raw_query,
                        seller_id=input_data.seller_id,
                        category=input_data.category,
                        scope=input_data.scope,
                        policy_version=input_data.policy_version,
                    )
                    # If semantic search found relevant passages, return result
                    if sem_result.found_relevant and sem_result.passages:
                        return sem_result
            except Exception as e:
                logger.warning("Semantic retrieval attempt failed (%s). Executing keyword fallback.", e)

        # Fallback to local keyword search
        return self._keyword_search(input_data)

    def _keyword_search(self, input_data: PolicySearchInput) -> PolicyRetrievalResult:
        """Executes verified keyword search across local markdown policies."""
        raw_query = input_data.query
        search_result = search_policy_documents(
            query=raw_query,
            policies_dir=self.policies_dir,
            seller_id=input_data.seller_id,
            category=input_data.category,
        )

        matches = search_result.get("matches", [])
        passages = [
            PolicyPassageSchema(
                document_name=m["document_name"],
                passage=m["passage"],
                matched_terms=m.get("matched_terms", []),
                line_number=m.get("line_number"),
                policy_id=m.get("policy_id"),
                scope=m.get("scope"),
            )
            for m in matches
        ]

        found_relevant = len(passages) > 0

        if found_relevant:
            explanation = (
                f"Retrieved {len(passages)} matching passage(s) directly from policy files "
                f"matching query '{raw_query}'. All passages represent unedited policy statements."
            )
            retrieval_method = "local_keyword_search"
        else:
            explanation = (
                f"No matching policy passages were found for '{raw_query}'. "
                "Policy review is required before committing to customer resolutions."
            )
            retrieval_method = "local_keyword_search"

        policy_ids = [p.policy_id for p in passages if p.policy_id]
        source_files = list(set([p.document_name for p in passages if p.document_name]))

        return PolicyRetrievalResult(
            query=raw_query,
            passages=passages,
            found_relevant=found_relevant,
            retrieval_method=retrieval_method,
            explanation=explanation,
            policy_ids=policy_ids,
            source_files=source_files,
            insufficient_evidence=not found_relevant,
        )
