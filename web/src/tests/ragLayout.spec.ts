import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import RagLayout from "@/layouts/RagLayout.vue";
import type { KnowledgeDocument } from "@/types/api";

const documents: KnowledgeDocument[] = [
  {
    id: "indexed-doc",
    filename: "指标口径.md",
    file_type: "MD",
    size_bytes: 12,
    category: "业务规则",
    status: "indexed",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    chunk_count: 1,
    summary: "销售额口径",
    failure_message: undefined,
    acl: { policy_type: "deny", role: null, user_id: null },
  },
  {
    id: "failed-doc",
    filename: "维度说明.txt",
    file_type: "TXT",
    size_bytes: 20,
    category: "数据字典",
    status: "failed",
    created_at: "2026-01-02T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    chunk_count: 0,
    summary: "字段说明",
    failure_message: "解析失败",
    acl: { policy_type: "deny", role: null, user_id: null },
  },
];

describe("RagLayout", () => {
  it("renders document statistics and emits filter updates", async () => {
    const wrapper = mount(RagLayout, {
      props: {
        documents,
        loading: false,
        refreshing: false,
        isAdmin: true,
        query: "",
        categoryFilter: "all",
      },
    });

    expect(wrapper.text()).toContain("2 份资料");
    expect(wrapper.find(".rag-sidebar__stats").text()).toContain("1");
    expect((wrapper.get('[aria-label="搜索资料"]').element as HTMLInputElement).value).toBe("");
    await wrapper.get('[aria-label="搜索资料"]').setValue("指标");
    await wrapper.get('[aria-label="按分类筛选"]').trigger("click");
    expect(wrapper.findAll('[role="option"]')).toHaveLength(3);
    const dataDictionaryOption = wrapper
      .findAll('[role="option"]')
      .find((option) => option.text() === "数据字典");
    expect(dataDictionaryOption).toBeDefined();
    await dataDictionaryOption?.trigger("click");

    expect(wrapper.emitted("update:query")).toEqual([["指标"]]);
    expect(wrapper.emitted("update:categoryFilter")).toEqual([["数据字典"]]);
  });

  it("shows admin upload action and emits upload and refresh events", async () => {
    const wrapper = mount(RagLayout, {
      props: {
        documents,
        loading: false,
        refreshing: false,
        isAdmin: true,
        query: "",
        categoryFilter: "all",
      },
    });

    await wrapper.get(".primary-button").trigger("click");
    await wrapper.get('[aria-label="刷新列表"]').trigger("click");

    expect(wrapper.emitted("upload")).toHaveLength(1);
    expect(wrapper.emitted("refresh")).toHaveLength(1);
  });

  it("shows but disables upload for members and disables refresh while loading", () => {
    const wrapper = mount(RagLayout, {
      props: {
        documents,
        loading: true,
        refreshing: false,
        isAdmin: false,
        query: "",
        categoryFilter: "all",
      },
    });

    expect(wrapper.get(".primary-button").attributes("disabled")).toBeDefined();
    expect(wrapper.get('[aria-label="刷新列表"]').attributes("disabled")).toBeDefined();
  });
});
