import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DatabaseLayout from "@/layouts/DatabaseLayout.vue";
import type { Database } from "@/types/api";

const databases: Database[] = [
  {
    id: "main",
    name: "主数据",
    dialect: "sqlite",
    enabled: true,
    config: {},
    tables: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "analytics",
    name: "分析库",
    dialect: "mysql",
    enabled: false,
    config: {},
    tables: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

describe("DatabaseLayout", () => {
  it("filters databases by search text and emits selection", async () => {
    const wrapper = mount(DatabaseLayout, {
      props: { databases, selectedDatabaseId: "main", loading: false, isAdmin: true },
    });

    await wrapper.get('[aria-label="搜索数据库"]').setValue("分析");
    expect(wrapper.findAll(".database-nav-item")).toHaveLength(1);
    expect(wrapper.text()).toContain("分析库");
    expect(wrapper.text()).not.toContain("主数据");

    await wrapper.get(".database-nav-item").trigger("click");
    expect(wrapper.emitted("select")).toEqual([["analytics"]]);
  });

  it("filters by enabled status and shows the admin action", async () => {
    const wrapper = mount(DatabaseLayout, {
      props: { databases, selectedDatabaseId: "main", loading: false, isAdmin: true },
    });

    await wrapper.get(".status-filter button:nth-of-type(2)").trigger("click");
    expect(wrapper.findAll(".database-nav-item")).toHaveLength(1);
    expect(wrapper.text()).toContain("主数据");
    expect(wrapper.find(".sidebar-add-button").element).toBeTruthy();
  });

  it("covers loading, empty, and non-admin states", async () => {
    const loading = mount(DatabaseLayout, {
      props: { databases, selectedDatabaseId: "main", loading: true, isAdmin: false },
    });
    expect(loading.text()).toContain("正在加载数据源");
    expect(loading.get(".sidebar-refresh-button").attributes("disabled")).toBeDefined();
    expect(loading.get(".sidebar-add-button").attributes("disabled")).toBeDefined();

    const empty = mount(DatabaseLayout, {
      props: { databases: [], selectedDatabaseId: "", loading: false, isAdmin: true },
    });
    expect(empty.text()).toContain("暂无数据库");
  });
});
