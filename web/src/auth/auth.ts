import { fetchSession, loginSession, logoutSession } from "@/api/client";
import type { LoginCredentials } from "@/auth/types";

let authenticated = false;
let username = "admin";

export function getDemoUsername(): string {
  return username;
}

export async function isAuthenticated(): Promise<boolean> {
  try {
    const session = await fetchSession();
    authenticated = session.authenticated;
    username = session.username || username;
  } catch {
    authenticated = false;
  }
  return authenticated;
}

export async function login(credentials: LoginCredentials): Promise<boolean> {
  try {
    const session = await loginSession(credentials);
    authenticated = session.authenticated;
    username = session.username || username;
    return authenticated;
  } catch {
    authenticated = false;
    return false;
  }
}

export async function logout(): Promise<void> {
  try {
    await logoutSession();
  } finally {
    authenticated = false;
  }
}
