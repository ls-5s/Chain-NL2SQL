import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchConversations: vi.fn(),
  fetchConversation: vi.fn(),
  createConversation: vi.fn(),
  deleteConversation: vi.fn(),
  streamConversationQuery: vi.fn(),
}));

vi.mock("@/api/client", () => api);

import { createAgentConversationStore } from "@/composables/agentConversations";

const summary = { id: "c1", title: "新聊天", database_id: "demo", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", message_count: 0 };

function detail(messages: object[] = []) {
  return { ...summary, messages };
}

describe("agent conversations", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.fetchConversations.mockResolvedValue([summary]);
    api.fetchConversation.mockResolvedValue(detail());
    api.createConversation.mockResolvedValue(summary);
    api.streamConversationQuery.mockImplementation(async (_id: string, _payload: object, progress: (event: object) => void) => {
      progress({ node: "intent_gate", message: "正在理解问题" });
      return { request_id: "r1", intent: "general_chat", status: "succeeded", iteration: 0, final_answer: "完成", trace: [] };
    });
  });

  it("loads the active conversation from the server", async () => {
    const store = createAgentConversationStore();
    await store.initialize();
    expect(store.activeConversationId.value).toBe("c1");
    expect(api.fetchConversations).toHaveBeenCalledOnce();
    expect(api.fetchConversation).toHaveBeenCalledWith("c1");
  });

  it("creates a server conversation and selects it", async () => {
    api.createConversation.mockResolvedValue({ ...summary, id: "c2", title: "新聊天" });
    api.fetchConversations.mockResolvedValue([{ ...summary, id: "c2" }, summary]);
    const store = createAgentConversationStore();
    await store.initialize();
    await store.createConversation("demo");
    expect(api.createConversation).toHaveBeenCalledWith("demo");
    expect(store.activeConversationId.value).toBe("c2");
  });

  it("streams a turn and refreshes the durable server history", async () => {
    const store = createAgentConversationStore();
    await store.initialize();
    await store.sendQuestion("查询用户数量", vi.fn());
    expect(api.streamConversationQuery).toHaveBeenCalledWith(
      "c1",
      { question: "查询用户数量", reference_ids: [] },
      expect.any(Function),
    );
    expect(api.fetchConversation).toHaveBeenCalledTimes(2);
  });

  it("sends selected result references with the next turn only", async () => {
    const store = createAgentConversationStore();
    await store.initialize();

    await store.sendQuestion("查看这条记录", vi.fn(), ["ref-1"]);

    expect(api.streamConversationQuery).toHaveBeenCalledWith(
      "c1",
      { question: "查看这条记录", reference_ids: ["ref-1"] },
      expect.any(Function),
    );
  });
});
