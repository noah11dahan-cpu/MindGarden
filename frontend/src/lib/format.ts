import { ApiError } from "./api";

export function formatErr(e: any): string {
  if (e instanceof ApiError) return `HTTP ${e.status}: ${JSON.stringify(e.body)}`;
  return String(e?.message || e);
}
