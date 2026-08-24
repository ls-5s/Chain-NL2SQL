import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  fetchMembers: vi.fn(),
  createMember: vi.fn(),
  updateMember: vi.fn(),
  deleteMember: vi.fn(),
  ApiRequestError: class ApiRequestError extends Error {
    status?: number;
  },
}));
const auth = vi.hoisted(() => ({
  authState: { role: "member" as "super_admin" | "member" },
}));

vi.mock("@/api/client", () => api);
vi.mock("@/auth/auth", () => auth);

import MembersView from "@/views/MembersView.vue";

describe("MembersView permissions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.authState.role = "member";
    api.fetchMembers.mockResolvedValue([
      {
        id: "member-1",
        username: "alice",
        role: "member",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "admin-1",
        username: "admin",
        role: "super_admin",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ]);
  });

  it("shows the member list while disabling management controls", async () => {
    const wrapper = mount(MembersView);
    await flushPromises();

    expect(wrapper.text()).toContain("alice");
    expect(wrapper.text()).toContain("只读权限");
    expect(wrapper.get(".primary-button").attributes("disabled")).toBeDefined();
    expect(wrapper.findAll(".member-card__actions")).toHaveLength(2);
    expect(
      wrapper
        .findAll(".member-card__actions button")
        .every((button) => button.attributes("disabled") !== undefined),
    ).toBe(true);
  });
});
