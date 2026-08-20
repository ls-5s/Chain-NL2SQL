export type QueryStatus = "running" | "succeeded" | "blocked" | "failed";

export type QueryIntent = "data_query" | "general_chat" | "clarification";

export type ErrorCategory =
  | "syntax_error"
  | "unknown_column"
  | "unknown_table"
  | "join_error"
  | "aggregation_error"
  | "invalid_model_output"
  | "permission_error"
  | "connection_error"
  | "unsafe_sql"
  | "schema_changed"
  | "schema_retrieval_error"
  | "unknown";

export interface QueryRequest {
  question: string;
  database_id: string;
  max_iterations?: number;
}

export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
}

export interface TraceEvent {
  node: string;
  iteration: number;
  duration_ms?: number | null;
  error_category?: ErrorCategory | null;
  retrieved_document_count?: number | null;
}

export interface SchemaSummary {
  table_name: string;
  columns: string[];
  description?: string;
}

export interface KnowledgeHit {
  document_id: string;
  title: string;
  category: string;
  excerpt: string;
  relevance: number;
}

export interface QueryResponse {
  request_id: string;
  intent: QueryIntent;
  intent_confidence?: number | null;
  intent_reason?: string | null;
  intent_source?: "rule" | "llm" | null;
  status: QueryStatus;
  iteration: number;
  error_category?: ErrorCategory | null;
  final_answer: string;
  result?: QueryResult | null;
  trace: TraceEvent[];
  generated_sql?: string | null;
  schema_summary?: SchemaSummary[];
  knowledge_hits?: KnowledgeHit[];
}

export interface QueryStreamEvent {
  request_id?: string;
  node?: string;
  status?: QueryStatus;
  iteration?: number;
  message?: string;
  error_category?: ErrorCategory | null;
  retrieved_document_count?: number;
  detail?: string;
  status_code?: number;
  explanation?: string;
  tables?: string[];
  sql?: string;
  validated?: boolean;
  row_count?: number;
  retrieval_mode?: "vector" | "bm25" | "hybrid" | "full_schema";
  intent?: QueryIntent;
  classification_valid?: boolean;
  confidence?: number;
  source?: "rule" | "llm";
  reason?: string;
}

export interface DatabaseListResponse {
  database_ids: string[];
}

export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface ApprovalHistoryEntry {
  action: "submitted" | "approved" | "rejected";
  actor: string;
  occurred_at: string;
  note?: string;
}

export interface ApprovalItem {
  id: string;
  request_id: string;
  database_id: string;
  title: string;
  masked_sql: string;
  schema_summary: SchemaSummary[];
  risk_reason: string;
  status: ApprovalStatus;
  created_at: string;
  history: ApprovalHistoryEntry[];
}

export type KnowledgeDocumentStatus = "uploading" | "parsing" | "indexed" | "failed";

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_type: "TXT" | "MD" | "PDF" | "DOCX" | "CSV";
  size_bytes: number;
  category: string;
  status: KnowledgeDocumentStatus;
  created_at: string;
  chunk_count?: number;
  summary: string;
  failure_message?: string;
}

export interface KnowledgeUploadResult {
  document: KnowledgeDocument;
}
