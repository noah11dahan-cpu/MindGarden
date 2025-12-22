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
  // NEW: clear cached tier too
  localStorage.removeItem("mg_tier");
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

/** Day 8 (RAG): Retrieved reflection shape returned in ctx["retrieved_reflections"] */
export type RetrievedReflection = {
  score: number;
  checkin_date: string;
  text: string;
  reflection_id: number;
};

export type AiSuggestion = {
  suggestion: string;
  tone: "gentle" | "neutral" | "pushy";
  context?: {
    retrieved_reflections?: RetrievedReflection[];
    [key: string]: any;
  };
};

export async function getAiSuggestion(): Promise<AiSuggestion> {
  return apiFetch<AiSuggestion>("/ai/suggestions", { method: "GET" });
}

// --------------------
// NEW (Day 11 Premium)
// --------------------

export type SubscriptionTier = "free" | "premium";

export function getTier(): SubscriptionTier {
  const t = localStorage.getItem("mg_tier");
  return t === "premium" ? "premium" : "free";
}
export function setTier(tier: SubscriptionTier) {
  localStorage.setItem("mg_tier", tier);
}

export async function upgrade(): Promise<{ subscription_tier: SubscriptionTier }> {
  const data = await apiFetch<{ subscription_tier: SubscriptionTier }>("/upgrade", { method: "POST" });
  if (data?.subscription_tier === "premium" || data?.subscription_tier === "free") {
    setTier(data.subscription_tier);
  }
  return data;
}

export async function deepDive(topic: string): Promise<{ topic: string; response: string }> {
  return apiFetch<{ topic: string; response: string }>("/ai/deep_dive", {
    method: "POST",
    body: JSON.stringify({ topic }),
  });
}

export type ExportReflectionsResponse = {
  count: number;
  reflections: Array<{ date: string; mood: number | null; note: string | null }>;
};

export async function exportReflections(): Promise<ExportReflectionsResponse> {
  return apiFetch<ExportReflectionsResponse>("/export/reflections", { method: "GET" });
}

export type MetricsAnalyticsResponse = {
  date_utc: string;
  window_days: number;
  window_start_utc: string;
  checkins_window: number;
  ai_suggestions_count_window: number;
  ai_suggestions_latency_ms_avg_window: number | null;
  ai_suggestions_latency_ms_p95_window: number | null;
  subscription_tier: SubscriptionTier | string;
};

export async function metricsAnalytics(days: number): Promise<MetricsAnalyticsResponse> {
  const data = await apiFetch<MetricsAnalyticsResponse>(`/metrics/analytics?days=${days}`, { method: "GET" });
  // cache tier for UI
  const t = data?.subscription_tier === "premium" ? "premium" : "free";
  setTier(t);
  return data;
}
