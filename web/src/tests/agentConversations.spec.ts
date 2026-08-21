import { beforeEach, describe, expect, it } from "vitest";

import {
  AGENT_CONVERSATIONS_STORAGE_KEY,
  createAgentConversationStore,
} from "@/composables/agentConversations";

describe("agent conversations", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("creates and persists one empty conversation on first use", () => {
    const store = createAgentConversationStore();

    expect(store.conversations.value).toHaveLength(1);
    expect(store.activeConversation.value.title).toBe("新聊天");
    expect(localStorage.getItem(AGENT_CONVERSATIONS_STORAGE_KEY)).toContain('"version":1');
  });

  it("uses the first question as the conversation title and persists messages and drafts", () => {
    const store = createAgentConversationStore();
    const question = "请统计最近一个月已完成订单的销售额，并按地区排序";

    store.appendMessage({ id: "user-1", role: "user", content: question });
    store.appendMessage({ id: "assistant-1", role: "assistant", content: "查询完成" });
    store.setDraft("继续按商品分类分析");
    store.setDatabaseId("analytics");

    const restored = createAgentConversationStore();
    expect(restored.activeConversation.value.title).toBe(question.slice(0, 24));
    expect(restored.activeConversation.value.messages).toHaveLength(2);
    expect(restored.activeConversation.value.draft).toBe("继续按商品分类分析");
    expect(restored.activeConversation.value.databaseId).toBe("analytics");
  });

  it("creates, switches and sorts conversations by last update", () => {
    const store = createAgentConversationStore();
    const firstId = store.activeConversationId.value;

    store.appendMessage({ id: "user-1", role: "user", content: "第一个会话" });
    store.createConversation();
    const secondId = store.activeConversationId.value;
    store.appendMessage({ id: "user-2", role: "user", content: "第二个会话" });
    store.selectConversation(firstId);
    store.setDraft("更新第一个会话");

    expect(store.activeConversationId.value).toBe(firstId);
    expect(store.recentConversations.value[0].id).toBe(firstId);
    store.selectConversation(secondId);
    expect(store.activeConversation.value.messages[0].content).toBe("第二个会话");
  });

  it("deletes the active conversation and selects the remaining conversation", () => {
    const store = createAgentConversationStore();
    const firstId = store.activeConversationId.value;
    store.appendMessage({ id: "user-1", role: "user", content: "保留的会话" });
    store.createConversation();
    const secondId = store.activeConversationId.value;

    store.deleteConversation(secondId);

    expect(store.conversations.value).toHaveLength(1);
    expect(store.activeConversationId.value).toBe(firstId);
  });

  it("ignores malformed persisted data and starts with an empty conversation", () => {
    localStorage.setItem(AGENT_CONVERSATIONS_STORAGE_KEY, "not-json");

    const store = createAgentConversationStore();

    expect(store.conversations.value).toHaveLength(1);
    expect(store.activeConversation.value.messages).toEqual([]);
  });
});
