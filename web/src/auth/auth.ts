import type { LoginCredentials } from "@/auth/types";

export const AUTH_STORAGE_KEY = "chain-nl2sql-authenticated";

const demoUsername = (import.meta.env.VITE_DEMO_USERNAME || "admin").trim();
const demoPassword = import.meta.env.VITE_DEMO_PASSWORD || "";

export function getDemoUsername(): string {
  return demoUsername;
}

export function isAuthenticated(): boolean {
  return window.localStorage.getItem(AUTH_STORAGE_KEY) === "true";
}

export function login(credentials: LoginCredentials): boolean {
  const valid = credentials.username.trim() === demoUsername && credentials.password === demoPassword;
  if (valid) window.localStorage.setItem(AUTH_STORAGE_KEY, "true");
  return valid;
}

export function logout(): void {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}
