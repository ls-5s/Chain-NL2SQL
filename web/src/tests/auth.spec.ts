import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ fetchSession: vi.fn(), loginSession: vi.fn(), logoutSession: vi.fn() }));
vi.mock("@/api/client", () => api);

import { getDemoUsername, isAuthenticated, login, logout } from "@/auth/auth";

describe("server session authentication", () => {
  beforeEach(() => vi.resetAllMocks());

  it("uses the server session instead of browser storage", async () => {
    api.fetchSession.mockResolvedValue({ authenticated: true, username: "admin" });
    await expect(isAuthenticated()).resolves.toBe(true);
    expect(getDemoUsername()).toBe("admin");
  });

  it("logs in and logs out through the API", async () => {
    api.loginSession.mockResolvedValue({ authenticated: true, username: "admin" });
    await expect(login({ username: "admin", password: "123456" })).resolves.toBe(true);
    await logout();
    expect(api.logoutSession).toHaveBeenCalledOnce();
  });
});
