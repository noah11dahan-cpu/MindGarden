import { CONFIG } from "../config";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`API Error ${status}`);
    this.status = status;
    this.body = body;
  }
}

export function getToken(): string | null {
  return localStorage.getItem("mg_token");
}
export function setToken(token: string) {
  localStorage.setItem("mg_token", token);
}
export function clearToken() {
  localStorage.removeItem("mg_token");
}

async function parseJsonSafe(resp: Response): Promise<unknown> {
  const text = await resp.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const base = CONFIG.apiBase;
  if (!base) throw new Error("Missing VITE_API_BASE in frontend/.env");

  const url = `${base}${path}`;
  const token = getToken();

  const headers = new Headers(init.headers || {});
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const resp = await fetch(url, { ...init, headers });

  if (!resp.ok) {
    const body = await parseJsonSafe(resp);
    throw new ApiError(resp.status, body);
  }

  return (await parseJsonSafe(resp)) as T;
}

export async function healthz(): Promise<unknown> {
  return apiFetch("/healthz");
}

export async function login(email: string, password: string): Promise<string> {
  const data = await apiFetch<any>(CONFIG.auth.loginPath, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  const token = data?.[CONFIG.auth.tokenField];
  if (typeof token !== "string") {
    throw new Error(`Login succeeded but "${CONFIG.auth.tokenField}" missing in response`);
  }

  setToken(token);
  return token;
}
export async function signup(email: string, password: string): Promise<void> {
  await apiFetch("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}
export type AiSuggestion = {
  suggestion: string;
  tone: "gentle" | "neutral" | "pushy";
  context?: any;
};

export async function getAiSuggestion(): Promise<AiSuggestion> {
  return apiFetch<AiSuggestion>("/ai/suggestions", { method: "GET" });
}
