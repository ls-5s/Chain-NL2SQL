import type {
  ApprovalItem,
  ApprovalStatus,
  KnowledgeDocument,
  KnowledgeDocumentStatus,
  QueryRequest,
  QueryResponse,
} from "@/types/api";

const now = () => new Date().toISOString();

const documents: KnowledgeDocument[] = [
  { id: "kb-metric-definition", filename: "销售指标口径.md", file_type: "MD", size_bytes: 18_432, category: "指标口径", status: "indexed", created_at: "2026-08-18T08:30:00.000Z", chunk_count: 12, summary: "定义销售额、退款额与净销售额的计算范围及时间口径。" },
  { id: "kb-order-dictionary", filename: "订单数据字典.csv", file_type: "CSV", size_bytes: 9_861, category: "数据字典", status: "indexed", created_at: "2026-08-18T08:32:00.000Z", chunk_count: 8, summary: "说明订单、商品和客户相关字段的业务含义与取值。" },
];

const approvals: ApprovalItem[] = [
  {
    id: "approval-001", request_id: "req_20260818_001", database_id: "demo", title: "按地区汇总本月净销售额",
    masked_sql: "SELECT region, SUM(amount - refund_amount) AS net_sales FROM orders WHERE created_at >= :month_start GROUP BY region ORDER BY net_sales DESC",
    schema_summary: [{ table_name: "orders", columns: ["region", "amount", "refund_amount", "created_at"], description: "订单事实表" }],
    risk_reason: "涉及销售金额聚合，执行前需要确认数据访问范围。", status: "pending", created_at: "2026-08-18T09:20:00.000Z",
    history: [{ action: "submitted", actor: "系统", occurred_at: "2026-08-18T09:20:00.000Z" }],
  },
  {
    id: "approval-002", request_id: "req_20260818_002", database_id: "demo", title: "查询高价值客户订单",
    masked_sql: "SELECT customer_id, COUNT(*) AS order_count FROM orders WHERE amount >= :threshold GROUP BY customer_id ORDER BY order_count DESC LIMIT 50",
    schema_summary: [{ table_name: "orders", columns: ["customer_id", "amount"], description: "订单事实表" }],
    risk_reason: "按客户维度聚合，结果字段将由服务端策略进一步脱敏。", status: "approved", created_at: "2026-08-18T08:45:00.000Z",
    history: [{ action: "submitted", actor: "系统", occurred_at: "2026-08-18T08:45:00.000Z" }, { action: "approved", actor: "演示审批员", occurred_at: "2026-08-18T08:48:00.000Z" }],
  },
];

function wait(milliseconds = 260): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export async function mockDatabases(): Promise<string[]> { await wait(120); return ["demo", "sales_analytics"]; }

export async function mockQuery(payload: QueryRequest): Promise<QueryResponse> {
  await wait(520);
  const question = payload.question.toLowerCase();
  const schemaSummary = [
    { table_name: "orders", columns: ["order_id", "product_id", "amount", "created_at"], description: "订单事实表" },
    { table_name: "products", columns: ["product_id", "product_name", "category"], description: "商品维表" },
  ];
  const knowledgeHits = documents.filter((document) => document.status === "indexed").slice(0, 2).map((document, index) => ({ document_id: document.id, title: document.filename, category: document.category, excerpt: document.summary, relevance: 0.92 - index * 0.08 }));
  if (question.includes("危险") || question.includes("删除") || question.includes("drop")) {
    return { request_id: "req_demo_blocked", status: "blocked", iteration: 0, error_category: "unsafe_sql", final_answer: "该请求包含不允许的写入或高危操作，已在执行前拦截。", result: null, schema_summary: schemaSummary, knowledge_hits: knowledgeHits, generated_sql: null, trace: [{ node: "retrieve_schema", iteration: 0, duration_ms: 42, retrieved_document_count: 2 }, { node: "validate_sql", iteration: 0, duration_ms: 11, error_category: "unsafe_sql" }] };
  }
  if (question.includes("失败") || question.includes("错误")) {
    return { request_id: "req_demo_failed", status: "failed", iteration: 1, error_category: "unknown_column", final_answer: "未能确认请求中的字段含义，已在受控轮次内停止重试。", result: null, schema_summary: schemaSummary, knowledge_hits: knowledgeHits, generated_sql: "SELECT product_title FROM orders LIMIT 20", trace: [{ node: "retrieve_schema", iteration: 0, duration_ms: 48, retrieved_document_count: 2 }, { node: "generate_sql", iteration: 0, duration_ms: 358 }, { node: "execute_sql", iteration: 0, duration_ms: 16, error_category: "unknown_column" }, { node: "repair_sql", iteration: 1, duration_ms: 274 }, { node: "execute_sql", iteration: 1, duration_ms: 15, error_category: "unknown_column" }] };
  }
  const empty = question.includes("空") || question.includes("没有");
  return { request_id: "req_demo_success", status: "succeeded", iteration: 0, final_answer: empty ? "查询已完成，当前筛选条件下没有匹配记录。" : "查询已完成，以下为按销售额排序的商品汇总。", result: { columns: ["商品", "销售额", "订单数"], rows: empty ? [] : [["无线耳机", 128_600, 842], ["便携显示器", 96_240, 415], ["机械键盘", 73_890, 326]], row_count: empty ? 0 : 3, truncated: false }, schema_summary: schemaSummary, knowledge_hits: knowledgeHits, generated_sql: "SELECT p.product_name AS 商品, SUM(o.amount) AS 销售额, COUNT(*) AS 订单数 FROM orders o JOIN products p ON o.product_id = p.product_id GROUP BY p.product_name ORDER BY 销售额 DESC LIMIT 5", trace: [{ node: "retrieve_schema", iteration: 0, duration_ms: 43, retrieved_document_count: 2 }, { node: "generate_sql", iteration: 0, duration_ms: 312 }, { node: "validate_sql", iteration: 0, duration_ms: 14 }, { node: "execute_sql", iteration: 0, duration_ms: 22 }, { node: "finalize", iteration: 0, duration_ms: 3 }] };
}

export async function mockApprovals(): Promise<ApprovalItem[]> { await wait(160); return approvals.map((item) => ({ ...item, history: [...item.history] })); }

export async function mockResolveApproval(id: string, status: Extract<ApprovalStatus, "approved" | "rejected">): Promise<ApprovalItem> {
  await wait(220);
  const item = approvals.find((approval) => approval.id === id);
  if (!item) throw new Error("未找到审批记录。");
  item.status = status;
  item.history.push({ action: status, actor: "演示审批员", occurred_at: now() });
  return { ...item, history: [...item.history] };
}

export async function mockKnowledgeDocuments(): Promise<KnowledgeDocument[]> { await wait(160); return documents.map((document) => ({ ...document })); }

export async function mockUploadKnowledge(file: File, category: string): Promise<KnowledgeDocument> {
  await wait(260);
  const extension = file.name.split(".").pop()?.toUpperCase() || "TXT";
  const document: KnowledgeDocument = { id: `kb-${Date.now()}`, filename: file.name, file_type: extension === "MARKDOWN" ? "MD" : (extension as KnowledgeDocument["file_type"]), size_bytes: file.size, category, status: "uploading", created_at: now(), summary: "本地演示文件，索引后可作为查询上下文摘要显示。" };
  documents.unshift(document);
  window.setTimeout(() => updateKnowledgeStatus(document.id, "parsing"), 450);
  window.setTimeout(() => {
    const failed = file.name.toLowerCase().includes("fail");
    updateKnowledgeStatus(document.id, failed ? "failed" : "indexed", failed ? undefined : 6, failed ? "演示索引失败，请重试。" : undefined);
  }, 1_050);
  return { ...document };
}

function updateKnowledgeStatus(id: string, status: KnowledgeDocumentStatus, chunkCount?: number, failureMessage?: string): void {
  const document = documents.find((item) => item.id === id);
  if (!document) return;
  document.status = status;
  document.chunk_count = chunkCount;
  document.failure_message = failureMessage;
}

export async function mockDeleteKnowledge(id: string): Promise<void> { await wait(180); const index = documents.findIndex((document) => document.id === id); if (index >= 0) documents.splice(index, 1); }
