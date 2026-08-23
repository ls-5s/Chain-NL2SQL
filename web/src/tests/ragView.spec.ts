import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchKnowledgeDocuments: vi.fn(),
  uploadKnowledgeDocument: vi.fn(),
  deleteKnowledgeDocument: vi.fn(),
  updateKnowledgeACL: vi.fn(),
  ApiRequestError: class ApiRequestError extends Error {
    status?: number;
  },
}));
const auth = vi.hoisted(() => ({ getDemoRole: vi.fn() }));

vi.mock("@/api/client", () => api);
vi.mock("@/auth/auth", () => auth);

import RagView from "@/views/RagView.vue";

const indexed = {
  id: "doc-1",
  filename: "指标口径.md",
  file_type: "MD" as const,
  size_bytes: 12,
  category: "业务规则",
  status: "indexed" as const,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  chunk_count: 1,
  summary: "销售额口径",
  failure_message: null,
  acl: { policy_type: "deny" as const, role: null, user_id: null },
};

describe("RagView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    auth.getDemoRole.mockReturnValue("super_admin");
    api.fetchKnowledgeDocuments.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("loads an empty state and hides write controls for members", async () => {
    auth.getDemoRole.mockReturnValue("member");
    const wrapper = mount(RagView);
    await flushPromises();

    expect(wrapper.text()).toContain("暂无资料");
    expect(wrapper.find(".document-list").exists()).toBe(false);
    expect(wrapper.find("button.primary-button").exists()).toBe(false);
  });

  it("uploads a document and polls until indexing completes", async () => {
    const uploading = { ...indexed, status: "uploading" as const, summary: "", chunk_count: 0 };
    api.uploadKnowledgeDocument.mockResolvedValue(uploading);
    api.fetchKnowledgeDocuments.mockResolvedValueOnce([]).mockResolvedValueOnce([indexed]);
    const wrapper = mount(RagView);
    await flushPromises();

    await wrapper.get("button.primary-button").trigger("click");
    const file = new File(["销售额口径"], "sales.md", { type: "text/markdown" });
    const input = wrapper.get('input[type="file"]');
    Object.defineProperty(input.element, "files", { configurable: true, value: [file] });
    await input.trigger("change");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(api.uploadKnowledgeDocument).toHaveBeenCalledWith(file, "业务规则");
    expect(wrapper.text()).toContain("上传中");

    await vi.advanceTimersByTimeAsync(2000);
    await flushPromises();
    expect(api.fetchKnowledgeDocuments).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("已索引");
  });

  it("lets an administrator save a document ACL", async () => {
    const updated = {
      ...indexed,
      acl: { policy_type: "all_authenticated" as const, role: null, user_id: null },
    };
    api.fetchKnowledgeDocuments.mockResolvedValue([indexed]);
    api.updateKnowledgeACL.mockResolvedValue(updated);
    const wrapper = mount(RagView);
    await flushPromises();

    await wrapper.get('[id="acl-policy-doc-1"]').setValue("all_authenticated");
    await wrapper.get('[aria-label="保存访问范围"]').trigger("click");
    await flushPromises();

    expect(api.updateKnowledgeACL).toHaveBeenCalledWith("doc-1", {
      policy_type: "all_authenticated",
    });
  });
});
