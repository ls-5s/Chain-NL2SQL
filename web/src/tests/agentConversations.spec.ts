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

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
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

  it("keeps the first turn on the empty state until durable history is refreshed", async () => {
    const completed = deferred<object>();
    const persistedMessages = [
      { id: "m1", turn_id: "t1", role: "user", content: "查询用户数量", status: "succeeded", progress: [], created_at: "2026-01-01T00:00:00Z" },
      { id: "m2", turn_id: "t1", role: "assistant", content: "共有 3 位用户", status: "succeeded", progress: [], created_at: "2026-01-01T00:00:01Z" },
    ];
    api.fetchConversation.mockResolvedValueOnce(detail()).mockResolvedValueOnce(detail(persistedMessages));
    api.streamConversationQuery.mockImplementation(async (_id: string, _payload: object, progress: (event: object) => void) => {
      progress({ node: "intent_gate", message: "正在理解问题" });
      return completed.promise;
    });
    const store = createAgentConversationStore();
    await store.initialize();

    const send = store.sendQuestion("查询用户数量", vi.fn());

    expect(store.isBusy.value).toBe(true);
    expect(store.activeConversation.value.messages).toEqual([]);
    expect(api.fetchConversation).toHaveBeenCalledTimes(1);

    completed.resolve({ request_id: "r1" });
    await send;

    expect(api.fetchConversation).toHaveBeenCalledTimes(2);
    expect(store.activeConversation.value.messages).toEqual(persistedMessages);
  });

  it("keeps optimistic messages and stream progress for later turns", async () => {
    const completed = deferred<object>();
    const history = [
      { id: "m1", turn_id: "t1", role: "user", content: "上一轮问题", status: "succeeded", progress: [], created_at: "2026-01-01T00:00:00Z" },
      { id: "m2", turn_id: "t1", role: "assistant", content: "上一轮回答", status: "succeeded", progress: [], created_at: "2026-01-01T00:00:01Z" },
    ];
    api.fetchConversation.mockResolvedValue(detail(history));
    api.streamConversationQuery.mockImplementation(async (_id: string, _payload: object, progress: (event: object) => void) => {
      progress({ node: "generation", message: "正在生成 SQL" });
      return completed.promise;
    });
    const store = createAgentConversationStore();
    await store.initialize();

    const send = store.sendQuestion("继续查询", vi.fn());

    const messages = store.activeConversation.value.messages;
    expect(messages).toHaveLength(4);
    expect(messages.at(-1)).toMatchObject({ role: "assistant", content: "正在生成 SQL", status: "running" });
    expect(messages.at(-1)?.progress).toEqual([{ node: "generation", message: "正在生成 SQL" }]);

    completed.resolve({ request_id: "r2" });
    await send;
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
