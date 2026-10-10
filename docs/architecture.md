# ResolveAI System Architecture

## 1. System Overview
ResolveAI is designed as an autonomous multimodal multi-agent customer support resolution system.
- **Level 1** established the foundational backbone: FastAPI core, SQLAlchemy 2.x relational persistence with SQLite, 8 core domain tables, deterministic synthetic seeding, structured logging, centralized configuration, and isolated testing.
- **Level 2** implements independently testable AI agents, real backend support tools with safe database access, local policy retrieval, evidence-backed resolution recommendations, and independent verification.
- **Level 2.1** localized the platform for Indian e-commerce: INR currency handling in integer paise (`₹1,49,999.00`), synthetic multi-seller marketplace rules, 15 synthetic policies, and a strict precedence hierarchy engine.
- **Level 3** established dense semantic RAG: persistent local ChromaDB vector store, deterministic chunking with SHA-256 chunk IDs, CPU MiniLM embeddings, offline test mocks, metadata-filtered queries, and keyword search fallback.
- **Level 4** coordinates the system via LangGraph stateful multi-agent orchestration: compiled `StateGraph`, strongly typed `WorkflowState`, 11 coordinated nodes, deterministic conditional routing, bounded recovery (`max_retries=1`), case event auditing via short-lived DB sessions, and `POST /api/v1/workflows/resolve`.
- **Level 5** implements Human-in-the-Loop Approval and Review: persistent SQLite checkpointing (`langgraph-checkpoint-sqlite`), interruption at `supervisor_review` node via `interrupt()`, pending review discovery and inspection APIs, atomic approval and rejection endpoints resuming saved workflows via `Command(resume=...)`, safety invariant guards, and a dark blue supervisor review dashboard at `GET /dashboard`.

```
ResolveAI System Architecture (Levels 1 - 5)
│
├── Presentation & HTTP Layer (FastAPI app.main:app)
│   ├── Middleware: CORS, Lifespan context
│   ├── System Endpoints:
│   │   ├── GET /health (Liveness probe)
│   │   ├── GET / (Service metadata)
│   │   ├── GET /dashboard (Supervisor Review Command Center UI)
│   │   └── GET /api/v1/status (Readiness & DB connectivity probe)
│   ├── Human Approval & Review Endpoints (Level 5):
│   │   ├── GET /api/v1/workflows/pending-approvals (Paginated pending queue)
│   │   ├── GET /api/v1/workflows/{thread_id}/approval (Case & evidence inspector)
│   │   ├── POST /api/v1/workflows/{thread_id}/approve (Resume & complete)
│   │   └── POST /api/v1/workflows/{thread_id}/reject (Resume & terminate)
│   ├── Multi-Agent Orchestration Endpoint (Level 4):
│   │   └── POST /api/v1/workflows/resolve
│   ├── Agent Endpoints (Level 2):
│   │   ├── POST /api/v1/analyze-complaint
│   │   ├── POST /api/v1/investigate-order
│   │   ├── POST /api/v1/search-policies
│   │   ├── POST /api/v1/recommend-resolution
│   │   └── POST /api/v1/verify-resolution
│   └── Support Tool Endpoints (Level 2):
│       ├── GET /api/v1/orders/{order_number}
│       ├── GET /api/v1/cases/{case_number}
│       ├── POST /api/v1/cases/{case_id}/tickets
│       └── POST /api/v1/cases/{case_id}/events
│
├── Multi-Agent Orchestration Subsystem (Levels 4 & 5 - LangGraph)
│   ├── WorkflowState (TypedDict state schema carrying facts, policies, approvals)
│   ├── Compiled StateGraph (12 nodes, persistent SQLite checkpointer)
│   ├── Interruption Point: supervisor_review_node (interrupt() -> Command(resume=...))
│   ├── Bounded Error Recovery (max_retries=1 loop back to recommend_resolution)
│   ├── Safety Invariant Enforcement (route_after_supervisor_review)
│   └── Checkpoint Persistence: SQLite WAL checkpointer at data/checkpoints.db
│
├── AI Agent Layer (backend/app/agents/)
│   ├── ComplaintAnalyzerAgent (Category, issue extraction, image relevance)
│   ├── OrderInvestigatorAgent (Order facts, delivery, historical complaints)
│   ├── PolicyRetrieverAgent (Local keyword policy document retrieval)
│   ├── ResolutionRecommenderAgent (Evidence-backed recommendation generation)
│   └── VerifierAgent (Factual consistency & anti-hallucination checking)
│
├── Semantic RAG Subsystem (Level 3 - backend/app/rag/)
│   ├── Document Loader & YAML frontmatter validator
│   ├── Heading-aware chunker (deterministic SHA-256 chunk IDs)
│   ├── CPU MiniLM & Offline Mock embedding providers
│   ├── Local persistent ChromaDB vector store (data/vector_store/)
│   └── Precedence hierarchy resolver (Platform > Category > Seller)
│
├── Real Support Tools (backend/app/tools/support_tools.py)
│   ├── get_order_details, get_customer_orders, get_previous_complaints
│   ├── get_case_details, get_refund_status, create_support_ticket
│   ├── update_case_status, record_case_event, search_policy_documents
│   └── check_refund_eligibility
│
├── LLM Provider Abstraction (backend/app/core/llm_provider.py)
│   ├── BaseLLMProvider (Abstract contract)
│   ├── NullLLMProvider (Offline deterministic fallback when keys absent)
│   └── HTTPLLMProvider (Lightweight HTTP integration with Gemini/Groq via httpx)
│
├── Central Configuration & Security (backend/app/core/config.py)
│   ├── Pydantic Settings with root-anchored SQLite normalization
│   └── Zero mandatory credentials for local execution
│
└── Relational Persistence (SQLAlchemy 2.x & SQLite)
    ├── 8 Domain Tables (customers, orders, support_cases, support_tickets,
    │                    approval_requests, case_events, call_summaries, customer_feedback)
    └── Foreign Keys (PRAGMA foreign_keys = ON) & Rating Constraints
```

---

## 2. Component Responsibilities

### A. Complaint Analyzer Agent (`app.agents.complaint_analyzer`)
- **Input**: `complaint_text`, optional `order_number`, optional `case_id`.
- **Extraction**: Classifies categories (`delayed_delivery`, `missing_order`, `damaged_product`, `refund_request`, `replacement_request`, `wrong_item`, `cancellation`, `warranty`, `other`).
- **Attributes**: Determines `image_relevant` (True for damage/wrong items), extracts order numbers via regex matching if omitted, and detects missing information.
- **Provider Transparency**: Employs deterministic parsing when no LLM is configured, explicitly declaring `analysis_method="rule_based"`.

### B. Order Investigation Agent (`app.agents.order_investigator`)
- **Input**: `order_number` or `case_number`.
- **Responsibilities**: Retrieves actual database records using real support tools without fabricating state.
- **Delivery Factuality**: Evaluates delivery based on confirmed `delivered_at` records rather than expected dates.
- **Refund Factuality**: Inspects approval request records and explicitly reports `refund_status="not_recorded"` because the database schema does not include external payment gateway disbursement tables.

### C. Policy Retrieval Agent (`app.agents.policy_retriever`)
- **Input**: Query or category keywords.
- **Search Mechanism**: Real local document search across markdown files in `data/policies/`.
- **Factuality**: Preserves unedited policy text, returns exact filenames and matched passages, and explains when no policy passage matches the query.

### D. Resolution Recommendation Agent (`app.agents.resolution_recommender`)
- **Input**: `ComplaintAnalysisResult`, `OrderInvestigationResult`, `PolicyRetrievalResult`.
- **Rules**:
  1. Recommends review or actions based strictly on verified order facts and retrieved policy evidence.
  2. Never executes or promises refunds or replacements.
  3. Differentiates Tier 1 automated review thresholds (₹5,000.00 / 5,00,000 paise) from Tier 2 supervisor approval requirements (over ₹25,000.00 / 25,00,000 paise).
  4. Flags missing evidence and labels reasoning clearly (`method="rule_based"`).

### E. Verification Agent (`app.agents.verifier`)
- **Input**: Proposed recommendation and underlying evidence.
- **Checks**:
  1. Confirms referenced order actually exists in database facts.
  2. Verifies cited policy rules exist in retrieved evidence.
  3. Rejects recommendations that contradict stored order delivery status.
  4. Rejects recommendations falsely claiming a refund or ticket was already completed.
  5. Determines required next steps (e.g. supervisor review queue).

### F. Real Support Tools (`app.tools.support_tools`)
- Real Python database query and mutation functions utilizing SQLAlchemy sessions and transactions.
- Atomically records audit events during status transitions and rolls back on failure.
- `check_refund_eligibility` assesses category-specific return windows and INR paise thresholds conservatively without issuing payments.

---

## 3. Level 2.1: Indian Localization & Policy Architecture

### A. Indian Currency Standard (INR / Paise)
- **Currency Code**: `INR` (Symbol: `₹`).
- **Database Storage**: Pure integer paise (1 INR = 100 paise). Binary floating-point monetary storage is strictly prohibited across the database models and calculation logic.
- **Display Formatting**: `format_inr(paise)` implements standard Indian number grouping (`₹1,49,999.00`).
- **Financial Thresholds**:
  - `TIER_1_MAX_AMOUNT_PAISE = 500_000` (₹5,000.00)
  - `HIGH_VALUE_THRESHOLD_PAISE = 2_500_000` (₹25,000.00)

### B. Demonstration Marketplace Ecosystem
- **Fictional Demonstration Sellers**:
  - `SELLER-001` (Deccan Digital): Electronics, mobiles, laptops, accessories (focus: DOA hardware, serial verification, replacement).
  - `SELLER-002` (VastraKart): Fashion, apparel, footwear (focus: size exchanges, tags/hygiene condition, 14-day window).
  - `SELLER-003` (GrihaMart): Home appliances, household products (focus: transit damage, technician inspection reports, installation issues).
- **Supported Product Categories**: `electronics`, `fashion`, `home_appliances`, `general_merchandise`.

### C. Policy Knowledge Base & Precedence Hierarchy
- 15 comprehensive synthetic policy documents stored in `data/policies/` with YAML front matter metadata, indexed in `manifest.json`.
- Backward-compatibility pointer preserved at `data/policies/return_policy.md`.
- **Precedence Hierarchy Engine (`resolve_policy_precedence`)**:
  1. Non-overridable Platform Constraints & Security Controls (`platform_constraint`)
  2. Applicable Platform-wide Policies (`platform`)
  3. Applicable Category-specific Policies (`category`)
  4. Applicable Seller-specific Policies (`seller`, only where explicitly permitted by platform)
- Direct conflicts or missing evidence deterministically resolve to `needs_review` with conflicting policy identifiers preserved for human escalation.

---

## 4. Level 3: Semantic RAG & Vector Storage Subsystem

### A. Subsystem Architecture
The Level 3 Semantic RAG subsystem replaces brittle keyword matching with dense vector similarity search while strictly enforcing anti-hallucination constraints and platform precedence:

```
[Markdown Policies (data/policies/)]
                 │
                 ▼
       [Document Loader]  <── Manifest & YAML Frontmatter
                 │
                 ▼
       [Heading-Aware Chunker]  <── 400-700 tokens, SHA-256 chunk IDs
                 │
                 ▼
    [ChromaPolicyVectorStore]  <── Local persistent ChromaDB (data/vector_store/)
                 │                  HNSW Cosine Distance, Idempotent Upserts
                 ▼
   [SemanticPolicyRetriever]  <── Cosine Distance Threshold (0.80)
          │            │
          │            └── Fallback to Keyword Search if unindexed or failure
          ▼
   [Policy Precedence Resolver] (Platform > Category > Seller)
          │
          ▼
  [PolicyRetrievalResult]  <── Exact unedited passages + Provenance citations
```

### B. Core Modules (`backend/app/rag/`)
1. **`document_loader.py`**:
   - Manifest-guided loading from `data/policies/manifest.json`.
   - Security verification preventing path traversal outside `data/policies/`.
   - YAML frontmatter extraction separating metadata from document body.
   - Automatically skips compatibility redirects (`return_policy.md`).
2. **`chunker.py`**:
   - Heading-based segmentation along Markdown `## ` and `### ` headers.
   - Long sections split along sentence boundaries without breaking policy rules.
   - Generates deterministic, stable chunk IDs (`chk_<sha256>`).
3. **`embeddings.py`**:
   - `SentenceTransformerEmbeddingProvider`: Production provider using `sentence-transformers/all-MiniLM-L6-v2` executed exclusively on CPU with in-process singleton caching.
   - `MockEmbeddingProvider`: Deterministic signed feature-hashing provider for 100% offline unit testing with zero external network downloads.
4. **`vector_store.py`**:
   - Encapsulates `chromadb.PersistentClient` rooted at `data/vector_store/`.
   - Idempotent upsert logic tracking content hashes to prevent duplicate vectors.
   - Automatic pruning of stale/deleted policy chunks during synchronization.
5. **`retriever.py`**:
   - Queries ChromaDB with metadata filters (`seller_id`, `category`, `scope`, `policy_version`).
   - Filters results with `RAG_DISTANCE_THRESHOLD = 0.80`.
   - Automatically falls back to keyword search if the vector store is unavailable.
   - Applies `resolve_policy_precedence` across retrieved candidates.
6. **`index_policies.py`**:
   - Standalone CLI command entrypoint supporting `--mock`, `--force`, `--policies-dir`, and `--persist-dir`.

---

## 5. Level 4: LangGraph Multi-Agent Orchestration Subsystem

### A. Subsystem Purpose & Design Principles
The Level 4 orchestration subsystem replaces ad-hoc agent chaining with an explicit, observable, and deterministic state machine built on LangGraph (`StateGraph`).
- **No Agent Hallucinations of Authority**: Agents do not autonomously invoke tools with unvalidated parameters or loop indefinitely.
- **Strongly Typed Workflow State**: A single immutable-per-step `WorkflowState(TypedDict)` carries all facts, policy passages, analysis results, and decisions.
- **Deterministic Conditional Routing**: Edges route based on structured attributes, not loose regex matches or LLM self-reports.
- **Anti-Infinite-Loop Guarantee**: Verification failures allow strictly `max_retries = 1` attempt at bounded recovery before deterministic escalation.
- **Human Approval Boundary**: High-value financial resolutions (>₹25,000.00), precedence conflicts, or ambiguous facts route to `escalate_case` and enter `needs_review: true`, preserving Level 5 human-in-the-loop governance.
- **Database Transaction Safety**: Sessions are scoped per node using `with SessionLocal() as db:` context managers, preventing database locks during CPU embedding calculations.

### B. Graph Topology & Control Flow
```
                          [START]
                             │
                             ▼
                    [initialize_case]
                             │
              (route_after_init: empty complaint?)
                ┌────────────┴────────────┐
             [Valid]                   [Empty]
                │                         │
                ▼                         ▼
       [analyze_complaint]       [finalize_response]
                │                         │
                ▼                         ▼
       [investigate_order]              [END]
                │
                ▼
    [retrieve_policy_evidence]
                │
                ▼
      [recommend_resolution] <────────────┐
                │                         │
                ▼                         │
       [verify_resolution]                │
                │                         │
     (route_after_verification)           │
       ┌────────┬─────────────┬───────────┴──────────┐
       │        │             │                      │
[Clean Valid] [Missing Info] [Conflict / Review] [Verify Fail]
       │        │             │               (retries < 1)
       │        │             │                      │
       │        │             │                      ▼
       │        │             │              [attempt_recovery]
       │        │             │
       ▼        ▼             ▼
  [record_]  [handle_]   [escalate_]
[resolution][missing_info][case]
       │        │             │
       └────────┼─────────────┘
                │
                ▼
       [finalize_response]
                │
                ▼
              [END]
```

### C. Workflow State Contract (`WorkflowState`)
Defined in [`backend/app/workflows/state.py`](file:///C:/Users/User/Documents/ResolveAI/backend/app/workflows/state.py):
| Field | Type | Description |
|---|---|---|
| `workflow_id` | `str` | UUID4 unique workflow execution identifier |
| `case_id` | `Optional[int]` | Associated relational `SupportCase.id` |
| `case_number` | `Optional[str]` | Human-readable case code (e.g. `CASE-2026-0001`) |
| `customer_id` | `Optional[int]` | Relational customer identifier |
| `order_number` | `Optional[str]` | Normalized order code (e.g. `ORD-10001`) |
| `complaint_text` | `str` | Raw customer complaint prose |
| `complaint_analysis` | `Optional[Dict]` | Serialized `ComplaintAnalysisResult` |
| `complaint_category` | `Optional[str]` | Categorized issue (`damaged_product`, etc.) |
| `urgency` | `str` | Extracted urgency (`low`, `medium`, `high`) |
| `order_investigation`| `Optional[Dict]` | Serialized `OrderInvestigationResult` |
| `order_status` | `Optional[str]` | Actual delivery status (`delivered`, `in_transit`, etc.) |
| `missing_order` | `bool` | True when referenced order does not exist in DB |
| `missing_information`| `List[str]` | Missing fields preventing resolution |
| `retrieved_policy_passages` | `List[Dict]` | Unaltered policy passages from Level 3 RAG |
| `policy_source_metadata` | `List[str]` | Source files and chunk identifiers |
| `retrieval_method` | `str` | `semantic_search` or `keyword_fallback` |
| `policy_conflict_status` | `str` | `resolved`, `needs_review`, or `none` |
| `insufficient_evidence` | `bool` | True when semantic distance > 0.80 |
| `recommended_resolution` | `Optional[Dict]` | Serialized `ResolutionRecommendationResult` |
| `verification_result` | `Optional[Dict]` | Serialized `VerificationResult` |
| `is_valid` | `Optional[bool]` | Consistency outcome from VerifierAgent |
| `workflow_status` | `str` | `in_progress`, `completed`, `needs_information`, `needs_review`, `failed` |
| `current_stage` | `str` | Active node identifier or `finalized` |
| `escalation_reason` | `Optional[str]` | Explanatory reason for routing to review |
| `errors` | `List[str]` | Sanitized error strings |
| `retry_count` | `int` | Number of recovery attempts executed |
| `max_retries` | `int` | Upper bound for recovery attempts (default: 1) |
| `events_recorded` | `List[str]` | Audit event keys written to `CaseEvent` table |
| `created_at` | `str` | ISO 8601 UTC workflow creation timestamp |
| `updated_at` | `str` | ISO 8601 UTC workflow last transition timestamp |

### D. Graph Nodes and Responsibilities
1. **`initialize_case_node`**:
   - Generates `workflow_id`.
   - Strips and normalizes input text.
   - If `case_id` provided, verifies record in DB; if absent, creates pending case.
   - Records `workflow_started` in `CaseEvent` table.
2. **`analyze_complaint_node`**:
   - Calls `ComplaintAnalyzerAgent.analyze()`.
   - Extracts category, urgency, and image relevance.
3. **`investigate_order_node`**:
   - Executes `OrderInvestigatorAgent.investigate()` using short-lived DB session.
   - Sets `missing_order = True` if order cannot be found in database.
4. **`retrieve_policy_evidence_node`**:
   - Invokes `PolicyRetrieverAgent.retrieve()` backed by Level 3 ChromaDB semantic store.
   - Preserves source file provenance and passes candidates to `resolve_policy_precedence`.
5. **`recommend_resolution_node`**:
   - Invokes `ResolutionRecommenderAgent.recommend()`.
   - Evaluates INR paise amounts against financial approval tiers (₹5,000 / ₹25,000).
6. **`verify_resolution_node`**:
   - Invokes `VerifierAgent.verify()`.
   - Enforces factual consistency against stored order status and retrieved policy prose.
7. **`handle_missing_information_node`**:
   - Terminal node for missing orders or missing complaint specifics.
   - Sets `workflow_status = "needs_information"`.
   - Records `case_needs_information` audit event.
8. **`escalate_case_node`**:
   - Terminal node for policy conflicts, insufficient evidence, supervisor approval requirements, or exhausted retries.
   - Sets `workflow_status = "needs_review"`.
   - Records `case_needs_review` audit event.
9. **`attempt_recovery_node`**:
   - Increments `retry_count`.
   - Appends verifier critique into state for recommender to adjust.
   - Loops back to `recommend_resolution_node`.
10. **`record_resolution_node`**:
    - Terminal node for verified recommendations.
    - Sets `workflow_status = "completed"`.
    - Records `resolution_verification_passed` audit event.
11. **`finalize_response_node`**:
    - Sanitizes internal state, timestamps final output, sets `current_stage = "finalized"`.

### E. Deterministic Routing Decision Table
| Priority | Router | State Condition | Next Node | Workflow Status |
|---|---|---|---|---|
| Init 1 | `route_after_init` | `complaint_text` is empty/whitespace | `finalize_response` | `failed` |
| Init 2 | `route_after_init` | `complaint_text` is non-empty | `analyze_complaint` | `in_progress` |
| Post-Ver 1 | `route_after_verification` | `missing_order == True` (Order missing in DB) | `handle_missing_information` | `needs_information` |
| Post-Ver 2 | `route_after_verification` | `policy_conflict_status == "needs_review"` | `escalate_case` | `needs_review` |
| Post-Ver 3 | `route_after_verification` | `is_valid == False` and `retry_count < max_retries` | `attempt_recovery` | `in_progress` |
| Post-Ver 4 | `route_after_verification` | `is_valid == False` and `retry_count >= max_retries` | `escalate_case` | `needs_review` |
| Post-Ver 5 | `route_after_verification` | `insufficient_evidence == True` | `escalate_case` | `needs_review` |
| Post-Ver 6 | `route_after_verification` | `requires_supervisor_approval == True` | `escalate_case` | `needs_review` |
| Post-Ver 7 | `route_after_verification` | `recommendation_type == "request_more_info"` | `handle_missing_information` | `needs_information` |
| Post-Ver 8 | `route_after_verification` | Clean, verified recommendation | `record_resolution` | `completed` |

### F. Module Structure (`backend/app/workflows/`)
```
backend/app/workflows/
├── __init__.py           -> Exports WorkflowState, initialize_workflow_state, get_resolution_graph, run_resolution_workflow, checkpointer
├── checkpointer.py       -> Persistent SQLite checkpointer connection lifecycle with WAL mode
├── state.py              -> WorkflowState TypedDict and initialization helper
├── nodes.py              -> 12 atomic graph nodes including supervisor_review_node (interrupt point)
├── routing.py            -> Deterministic conditional edge functions (route_after_init, route_after_verification, route_after_supervisor_review)
└── graph.py              -> StateGraph construction, SQLite checkpointer compilation, and runner
```

---

## 7. Level 5: Human-in-the-Loop Approval & Review Architecture

### A. Core Architecture Principles
1. **Zero Unauthorized Execution**: AI agents propose remedies, but sensitive actions (high-value refunds > ₹5,000.00, policy precedence conflicts, unverified damage claims) cannot complete without an authorized supervisor decision.
2. **Persistent Checkpointing**: Workflow states are serialized to a dedicated SQLite checkpointer database (`data/checkpoints.db`) under unique `thread_id` keys in Write-Ahead Logging (WAL) mode. Executions survive server reboots and process restarts.
3. **Native LangGraph Interruption & Resumption**: 
   - `interrupt(...)` pauses the graph inside `supervisor_review_node`.
   - `Command(resume=...)` injects the authorized decision payload (`approve` or `reject`), resuming execution from the saved checkpoint.
4. **Defense-in-Depth Safety Invariants**:
   - `route_after_supervisor_review` and `record_resolution_node` independently re-validate safety rules.
   - Even if a supervisor approves a case, if that case has an unresolved policy conflict (`needs_review`), missing order, or failed verification, the system strictly refuses to mark the resolution as `completed`.
5. **Separation of Database Concerns**:
   - Relational business entities (`support_cases`, `approval_requests`, `case_events`) reside in `data/resolveai.db` managed by SQLAlchemy.
   - Graph checkpoint blobs and versioned execution steps reside in `data/checkpoints.db` managed by `SqliteSaver`.

### B. Supervisor Review Interruption & Resume Flow

```
   [recommend_resolution] -> [verify_resolution]
                                  │
                                  ▼ (route_after_verification)
                            [escalate_case]
                                  │ (creates ApprovalRequest in DB)
                                  ▼
                        [supervisor_review] ◄─── (interrupt() pauses execution)
                                  │                (persisted to checkpoints.db)
                                  │
      ┌───────────────────────────┴───────────────────────────┐
      │                                                       │
  [APPROVE]                                               [REJECT]
  Command(resume={"action":"approve"})    Command(resume={"action":"reject", "reason":...})
      │                                                       │
      ▼                                                       ▼
  (route_after_supervisor_review)                         [finalize_response]
      │                                                       │
 ┌────┴──────────────────────────┐                            ▼
 │ Safety Pass                   │ Violation               [END]
 ▼                               ▼                   (workflow_status='rejected')
[record_resolution]      [finalize_response]
 │                               │
 ▼                               ▼
[finalize_response]            [END]
 │                       (workflow_status='needs_review')
 ▼
[END]
(workflow_status='completed')
```

### C. Approval API Endpoints
- `GET /api/v1/workflows/pending-approvals`: Paginated list of cases awaiting human supervisor review.
- `GET /api/v1/workflows/{thread_id}/approval`: Full case investigation facts, order details, and policy evidence for a specific thread.
- `POST /api/v1/workflows/{thread_id}/approve`: Authorized approval decision resuming workflow to completion.
- `POST /api/v1/workflows/{thread_id}/reject`: Authorized rejection decision halting proposed actions without ticket creation.

### D. Supervisor Review Command Center Dashboard
Served directly at `GET /dashboard`:
- Dark navy and royal blue theme with electric cyan accents.
- Live queue showing pending approval requests with Indian Rupee formatting.
- Case inspector displaying customer complaint, order facts, proposed recommendation, and policy evidence.
- Interactive decision controls with rejection justification modal and real-time toast feedback.


