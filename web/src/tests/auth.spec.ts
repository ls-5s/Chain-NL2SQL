import { beforeEach, describe, expect, it } from "vitest";

import { AUTH_STORAGE_KEY, isAuthenticated, login, logout } from "@/auth/auth";
import { router } from "@/router";

describe("demo authentication", () => {
  beforeEach(async () => {
    localStorage.clear();
    await router.push("/login");
  });

  it("accepts configured demo credentials and persists the session", () => {
    const password = import.meta.env.VITE_DEMO_PASSWORD || "";
    expect(login({ username: import.meta.env.VITE_DEMO_USERNAME || "admin", password })).toBe(true);
    expect(localStorage.getItem(AUTH_STORAGE_KEY)).toBe("true");
    expect(isAuthenticated()).toBe(true);
  });

  it("rejects invalid credentials", () => {
    expect(login({ username: "wrong-user", password: "wrong-password" })).toBe(false);
    expect(isAuthenticated()).toBe(false);
  });

  it("guards protected routes and restores the requested route after login", async () => {
    await router.push("/agent");
    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe("/agent");

    const password = import.meta.env.VITE_DEMO_PASSWORD || "";
    expect(login({ username: import.meta.env.VITE_DEMO_USERNAME || "admin", password })).toBe(true);
    // Use a changed query to trigger a new navigation after the initial guard redirect.
    await router.push({ name: "login", query: { redirect: "/agent", retry: "1" } });
    expect(router.currentRoute.value.name).toBe("agent");
  });

  it("clears the session on logout and protects business routes again", async () => {
    localStorage.setItem(AUTH_STORAGE_KEY, "true");
    expect(isAuthenticated()).toBe(true);
    logout();
    expect(isAuthenticated()).toBe(false);
    await router.push("/agent");
    expect(router.currentRoute.value.name).toBe("login");
  });
});
