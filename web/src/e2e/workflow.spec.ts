import { expect, test } from "@playwright/test";

type Conversation = {
  id: string;
  title: string;
  database_id: string | null;
  created_at: string;
  updated_at: string;
  messages: object[];
};

function sse(response: object) {
  return `event: start\ndata: ${JSON.stringify({ request_id: "e2e-request", phase: "start" })}\n\nevent: progress\ndata: ${JSON.stringify({ request_id: "e2e-request", phase: "progress", node: "intent_gate", status: "running", message: "正在理解问题" })}\n\nevent: complete\ndata: ${JSON.stringify({ ...response, request_id: "e2e-request", phase: "complete" })}\n\n`;
}

test("keeps an unbound conversation through chat, clarification, database selection, and refresh", async ({ page }) => {
  const conversations = new Map<string, Conversation>();
  let nextConversation = 1;
  const document = {
    id: "doc-1", filename: "销售指标口径.md", file_type: "MD", size_bytes: 24, category: "指标口径", status: "indexed",
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", chunk_count: 1, summary: "销售额按订单明细汇总", failure_message: null,
    acl: { policy_type: "deny", role: null, user_id: null },
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const json = (body: object, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/v1/auth/session") return json({ authenticated: false, username: null, role: null });
    if (path === "/api/v1/auth/login") return json({ authenticated: true, username: "admin", role: "super_admin" });
    if (path === "/api/v1/databases") return json({ database_ids: ["demo"], databases: [] });
    if (path === "/api/v1/knowledge" && request.method() === "GET") return json([document]);
    if (path === "/api/v1/knowledge/doc-1/acl" && request.method() === "PATCH") {
      Object.assign(document.acl, JSON.parse(request.postData() || "{}"));
      document.acl.role ??= null;
      document.acl.user_id ??= null;
      return json(document);
    }
    if (path === "/api/v1/conversations" && request.method() === "GET") {
      return json([...conversations.values()].map(({ messages, ...summary }) => ({ ...summary, message_count: messages.length })));
    }
    if (path === "/api/v1/conversations" && request.method() === "POST") {
      const id = `conversation-${nextConversation++}`;
      const now = "2026-01-01T00:00:00Z";
      const conversation = { id, title: "新聊天", database_id: null, created_at: now, updated_at: now, messages: [] };
      conversations.set(id, conversation);
      return json({ ...conversation, message_count: 0 });
    }
    const conversationMatch = path.match(/^\/api\/v1\/conversations\/([^/]+)$/);
    if (conversationMatch && request.method() === "GET") {
      const conversation = conversations.get(conversationMatch[1]);
      return json({ ...conversation, message_count: conversation?.messages.length ?? 0, pending_clarification: null });
    }
    const bindMatch = path.match(/^\/api\/v1\/conversations\/([^/]+)\/database$/);
    if (bindMatch && request.method() === "POST") {
      const conversation = conversations.get(bindMatch[1])!;
      if (conversation.database_id) return json({ detail: "A database has already been selected for this conversation." }, 409);
      conversation.database_id = JSON.parse(request.postData() || "{}").database_id;
      return json({ bound: true, database_id: conversation.database_id });
    }
    const queryMatch = path.match(/^\/api\/v1\/conversations\/([^/]+)\/query$/);
    if (queryMatch && request.method() === "POST") {
      const conversation = conversations.get(queryMatch[1])!;
      const question = JSON.parse(request.postData() || "{}").question as string;
      const response = question === "你好"
        ? { intent: "general_chat", intent_confidence: 0.98, status: "succeeded", iteration: 0, final_answer: "你好，我可以协助分析数据。", answer_source: "general_llm", trace: [] }
        : question === "帮我看看数据"
          ? { intent: "clarify", status: "needs_clarification", iteration: 0, final_answer: "为了继续处理，请补充：业务对象、指标或操作、时间范围。", answer_source: "deterministic_fallback", clarification_fields: ["业务对象", "指标或操作", "时间范围"], required_actions: ["provide_fields"], trace: [] }
          : { intent: "data_query", status: "succeeded", iteration: 0, final_answer: "共有 3 位用户。", answer_source: "deterministic_fallback", result: { columns: ["用户数"], rows: [[3]], row_count: 1, truncated: false }, generated_sql: "SELECT COUNT(*) AS 用户数 FROM users", trace: [] };
      conversation.title = question;
      conversation.messages.push(
        { id: `${question}-user`, turn_id: `${question}-turn`, role: "user", content: question, status: "succeeded", progress: [], created_at: "2026-01-01T00:00:00Z" },
        { id: `${question}-assistant`, turn_id: `${question}-turn`, role: "assistant", content: response.final_answer, status: response.status, response, progress: [{ request_id: "e2e-request", phase: "progress", node: "intent_gate", status: "running", message: "正在理解问题" }], created_at: "2026-01-01T00:00:01Z" },
      );
      return route.fulfill({ status: 200, contentType: "text/event-stream", body: sse(response) });
    }
    return json({ detail: `Unhandled e2e request: ${request.method()} ${path}` }, 500);
  });

  await page.goto("/login");
  await page.getByLabel("用户名").fill("admin");
  await page.getByLabel("密码").fill("123456");
  await page.getByRole("button", { name: "登录工作区" }).click();
  await expect(page).toHaveURL(/\/agent$/);

  const question = page.getByLabel("输入查询问题");
  await question.fill("你好");
  await page.getByRole("button", { name: "发送查询" }).click();
  await expect(page.getByText("你好，我可以协助分析数据。")).toBeVisible();

  await question.fill("帮我看看数据");
  await page.getByRole("button", { name: "发送查询" }).click();
  await expect(page.getByText("需要澄清")).toBeVisible();
  await expect(page.getByLabel("选择数据库后重新提交")).toBeVisible();
  await page.locator("#clarification-database").selectOption("demo");

  await question.fill("查询用户数量");
  await page.getByRole("button", { name: "发送查询" }).click();
  await expect(page.getByText("共有 3 位用户。")).toBeVisible();
  await expect(page.getByText("用户数")).toBeVisible();

  await page.reload();
  await expect(page.getByText("共有 3 位用户。")).toBeVisible();

  await page.getByRole("link", { name: "RAG 资料库" }).click();
  await expect(page.getByText("销售指标口径.md")).toBeVisible();
  await page.getByLabel("访问范围").selectOption("all_authenticated");
  await page.getByRole("button", { name: "保存访问范围" }).click();
  await expect(page.getByLabel("访问范围")).toHaveValue("all_authenticated");
});
