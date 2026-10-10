# ResolveAI

ResolveAI is an autonomous multimodal multi-agent customer support resolution system engineered for hackathon-grade performance. The system autonomously investigates customer complaints, retrieves support policies, inspects order information, analyzes product images, verifies claims, recommends resolutions, and requests human approval for sensitive financial actions.

---

## 1. Project Implementation Status

- **Level 1 (Foundation)**: Complete. FastAPI backend, SQLAlchemy 2.x relational persistence with SQLite (8 domain tables), deterministic synthetic seed data, centralized configuration, structured logging, and automated test suite.
- **Level 2 (Agents & Real Support Tools)**: Complete. Five independent AI agents (Complaint Analyzer, Order Investigator, Policy Retriever, Resolution Recommender, and Verifier), real backend support tool functions with database transactions, local policy document search, provider-agnostic LLM abstraction, and comprehensive test suite.
- **Level 2.1 (Indian Localization & Policy Expansion)**: Complete. Fully localized for the Indian e-commerce marketplace: INR currency standard (stored as integer paise, formatted with Indian numbering `₹1,49,999.00`), 3 distinct demonstration sellers (`SELLER-001: Deccan Digital`, `SELLER-002: VastraKart`, `SELLER-003: GrihaMart`), 4 product categories, 15 synthetic demonstration policy documents + manifest, and policy precedence hierarchy engine.
- **Level 3 (Semantic RAG & Policy Evidence Retrieval)**: Complete. Local persistent vector database using ChromaDB, deterministic heading-based chunking with content hashing, lightweight CPU-optimized embeddings (`sentence-transformers/all-MiniLM-L6-v2`), deterministic mock embeddings for 100% offline unit tests, metadata-filtered semantic search, policy precedence hierarchy integration, anti-hallucination source provenance citations, graceful keyword-search fallback, and standalone CLI indexing command. 99 passing tests (98 offline unit + 1 live integration)- **Level 4 (LangGraph Multi-Agent Orchestration)**: Complete. Stateful multi-agent graph orchestration using LangGraph (`langgraph==0.6.11`), strongly typed `WorkflowState`, 11 coordinated workflow nodes, deterministic conditional routing (normal verified path, missing order/facts, policy conflict review, insufficient evidence escalation, human approval required routing, empty complaint fast-exit, and bounded recovery with `max_retries=1`), case event recording via short-lived database sessions, and `POST /api/v1/workflows/resolve` FastAPI endpoint. 126 passing tests (125 offline unit + 1 live integration).
- **Level 5 (Human-in-the-Loop Approval and Review)**: Complete. Stateful workflow pause/resume orchestration with persistent SQLite checkpoints (`langgraph-checkpoint-sqlite==3.0.3` in WAL mode at `data/checkpoints.db`), human interruption at `supervisor_review` node via native `interrupt()`, 4 dedicated approval endpoints for discovering, inspecting, approving, and rejecting cases, defense-in-depth safety invariant enforcement, and a sleek dark blue Supervisor Review Command Center dashboard served at `GET /dashboard`. 138 passing tests (137 offline unit + 1 live integration).

---

## 2. Architecture Overview

```
ResolveAI Architecture (Levels 1 - 5)
├── Presentation / HTTP Layer (FastAPI)
│   ├── GET /health                                -> Process health probe
│   ├── GET /                                     -> Service metadata & docs link
│   ├── GET /dashboard                            -> Supervisor Review Command Center UI
│   ├── GET /api/v1/status                        -> Subsystem & DB connectivity probe
│   ├── GET /api/v1/workflows/pending-approvals   -> Paginated pending approvals queue
│   ├── GET /api/v1/workflows/{thread}/approval   -> Full case investigation & evidence
│   ├── POST /api/v1/workflows/{thread}/approve   -> Supervisor approval & resume
│   ├── POST /api/v1/workflows/{thread}/reject    -> Supervisor rejection & termination
│   ├── POST /api/v1/workflows/resolve            -> LangGraph Orchestration Endpoint
│   ├── POST /api/v1/analyze-complaint            -> Complaint analyzer agent probe
│   ├── POST /api/v1/investigate-order            -> Order investigation agent probe
│   ├── POST /api/v1/search-policies              -> Policy retriever agent (RAG + Fallback)
│   ├── POST /api/v1/recommend-resolution         -> Resolution recommender agent probe
│   ├── POST /api/v1/verify-resolution            -> Resolution verifier agent probe
│   ├── GET /api/v1/orders/{order_number}         -> Stored order query
│   ├── GET /api/v1/cases/{case_number}           -> Stored case query
│   ├── POST /api/v1/cases/{id}/tickets           -> Support ticket creation
│   └── POST /api/v1/cases/{id}/events            -> Case audit event logging
├── Multi-Agent Orchestration Layer (Levels 4 & 5 - LangGraph)
│   ├── StateGraph(WorkflowState)                 -> Stateful coordinator
│   ├── Persistent SQLite Checkpointer            -> SqliteSaver (WAL mode, data/checkpoints.db)
│   ├── 12 Graph Nodes:
│   │   ├── initialize_case                       -> Case & workflow state setup
│   │   ├── analyze_complaint                     -> Complaint category & issue extraction
│   │   ├── investigate_order                     -> Stored order fact checking
│   │   ├── retrieve_policy_evidence              -> Semantic RAG retrieval & precedence
│   │   ├── recommend_resolution                  -> Policy-grounded actionable recommendation
│   │   ├── verify_resolution                     -> Consistency & hallucination verification
│   │   ├── handle_missing_information            -> Terminal node for incomplete facts
│   │   ├── escalate_case                         -> Relational DB ApprovalRequest creation
│   │   ├── supervisor_review                     -> Interruption point (interrupt() / resume)
│   │   ├── attempt_recovery                      -> Bounded regeneration node (max_retries=1)
│   │   ├── record_resolution                     -> Terminal node recording resolution events
│   │   └── finalize_response                     -> State normalization & response preparation
│   └── Deterministic Conditional Edges:
│       ├── route_after_init                      -> Empty complaint fast-path validation
│       ├── route_after_verification              -> Missing Order -> Conflict -> Recovery -> Insufficient -> Escalate -> Record
│       └── route_after_supervisor_review         -> Rejection -> Safety Invariants -> Record -> Finalize
├── AI Agent Layer
│   ├── ComplaintAnalyzerAgent                    -> Category, issue, desired outcome, image relevance
│   ├── OrderInvestigatorAgent                    -> Fact retrieval, delivery summary, case history
│   ├── PolicyRetrieverAgent                      -> Semantic vector retrieval with keyword fallback
│   ├── ResolutionRecommenderAgent                -> Evidence-backed actionable recommendations
│   └── VerifierAgent                             -> Factual consistency & anti-hallucination verification
├── Semantic RAG Subsystem (Level 3)
│   ├── Document Loader                           -> Manifest-driven parser with YAML frontmatter extraction
│   ├── Policy Chunker                            -> Heading-aware deterministic chunker with SHA-256 IDs
│   ├── Embedding Providers                       -> Lazy CPU SentenceTransformers & Offline Mock Provider
│   ├── ChromaDB Persistent Vector Store          -> Isolated local vector storage at data/vector_store/
│   ├── Semantic Policy Retriever                 -> Cosine similarity query + metadata filtering
│   ├── Policy Precedence Integration             -> Platform constraints > Platform > Category > Seller
│   └── CLI Indexing Command                      -> python -m backend.app.rag.index_policies
├── Real Support Tool Engine
│   └── 14 safe database tools (read order, read history, tickets, events, approval requests)
├── Core Application Config & Persistence
│   ├── Settings (Pydantic BaseSettings with root-anchored SQLite paths)
│   ├── Business Database: SQLite (data/resolveai.db) with 8 Domain Models
│   └── Checkpointer Database: SQLite (data/checkpoints.db) in WAL mode
└── Automated Testing
    ├── 100% Offline Test Suite (137 unit tests without internet or model downloads)
    └── Live Integration Suite (1 real SentenceTransformers + ChromaDB end-to-end test)
```

---

## 3. Level 3 Semantic RAG Foundation

### What RAG Does in ResolveAI
In ResolveAI, **Retrieval-Augmented Generation (RAG)** provides verifiable, factual grounding for automated support decisions. It retrieves unaltered, authoritative policy passages from the platform's knowledge base and provides them as evidence to downstream agents.
- **RAG does NOT generate answers or hallucinate rules**: Semantic retrieval finds and extracts existing policy prose with exact source metadata.
- **RAG does NOT replace human review or guarantee legal correctness**: If policies conflict or query relevance is below threshold, the system flags `needs_review: true` and `insufficient_evidence: true`.
- **Synthetic Policies Notice**: All policy documents in `data/policies/` are synthetic demonstration documents created solely for automated testing. They do not represent real-world commercial contracts or legal advice.

### Document Loading and Validation
- Policy files are registered in [`data/policies/manifest.json`](file:///C:/Users/User/Documents/ResolveAI/data/policies/manifest.json).
- The loader validates that every referenced Markdown file exists, resides strictly within the allowed `data/policies/` directory (preventing directory traversal), and has valid YAML frontmatter.
- YAML frontmatter metadata (`policy_id`, `version`, `effective_date`, `scope`, `seller_id`, `category`, `synthetic_policy`) is preserved while keeping raw frontmatter excluded from indexed prose.
- Legacy pointer documents (such as `return_policy.md` which redirects to `platform_return_refund_policy.md`) are automatically skipped during indexing to prevent redundant passages.

### Deterministic Heading-Aware Chunking
- Documents are split along Markdown headings (`## ` and `### `).
- Heading context is preserved inside each chunk (e.g., `## Electronics Policy — 2. Defective Items`).
- Chunks are bounded to approximately 400–700 tokens (or 1,800 characters) with sentence-boundary awareness.
- Every chunk receives a deterministic, immutable chunk ID computed via SHA-256 hash of its source file, section heading, chunk index, and content:
  ```python
  chunk_id = f"chk_{hashlib.sha256(...).hexdigest()[:16]}"
  ```
- Empty sections and trivial whitespace are safely pruned.

### Embedding Model Configuration
- **Model Identifier**: `sentence-transformers/all-MiniLM-L6-v2` (configured via `EMBEDDING_MODEL_NAME`).
- **Hardware Architecture**: 100% CPU inference; no GPU or CUDA required (engineered for 8 GB RAM machines).
- **Lifecycle**: Loaded lazily on first access and cached as an in-process singleton across requests.
- **Testing Isolation**: Unit tests utilize `MockEmbeddingProvider`, an offline signed feature-hashing implementation that requires **zero downloads, zero network calls, and zero external API keys**.

### ChromaDB Persistence & Idempotency
- **Persistence Location**: `data/vector_store/` (automatically excluded from Git via `.gitignore`).
- **Collection Name**: `policy_knowledge_base` (cosine distance metric `hnsw:space: "cosine"`).
- **Idempotent Synchronization**: When indexing runs:
  - Chunks whose content hash has not changed are skipped (`0 updated, 0 added, 91 unchanged`).
  - Modified chunks are upserted.
  - Chunks from deleted or renamed sections are pruned via ID reconciliation.
- **Safe Startup**: The API does NOT rebuild or wipe the vector store on startup, preventing startup delays or race conditions.

### Metadata Filtering & Precedence Hierarchy
Queries support fine-grained ChromaDB metadata filtering before distance calculation:
- `seller_id`: Normalized to match seller policies (`SELLER-001`, `SELLER-002`, `SELLER-003`, with backward-compatible support for `SLR-` prefixes).
- `category`: Restricts search to category-specific rules (`electronics`, `fashion`, `home_appliances`, `general_merchandise`).
- `scope`: Restricts by policy scope (`platform`, `category`, `seller`).
- `policy_version`: Filters by specific policy versions (e.g., `1.0.0`).

Retrieved candidate policies are evaluated against the platform's precedence engine ([`resolve_policy_precedence`](file:///C:/Users/User/Documents/ResolveAI/backend/app/core/policy_rules.py)):
1. **Platform Non-overridable Constraints** (Security, anti-fraud, audit logs)
2. **Platform-Wide Policies** (General return, refund, and cancellation policies)
3. **Category-Specific Policies** (Technical inspection requirements, hygiene seals)
4. **Seller-Specific Policies** (Merchant-specific SLAs, allowed only where permitted)

### Anti-Hallucination & Insufficient-Evidence Handling
- If query results exceed the semantic distance threshold (`RAG_DISTANCE_THRESHOLD = 0.80`), they are discarded.
- If no passages pass the threshold, the retriever returns:
  - `found_relevant: false`
  - `insufficient_evidence: true`
  - `passages: []`
  - Clear explanatory message citing the distance metrics.
- Similarity scores are never presented as probabilities or legal eligibility.

### Keyword Fallback Mechanism
If the ChromaDB collection is empty, the vector store fails to initialize, or the embedding model cannot load:
- The system automatically triggers the verified keyword search engine (`search_policy_documents`).
- The response explicitly reports `retrieval_method="keyword_fallback"`.
- The application never crashes due to a vector store failure.

---

## 4. Level 4: LangGraph Multi-Agent Orchestration

### What LangGraph Does in ResolveAI
LangGraph orchestrates the multi-agent customer support resolution lifecycle as a compiled stateful directed acyclic/cyclic graph (`StateGraph`). Rather than letting individual agents call each other informally or relying on uncontrolled autonomous agent loops, LangGraph enforces:
1. **Explicit, Strongly Typed State**: `WorkflowState` passes validated data between stages without mutable globals.
2. **Deterministic Conditional Branching**: Edge routing evaluates structured state attributes (`missing_order`, `policy_conflict_status`, `is_valid`, `retry_count`) rather than brittle text matching.
3. **Strict Bounded Recovery**: Verification failures trigger at most **one** controlled recovery re-recommendation (`max_retries=1`). If verification fails again, the workflow deterministically escalates to human review (`needs_review: true`), completely preventing infinite loops.
4. **Human Approval Boundaries**: High-value refunds (>₹25,000.00), policy precedence conflicts, or cases requiring supervisor review are routed to `escalate_case` and flagged `needs_review: true`, strictly preserving the Level 5 human-in-the-loop approval boundary.
5. **Safe Database & Event Persistence**: Database access and event recording utilize short-lived database transactions, ensuring zero open database transactions or locks during embedding inference.

### LangGraph Workflow Topology

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

### Strongly Typed Workflow State (`WorkflowState`)
Defined in `backend/app/workflows/state.py`:
- **Identifiers**: `workflow_id` (UUID4 string), `case_id` (optional int), `customer_id` (optional int), `order_number` (optional str).
- **Complaint Facts**: `complaint_text`, `complaint_analysis`, `complaint_category`, `urgency`, `missing_information`.
- **Order Facts**: `order_investigation`, `order_status`, `missing_order`.
- **Policy Evidence**: `retrieved_policy_passages`, `policy_source_metadata`, `retrieval_method`, `policy_conflict_status`, `insufficient_evidence`.
- **Recommendation**: `recommended_resolution`.
- **Verification**: `verification_result`, `is_valid`.
- **Routing & Control**: `workflow_status` (`in_progress`, `completed`, `needs_information`, `needs_review`, `failed`), `current_stage`, `escalation_reason`, `retry_count`, `max_retries` (default: 1), `errors`.
- **Audit & Metadata**: `events_recorded`, `created_at`, `updated_at`.

### Graph Nodes and Responsibilities
1. **`initialize_case_node`**: Generates `workflow_id` and `thread_id`, normalizes complaint text, optionally links or initializes database case, logs `workflow_started` audit event.
2. **`analyze_complaint_node`**: Invokes `ComplaintAnalyzerAgent`, extracts categories, urgency, and image relevance.
3. **`investigate_order_node`**: Uses short-lived DB session to invoke `OrderInvestigatorAgent`; detects if order exists or flags `missing_order = True`.
4. **`retrieve_policy_evidence_node`**: Runs `PolicyRetrieverAgent` against ChromaDB semantic vector store with category/seller metadata filters and `resolve_policy_precedence`.
5. **`recommend_resolution_node`**: Synthesizes evidence through `ResolutionRecommenderAgent` respecting INR paise financial tiers.
6. **`verify_resolution_node`**: Evaluates recommendation through `VerifierAgent` checking factuality, delivery truth, and policy alignment.
7. **`handle_missing_information_node`**: Terminal node for missing orders or ambiguous input; sets `workflow_status="needs_information"`.
8. **`escalate_case_node`**: Creates relational `ApprovalRequest` record in `data/resolveai.db`; routes to `supervisor_review`.
9. **`supervisor_review_node`**: Interruption point using LangGraph native `interrupt()`; persists execution snapshot to SQLite checkpointer; pauses until human supervisor decision is received.
10. **`attempt_recovery_node`**: Increments `retry_count`, attaches verifier critique, routes back to `recommend_resolution` for bounded recovery (`max_retries=1`).
11. **`record_resolution_node`**: Terminal node for verified valid recommendations; creates support ticket, records resolution event, and sets `workflow_status="completed"`.
12. **`finalize_response_node`**: Enforces safety invariants, normalizes timestamps, and prepares final response.

---

## 5. Level 5: Human-in-the-Loop Approval and Review

### Core Philosophy & Guardrails
ResolveAI enforces a strict boundary between automated AI analysis and sensitive operational execution:
- **No Unauthorized Execution**: AI agents analyze facts, retrieve policy evidence, and propose remedies. However, cases requiring supervisor approval (orders exceeding the Tier 1 threshold of ₹5,000.00 / 5,00,00paise, policy precedence conflicts, or unverified defect claims) are paused before any irreversible action is taken.
- **Safety Boundary**: Approving a case in ResolveAI executes the internal state transition, creates an indexed support ticket, and records immutable audit records. It **never executes real payment gateway disbursements, bank transfers, or physical shipments**.
- **Reviewer Identity**: Reviewer identity (`reviewer_id`) is submitted with decision payloads for demonstration and audit logging. Production OAuth/JWT authentication is acknowledged as an operational deployment constraint.

### Persistent SQLite Checkpointing
- **Dedicated Checkpoint Store**: To prevent database lock contention with SQLAlchemy domain models, LangGraph checkpoints are stored in an isolated SQLite database at `data/checkpoints.db`.
- **Write-Ahead Logging (WAL)**: Initialized with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` to support concurrent, thread-safe access.
- **Cross-Process Survival**: Paused workflows survive application restarts, container restarts, or crash recovery. A fresh graph instance loads the saved state directly from the SQLite checkpointer using `thread_id`.

### LangGraph Interruption & Resumption Protocol
1. **Pause**: In `supervisor_review_node`, calling `interrupt({...})` halts execution and saves the snapshot into `data/checkpoints.db`. The API returns HTTP 200 with `status="needs_review"`, `needs_review=true`, and the generated `thread_id`.
2. **Inspect**: Supervisors inspect pending cases via `GET /api/v1/workflows/pending-approvals` and `GET /api/v1/workflows/{thread_id}/approval`.
3. **Resume (Approve)**: `POST /api/v1/workflows/{thread_id}/approve` resumes the workflow using `Command(resume={"action": "approve", "reviewer_id": ...})`. The graph evaluates `route_after_supervisor_review`, verifies safety invariants, executes `record_resolution`, and finalizes with `status="completed"`.
4. **Resume (Reject)**: `POST /api/v1/workflows/{thread_id}/reject` requires a mandatory rejection reason and resumes using `Command(resume={"action": "reject", "reviewer_id": ...})`. The graph routes directly to `finalize_response`, bypassing `record_resolution` completely, and finalizes with `status="rejected"`.

### Defense-in-Depth Safety Invariants
Even if a supervisor approves a case:
- If the case has an unresolved policy conflict (`policy_conflict_status == "needs_review"`),
- If the order does not exist in the database,
- If policy evidence was insufficient, or
- If independent verification failed,
Both `route_after_supervisor_review` and `record_resolution_node` intercept the execution, refuse to mark the case as `completed`, and prevent false completion claims.

### Supervisor Review Command Center Dashboard (`GET /dashboard`)
A responsive, high-aesthetic web dashboard served directly by the backend:
- **Theme**: Deep navy background (`#080D1A`), midnight cards (`#131E35`), electric cyan accents (`#00D2FF`), verified green (`#10B981`), and danger red (`#EF4444`).
- **Live Queue**: Real-time list of pending approval checkpoints with formatted Indian Rupee pricing (`₹19,999.00`).
- **Deep Inspector**: Displays customer complaint quotes, stored order investigation facts, proposed AI resolution, and exact policy evidence passages.
- **Interactive Decision Controls**: Approve with optional supervisor notes; Reject with mandatory justification modal; real-time toast feedback and automated queue refresh.

---

## 6. Commands for Development and Testing

### Activate Virtual Environment (PowerShell)
```powershell
.\.venv\Scripts\Activate.ps1
```
Or execute commands directly with `.\.venv\Scripts\python.exe`.

### Indexing Policy Knowledge Base (PowerShell)

**1. Normal Indexing with SentenceTransformers (Downloads model on first run):**
```powershell
.\.venv\Scripts\python.exe -m backend.app.rag.index_policies
```

**2. Fast Offline / Mock Indexing (Zero model download, perfect for CI/CD):**
```powershell
.\.venv\Scripts\python.exe -m backend.app.rag.index_policies --mock
```

**3. Force Full Re-indexing (Resets collection and re-indexes all 91 chunks):**
```powershell
.\.venv\Scripts\python.exe -m backend.app.rag.index_policies --force
```

### Run Automated Tests

**Run Entire Test Suite (138 tests):**
```powershell
$env:HF_HUB_OFFLINE='1'; .\.venv\Scripts\python.exe -m pytest backend -v
```

**Run Level 5 Human Approval & Review Tests Only (10 tests):**
```powershell
$env:HF_HUB_OFFLINE='1'; .\.venv\Scripts\python.exe -m pytest backend/tests/test_workflow_human_approval.py -v
```

**Run Level 4 Multi-Agent Workflow Tests Only (29 tests):**
```powershell
$env:HF_HUB_OFFLINE='1'; .\.venv\Scripts\python.exe -m pytest backend/tests/test_workflow_state.py backend/tests/test_workflow_graph.py backend/tests/test_workflow_api.py backend/tests/test_workflow_correctness_audit.py -v
```

**Run Offline Unit Tests Only (137 tests, excludes live model inference):**
```powershell
$env:HF_HUB_OFFLINE='1'; .\.venv\Scripts\python.exe -m pytest backend -m "not integration" -v
```

**Run Live Integration Test Only (Real MiniLM + ChromaDB):**
```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_rag_live_integration.py -v
```

### Start Development Server
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --reload --port 8000
```
- Interactive OpenAPI documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Supervisor Review Command Center: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)

### Initialize and Seed Database
```powershell
.\.venv\Scripts\python.exe -m backend.app.database.init_db
.\.venv\Scripts\python.exe -m backend.app.database.seed
```

---

## 7. API Endpoints

### Workflow Resolution Endpoint (`POST /api/v1/workflows/resolve`)
Executes the compiled LangGraph multi-agent workflow coordinating complaint analysis, order investigation, RAG policy retrieval, resolution recommendation, verification, bounded recovery, and audit logging.

**Request Body:**
```json
{
  "complaint_text": "The laptop delivered for order ORD-2026-001 has a completely shattered screen.",
  "order_number": "ORD-2026-001",
  "customer_id": 1
}
```

**Response Body (High-Value Order Requiring Supervisor Approval):**
```json
{
  "workflow_id": "4b684cb6-5e04-453d-82d2-c2aa01a91d84",
  "case_id": 1,
  "case_number": "CASE-2026-0001",
  "status": "needs_review",
  "current_stage": "finalized",
  "complaint_analysis": {
    "category": "damaged_product",
    "urgency": "medium",
    "image_relevant": true,
    "analysis_method": "rule_based"
  },
  "order_investigation": {
    "order_number": "ORD-2026-001",
    "seller_id": "SELLER-001",
    "item_category": "electronics",
    "total_amount_paise": 1499900,
    "delivery_status": "delivered"
  },
  "policy_evidence": {
    "query": "The laptop delivered for order ORD-2026-001 has a completely shattered screen.",
    "passages": [
      {
        "document_name": "category_electronics_policy.md",
        "passage": "## Category Policy — 2. Defective Items\n\nCustomers must report dead-on-arrival or damaged screens within 7 calendar days of confirmed delivery for replacement.",
        "matched_terms": [],
        "line_number": null,
        "policy_id": "POL-CAT-001",
        "scope": "category"
      }
    ],
    "found_relevant": true,
    "retrieval_method": "semantic_search",
    "explanation": "Retrieved via workflow orchestration.",
    "policy_ids": ["POL-CAT-001"],
    "source_files": ["category_electronics_policy.md"],
    "conflict_status": "resolved",
    "needs_review": false,
    "insufficient_evidence": false
  },
  "retrieval_method": "semantic_search",
  "recommended_resolution": {
    "recommendation_type": "recommend_replacement_review",
    "title": "Recommend Replacement Under Damage Policy",
    "reasoning": "Customer reported damaged product (Ultra-Slim Laptop 14-inch). Order total is ₹14,999.00. Exceeds Tier 1 threshold (₹5,000.00), requiring Tier 2 supervisor approval.",
    "action_required": "Review uploaded photo/unboxing evidence and create replacement approval request.",
    "human_approval_required": true,
    "missing_information": [],
    "evidence_used": ["Order: ORD-2026-001", "Seller: SELLER-001"],
    "method": "rule_based"
  },
  "verification_result": {
    "verification_status": "pass",
    "is_valid": true,
    "detected_issues": [],
    "evidence_checked": ["order_exists", "delivery_status_delivered"],
    "missing_evidence": [],
    "required_next_step": "supervisor_approval"
  },
  "needs_review": true,
  "escalation_reason": "High-value order or sensitive resolution requires supervisor sign-off (Recommend Replacement Under Damage Policy).",
  "missing_information": [],
  "errors": [],
  "retry_count": 0,
  "events_recorded": [
    {"event_type": "workflow_started", "message": "Workflow initiated for case 1"},
    {"event_type": "order_investigation_completed", "message": "Order investigation completed"},
    {"event_type": "policy_evidence_retrieved", "message": "Policy retrieval via semantic_search"},
    {"event_type": "resolution_recommended", "message": "Recommendation generated"},
    {"event_type": "resolution_verification_passed", "message": "Verification result: status=pass, valid=True"},
    {"event_type": "case_needs_review", "message": "Case escalated to supervisor queue"}
  ],
  "created_at": "2026-10-09T18:43:17.102931Z",
  "updated_at": "2026-10-09T18:43:37.492104Z"
}
```

### Policy Search Endpoint (`POST /api/v1/search-policies`)
Performs semantic vector search across the indexed knowledge base with automatic keyword fallback.

**Request Body:**
```json
{
  "query": "laptop screen defective on arrival replacement policy",
  "seller_id": "SELLER-001",
  "category": "electronics",
  "scope": null,
  "policy_version": null,
  "method": "semantic"
}
```

**Response Body:**
```json
{
  "query": "laptop screen defective on arrival replacement policy",
  "found_relevant": true,
  "retrieval_method": "semantic_search",
  "passages": [
    {
      "document_name": "category_electronics_policy.md",
      "passage": "## Category Policy — 2. Defective Items\n\nCustomers must report dead-on-arrival or damaged screens within 7 calendar days of confirmed delivery for replacement.",
      "matched_terms": ["cosine_dist:0.467"],
      "line_number": 2,
      "policy_id": "POL-CAT-001",
      "scope": "category"
    }
  ],
  "policy_ids": ["POL-CAT-001", "POL-PLAT-002"],
  "source_files": ["data/policies/category_electronics_policy.md"],
  "conflict_status": "resolved",
  "needs_review": false,
  "insufficient_evidence": false,
  "explanation": "Retrieved 5 relevant policy passage(s) via semantic vector search. Precedence status: resolved. Category-specific policy [POL-CAT-001] applied for category 'electronics'."
}
```

---

## 7. Common Windows Notes & Troubleshooting

1. **HuggingFace Symlinks Warning**:
   On Windows 11 without Developer Mode enabled, `huggingface_hub` issues a non-fatal warning about symlinks. File caching still functions normally in standard file copy mode.
2. **C++ Build Tools Not Required**:
   `chromadb` 1.5.x and `sentence-transformers` 6.x include precompiled Windows wheels; Microsoft Visual C++ Build Tools are not required for standard installation.
3. **Memory Optimization**:
   The `all-MiniLM-L6-v2` model consumes ~80 MB on disk and ~250 MB RAM in memory, operating safely within the target 8 GB RAM laptop environment.
