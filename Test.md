flowchart TD
    A["POST /chat"] --> B["Authenticate identity"]
    B --> C["Load permissions (role, vertical)"]
    C --> D["Intent router"]

    %% Fast Paths
    D -->|Clarification| E["Clarify / checkpoint"]
    E --> D
    D -->|Greeting| G["Greeting response"]
    D -->|Document RAG| H["RBAC-filtered document retrieval"]

    %% Core SQL & Hybrid
    D -->|SQL or hybrid| I["Permission-filtered schema retrieval"]
    D -->|"Hybrid (parallel)"| J["RBAC-filtered entity retrieval"]

    I --> K{"Authorized schema found?"}
    K -->|No| R["Deterministic refusal"]
    K -->|Yes| L["Validate authorized join paths"]

    %% Join Security Check
    L --> L_CHECK{"Valid authorized path?"}
    L_CHECK -->|Blocked bridge| R
    L_CHECK -->|Valid path or single table| M["Prune schema and mask columns"]

    %% Synchronization Barrier
    M --> N["Enrichment barrier (FewShot, Entity Links)"]
    J --> N
    N --> O["Generate SQL"]

    O --> P["Check schema sufficiency"]
    P -->|Expand within budget| I
    P -->|Sufficient| Q{"AST and RBAC validation"}

    %% Split AST failure modes
    Q -->|Security breach or forbidden write| S["Abort and audit"]
    Q -->|Syntax error with retries left| O
    Q -->|Valid SELECT| T["Read-only SQL execution"]

    %% Execution & Recovery
    T -->|Success| U["Result synthesis"]
    T -->|Execution error| V{"Retry budget remains?"}
    V -->|Yes| O
    V -->|No| W["Controlled recovery"]

    %% Unification
    H --> X["Document answer synthesis"]
    G --> Y["Finalize"]
    R --> Y
    S --> Y
    W --> Y
    U --> Y
    X --> Y
    Y --> Z["Persist safely"]

    
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal
from typing_extensions import NotRequired, TypedDict


# ============================================================
# 1. Identity and authorization
# ============================================================

class UserIdentity(TypedDict):
    """Resolved from a trusted authentication and authorization layer."""
    email: str
    role: str
    vertical_code: str


class AuthorizationContext(TypedDict):
    """Authorization context loaded from a trusted policy source."""
    authorization_status: Literal["PENDING", "ALLOWED", "DENIED"]
    authorized_table_ids: list[str]
    authorized_column_ids: list[str]
    policy_version: str


# ============================================================
# 2. Schema and table metadata
# ============================================================

class TableMetadata(TypedDict):
    """Schema metadata returned by permission-filtered retrieval."""
    table_id: str
    table_name: str
    vertical_domain: str
    primary_keys: list[str]
    allowed_columns: list[str]
    similarity_score: float


class JoinEdge(TypedDict):
    """A join relationship verified against the authorization policy."""
    source_table: str
    target_table: str
    join_type: Literal["INNER JOIN", "LEFT JOIN", "RIGHT JOIN"]
    join_condition: str
    is_bridge: bool


class GroundedEntity(TypedDict):
    """An entity/value candidate retrieved from authorized row embeddings."""
    table_id: str
    column_name: str
    matched_value: str
    similarity: float


class FewShotExample(TypedDict):
    """A vetted example for SQL generation."""
    question: str
    sql: str


# ============================================================
# 3. Document retrieval and citations
# ============================================================

class DocumentChunk(TypedDict):
    """An authorized document chunk retrieved for RAG."""
    document_id: str
    chunk_id: str
    content: str
    source: str
    page_number: int | None
    similarity_score: float


class Citation(TypedDict):
    """A source reference used to support the final answer."""
    source_id: str
    source_type: Literal["document", "sql_result"]
    title: str
    locator: str


# ============================================================
# 4. SQL AST validation
# ============================================================

class ASTValidationResult(TypedDict):
    """Result of parsing and validating generated SQL."""
    status: Literal[
        "NOT_CHECKED",
        "VALID",
        "SYNTAX_ERROR",
        "SECURITY_VIOLATION",
    ]
    error_message: str | None
    referenced_tables: list[str]
    referenced_columns: list[str]
    detected_write_ops: list[str]


# ============================================================
# 5. Execution and recovery
# ============================================================

class QueryExecutionMetadata(TypedDict):
    """Execution outcome and bounded-result metadata."""
    status: Literal["NOT_RUN", "SUCCESS", "ERROR", "BLOCKED"]
    row_count: int
    truncated: bool
    duration_ms: int | None


# ============================================================
# 6. Central LangGraph shared state
# ============================================================

class RAGState(TypedDict):
    # --------------------------------------------------------
    # A. Request and identity
    # --------------------------------------------------------
    question: str
    thread_id: str
    identity: UserIdentity
    authorization: AuthorizationContext

    original_question: NotRequired[str]
    clarification_prompt: NotRequired[str | None]
    clarification_response: NotRequired[str | None]
    needs_clarification: NotRequired[bool]

    # --------------------------------------------------------
    # B. Routing
    # --------------------------------------------------------
    intent: NotRequired[
        Literal[
            "sql",
            "hybrid",
            "rag",
            "greet",
            "clarify",
            "out_of_scope",
        ]
    ]

    # --------------------------------------------------------
    # C. Schema retrieval
    # --------------------------------------------------------
    schema_retrieval_status: NotRequired[
        Literal["NOT_RUN", "FOUND", "EMPTY", "ERROR"]
    ]

    retrieved_tables: NotRequired[list[TableMetadata]]

    # A retrieval result, not an independent authorization source.
    authorized_table_ids: NotRequired[list[str]]

    # --------------------------------------------------------
    # D. Join discovery
    # --------------------------------------------------------
    join_path_status: NotRequired[
        Literal[
            "NOT_CHECKED",
            "SINGLE_TABLE",
            "CONNECTED",
            "BLOCKED_BRIDGE",
            "NO_VALID_PATH",
        ]
    ]

    join_paths: NotRequired[list[JoinEdge]]
    join_clauses: NotRequired[list[str]]

    # Only authorized columns should appear in this prompt schema.
    pruned_ddl: NotRequired[str]

    # --------------------------------------------------------
    # E. Parallel retrieval and enrichment
    # --------------------------------------------------------

    # Parallel workers append their new results using these reducers.
    grounded_entities: Annotated[
        list[GroundedEntity], operator.add
    ]

    few_shot_examples: Annotated[
        list[FewShotExample], operator.add
    ]

    document_chunks: Annotated[
        list[DocumentChunk], operator.add
    ]

    # Status fields should be set by their coordinating nodes.
    entity_retrieval_status: NotRequired[
        Literal["NOT_RUN", "FOUND", "EMPTY", "ERROR"]
    ]

    few_shot_retrieval_status: NotRequired[
        Literal["NOT_RUN", "FOUND", "EMPTY", "ERROR"]
    ]

    document_retrieval_status: NotRequired[
        Literal["NOT_RUN", "FOUND", "EMPTY", "ERROR"]
    ]

    # --------------------------------------------------------
    # F. SQL generation and schema expansion
    # --------------------------------------------------------
    generated_sql: NotRequired[str | None]

    # Values are bound separately by the database execution layer.
    sql_parameters: NotRequired[list[Any]]

    schema_expansion_count: int
    max_schema_expansions: int

    schema_gap_reason: NotRequired[str | None]

    # --------------------------------------------------------
    # G. AST guardrails
    # --------------------------------------------------------
    ast_validation: NotRequired[ASTValidationResult]

    # --------------------------------------------------------
    # H. SQL execution
    # --------------------------------------------------------
    query_results: NotRequired[list[dict[str, Any]] | None]

    execution_metadata: NotRequired[QueryExecutionMetadata]

    sql_execution_error: NotRequired[str | None]

    # --------------------------------------------------------
    # I. Independent retry budgets
    # --------------------------------------------------------
    sql_generation_retries: int
    max_sql_generation_retries: int

    execution_retries: int
    max_execution_retries: int

    error_history: Annotated[list[str], operator.add]

    # --------------------------------------------------------
    # J. Final answer and audit outcome
    # --------------------------------------------------------
    final_answer: NotRequired[str | None]
    citations: NotRequired[list[Citation]]

    outcome: NotRequired[
        Literal[
            "SUCCESS",
            "CLARIFICATION",
            "OUT_OF_SCOPE",
            "ACCESS_DENIED",
            "SECURITY_ABORT",
            "RECOVERY_FAILED",
            "ERROR",
        ]
    ]

    # An identifier for a separately persisted audit event.
    # Do not store credentials or secrets here.
    audit_event_id: NotRequired[str | None]

from state import RAGState, UserIdentity, AuthorizationContext


def create_initial_state(
    question: str,
    thread_id: str,
    identity: UserIdentity,
    authorization: AuthorizationContext,
) -> RAGState:
    return {
        "question": question,
        "thread_id": thread_id,
        "identity": identity,
        "authorization": authorization,

        "grounded_entities": [],
        "few_shot_examples": [],
        "document_chunks": [],
        "error_history": [],

        "schema_expansion_count": 0,
        "max_schema_expansions": 2,

        "sql_generation_retries": 0,
        "max_sql_generation_retries": 2,

        "execution_retries": 0,
        "max_execution_retries": 2,
    }

CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS ai_search;


-- =========================================================
-- A. Schema embeddings: tables and columns
-- =========================================================

CREATE TABLE ai_search.schema_embeddings (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY
                        PRIMARY KEY,

    object_type         TEXT NOT NULL
                        CHECK (object_type IN ('table', 'column')),

    schema_name         TEXT NOT NULL,
    table_name          TEXT NOT NULL,
    column_name         TEXT,

    object_description  TEXT NOT NULL,
    searchable_text     TEXT NOT NULL,

    data_type           TEXT,
    is_primary_key      BOOLEAN NOT NULL DEFAULT FALSE,

    vertical_code       TEXT NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,

    embedding           VECTOR(1536) NOT NULL,

    embedding_model     TEXT NOT NULL,
    embedding_version   INTEGER NOT NULL DEFAULT 1,

    source_updated_at   TIMESTAMPTZ,
    embedded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE NULLS NOT DISTINCT (
        schema_name,
        table_name,
        column_name
    ),

    CHECK (
        (object_type = 'table' AND column_name IS NULL)
        OR
        (object_type = 'column' AND column_name IS NOT NULL)
    )
);

CREATE INDEX schema_embeddings_scope_idx
    ON ai_search.schema_embeddings
       (vertical_code, is_active, object_type);

CREATE INDEX schema_embeddings_table_idx
    ON ai_search.schema_embeddings
       (schema_name, table_name);


-- =========================================================
-- B. Row value embeddings: entity linking
-- =========================================================

CREATE TABLE ai_search.row_value_embeddings (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY
                        PRIMARY KEY,

    source_schema       TEXT NOT NULL,
    source_table        TEXT NOT NULL,
    source_pk           JSONB NOT NULL,

    column_name         TEXT NOT NULL,
    matched_value       TEXT NOT NULL,
    searchable_text     TEXT NOT NULL,

    vertical_code       TEXT NOT NULL,

    embedding           VECTOR(1536) NOT NULL,

    embedding_model     TEXT NOT NULL,
    embedding_version   INTEGER NOT NULL DEFAULT 1,

    source_updated_at   TIMESTAMPTZ,
    embedded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (
        source_schema,
        source_table,
        source_pk,
        column_name,
        embedding_version
    )
);

CREATE INDEX row_value_embeddings_source_idx
    ON ai_search.row_value_embeddings
       (source_schema, source_table, column_name);

CREATE INDEX row_value_embeddings_scope_idx
    ON ai_search.row_value_embeddings
       (vertical_code);


-- =========================================================
-- C. Document chunk embeddings
-- =========================================================

CREATE TABLE ai_search.document_chunk_embeddings (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY
                        PRIMARY KEY,

    document_id         TEXT NOT NULL,
    chunk_id            TEXT NOT NULL,

    document_title      TEXT,
    source_uri          TEXT,
    page_number         INTEGER,
    chunk_text          TEXT NOT NULL,

    vertical_code       TEXT NOT NULL,

    embedding           VECTOR(1536) NOT NULL,

    embedding_model     TEXT NOT NULL,
    embedding_version   INTEGER NOT NULL DEFAULT 1,

    content_hash        TEXT NOT NULL,
    source_updated_at   TIMESTAMPTZ,
    embedded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (document_id, chunk_id, embedding_version)
);

CREATE INDEX document_embeddings_scope_idx
    ON ai_search.document_chunk_embeddings
       (vertical_code, document_id);

CREATE INDEX document_embeddings_hash_idx
    ON ai_search.document_chunk_embeddings
       (content_hash);

