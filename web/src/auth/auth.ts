import { fetchSession, loginSession, logoutSession } from "@/api/client";
import type { LoginCredentials } from "@/auth/types";
import type { UserRole } from "@/types/api";
import { reactive } from "vue";

export const authState = reactive({
  authenticated: false,
  username: "admin",
  role: "member" as UserRole,
});

export function getDemoUsername(): string {
  return authState.username;
}

export function getDemoRole(): UserRole {
  return authState.role;
}

export async function isAuthenticated(): Promise<boolean> {
  try {
    const session = await fetchSession();
    authState.authenticated = session.authenticated;
    authState.username = session.username || authState.username;
    authState.role = session.role || "member";
  } catch {
    authState.authenticated = false;
    authState.role = "member";
  }
  return authState.authenticated;
}

export async function login(credentials: LoginCredentials): Promise<boolean> {
  try {
    const session = await loginSession(credentials);
    authState.authenticated = session.authenticated;
    authState.username = session.username || authState.username;
    authState.role = session.role || "member";
    return authState.authenticated;
  } catch {
    authState.authenticated = false;
    authState.role = "member";
    return false;
  }
}

export async function logout(): Promise<void> {
  try {
    await logoutSession();
  } finally {
    authState.authenticated = false;
    authState.role = "member";
  }
}
