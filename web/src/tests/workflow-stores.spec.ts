import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useApprovalStore } from "@/stores/approval";
import { useKnowledgeStore } from "@/stores/knowledge";
import { useQueryStore } from "@/stores/query";

describe("mock workflow stores", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("returns a query response with trace and knowledge hits", async () => {
    const store = useQueryStore();
    store.question = "查询商品销售额";
    await store.runQuery();
    expect(store.response?.status).toBe("succeeded");
    expect(store.response?.trace.length).toBeGreaterThan(0);
    expect(store.response?.knowledge_hits?.length).toBeGreaterThan(0);
  });

  it("rejects unsupported knowledge-base files", async () => {
    const store = useKnowledgeStore();
    const accepted = await store.upload(new File(["x"], "rule.exe", { type: "application/octet-stream" }), "业务规则");
    expect(accepted).toBe(false);
    expect(store.errorMessage).toContain("仅支持");
  });

  it("records an approval decision", async () => {
    const store = useApprovalStore();
    await store.load();
    const item = store.items.find((candidate) => candidate.status === "pending");
    expect(item).toBeDefined();
    await store.decide(item!.id, "approved");
    expect(store.items.find((candidate) => candidate.id === item!.id)?.status).toBe("approved");
  });
});
