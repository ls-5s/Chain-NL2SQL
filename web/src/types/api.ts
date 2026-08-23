export type QueryStatus = "running" | "succeeded" | "blocked" | "failed" | "needs_clarification" | "no_grounded_answer";

export type QueryIntent = "data_query" | "general_chat" | "clarify";

export type AnswerSource = "general_llm" | "result_summary" | "deterministic_fallback";

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
  database_id?: string | null;
  max_iterations?: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface SessionResponse {
  authenticated: boolean;
  username?: string | null;
  role?: UserRole | null;
}

export type UserRole = "super_admin" | "member";

export interface Member {
  id: string;
  username: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

export interface MemberCreateRequest {
  username: string;
  password: string;
}

export interface MemberUpdateRequest {
  username?: string;
  password?: string;
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
  answer_source?: AnswerSource | null;
  status: QueryStatus;
  iteration: number;
  error_category?: ErrorCategory | null;
  final_answer: string;
  result?: QueryResult | null;
  trace: TraceEvent[];
  generated_sql?: string | null;
  schema_summary?: SchemaSummary[];
  knowledge_hits?: KnowledgeHit[];
  clarification_fields?: string[];
  required_actions?: string[];
}

export interface QueryStreamEvent {
  request_id?: string;
  node?: string;
  status?: QueryStatus;
  iteration?: number;
  message?: string;
  error_category?: ErrorCategory | null;
  retrieved_document_count?: number;
  retrieved_knowledge_count?: number;
  knowledge_available?: boolean;
  detail?: string;
  status_code?: number;
  explanation?: string;
  tables?: string[];
  sql?: string;
  validated?: boolean;
  row_count?: number;
  guarded?: boolean;
  answer_source?: AnswerSource | null;
  retrieval_mode?: "vector" | "bm25" | "hybrid" | "full_schema";
  intent?: QueryIntent;
  classification_valid?: boolean;
  confidence?: number;
  source?: "rule" | "llm";
  reason?: string;
  phase?: "start" | "progress" | "complete" | "error";
}

export interface DatabaseListResponse {
  database_ids: string[];
  databases?: Database[];
}

export type DatabaseDialect = "sqlite" | "mysql";

export interface DatabaseTable {
  table_name: string;
  agent_access: boolean;
  updated_at: string;
}

export interface Database {
  id: string;
  name: string;
  dialect: DatabaseDialect;
  enabled: boolean;
  config: Record<string, unknown>;
  tables: DatabaseTable[];
  created_at: string;
  updated_at: string;
}

export interface DatabaseCreateRequest {
  name: string;
  dialect: DatabaseDialect;
  config: Record<string, unknown>;
}

export interface DatabaseUpdateRequest {
  name?: string;
  config?: Record<string, unknown>;
  enabled?: boolean;
}

export interface ConversationSummary {
  id: string;
  title: string;
  database_id: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationMessage {
  id: string;
  turn_id: string;
  role: "user" | "assistant";
  content: string;
  status: QueryStatus;
  response?: QueryResponse | null;
  progress: QueryStreamEvent[];
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessage[];
  pending_clarification?: { fields?: string[]; required_actions?: string[] } | null;
}

export interface ResultReferenceResponse {
  id: string;
  label: string;
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
  updated_at?: string;
  chunk_count?: number;
  summary: string;
  failure_message?: string;
}

export interface KnowledgeUploadResult {
  document: KnowledgeDocument;
}
