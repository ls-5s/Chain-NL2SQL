import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchDatabaseConfigs: vi.fn(),
  updateDatabaseTableAccess: vi.fn(),
  testDatabase: vi.fn(),
  updateDatabase: vi.fn(),
  createDatabase: vi.fn(),
  deleteDatabase: vi.fn(),
  ApiRequestError: class ApiRequestError extends Error {
    status?: number;
  },
}));
const auth = vi.hoisted(() => ({ getDemoRole: vi.fn() }));

vi.mock("@/api/client", () => api);
vi.mock("@/auth/auth", () => auth);

import DatabasesView from "@/views/DatabasesView.vue";

const database = {
  id: "demo",
  name: "主数据",
  dialect: "sqlite" as const,
  enabled: true,
  config: {},
  tables: [
    { table_name: "orders", agent_access: true, updated_at: "2026-01-01T00:00:00Z" },
    { table_name: "users", agent_access: false, updated_at: "2026-01-01T00:00:00Z" },
    { table_name: "products", agent_access: false, updated_at: "2026-01-01T00:00:00Z" },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("DatabasesView permissions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.getDemoRole.mockReturnValue("super_admin");
    api.fetchDatabaseConfigs.mockResolvedValue([structuredClone(database)]);
    api.updateDatabaseTableAccess.mockImplementation(
      async (databaseId: string, tableName: string, value: boolean) => ({
        table_name: tableName,
        agent_access: value,
        updated_at: "2026-01-01T00:00:00Z",
      }),
    );
  });

  it("filters permission rows and applies all-authorize sequentially", async () => {
    const wrapper = mount(DatabasesView);
    await flushPromises();

    expect(wrapper.findAll(".table-row")).toHaveLength(3);
    await wrapper.get(".table-filter button:nth-child(2)").trigger("click");
    expect(wrapper.findAll(".table-row")).toHaveLength(1);
    expect(wrapper.text()).toContain("orders");

    await wrapper.get(".table-filter button:first-child").trigger("click");
    await wrapper.get(".text-action").trigger("click");
    await flushPromises();

    expect(api.updateDatabaseTableAccess.mock.calls.map((call) => call[1])).toEqual([
      "users",
      "products",
    ]);
    expect(wrapper.text()).toContain("已更新 2 张表");
    expect(wrapper.findAll(".table-row input:checked")).toHaveLength(3);
  });

  it("keeps successful rows and restores failed rows", async () => {
    api.updateDatabaseTableAccess
      .mockResolvedValueOnce({ table_name: "users", agent_access: true, updated_at: "" })
      .mockRejectedValueOnce(new Error("failed"));
    const wrapper = mount(DatabasesView);
    await flushPromises();

    await wrapper.get(".text-action").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("已更新 1 张表，1 张表失败");
    expect(wrapper.text()).toContain("部分表权限更新失败");
    const rows = wrapper.findAll(".table-row");
    expect(rows[1].get("input").element.checked).toBe(true);
    expect(rows[2].get("input").element.checked).toBe(false);
  });

  it("disables permission controls for members", async () => {
    auth.getDemoRole.mockReturnValue("member");
    const wrapper = mount(DatabasesView);
    await flushPromises();

    expect(
      wrapper
        .findAll(".table-filter button")
        .every((button) => button.attributes("disabled") === undefined),
    ).toBe(true);
    expect(
      wrapper
        .findAll(".table-row input")
        .every((input) => input.attributes("disabled") !== undefined),
    ).toBe(true);
    expect(
      wrapper
        .findAll(".text-action")
        .every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
  });

  it("disables permission writes when the database is not enabled", async () => {
    api.fetchDatabaseConfigs.mockResolvedValue([{ ...structuredClone(database), enabled: false }]);
    const wrapper = mount(DatabasesView);
    await flushPromises();

    expect(
      wrapper
        .findAll(".table-row input")
        .every((input) => input.attributes("disabled") !== undefined),
    ).toBe(true);
    expect(
      wrapper
        .findAll(".text-action")
        .every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
  });
});
