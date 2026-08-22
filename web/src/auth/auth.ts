import { fetchSession, loginSession, logoutSession } from "@/api/client";
import type { LoginCredentials } from "@/auth/types";
import type { UserRole } from "@/types/api";

let authenticated = false;
let username = "admin";
let role: UserRole = "member";

export function getDemoUsername(): string {
  return username;
}

export function getDemoRole(): UserRole {
  return role;
}

export async function isAuthenticated(): Promise<boolean> {
  try {
    const session = await fetchSession();
    authenticated = session.authenticated;
    username = session.username || username;
    role = session.role || "member";
  } catch {
    authenticated = false;
    role = "member";
  }
  return authenticated;
}

export async function login(credentials: LoginCredentials): Promise<boolean> {
  try {
    const session = await loginSession(credentials);
    authenticated = session.authenticated;
    username = session.username || username;
    role = session.role || "member";
    return authenticated;
  } catch {
    authenticated = false;
    role = "member";
    return false;
  }
}

export async function logout(): Promise<void> {
  try {
    await logoutSession();
  } finally {
    authenticated = false;
    role = "member";
  }
}
