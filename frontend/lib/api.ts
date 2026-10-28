// Typed client for the backend. STATUS: catalog/filters/modal verified in browser; auth (D-11) pending real-provider check (P1-11).
// Auth: the browser sends the HttpOnly `ftg_session` cookie (credentials: "include"). NEXT_PUBLIC_DEV_USER_ID is an
// OPTIONAL local-dev fallback that only works if the backend runs with ALLOW_DEV_AUTH=true.
import type { AuthProvider, AuthProviders, ChatEvent, ChatMessageView, ChatSessionInfo, DailyRecommendations, Game, GameDetail, InteractionType, Me, Platform, SortBy } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DEV_USER_ID = process.env.NEXT_PUBLIC_DEV_USER_ID ?? "";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function headers(): HeadersInit {
  return { "Content-Type": "application/json", ...(DEV_USER_ID ? { "X-User-Id": DEV_USER_ID } : {}) };
}

function req(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_URL}${path}`, { ...init, headers: { ...headers(), ...(init.headers ?? {}) }, credentials: "include" });
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new ApiError(res.status, `API ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

// ---- auth (D-11) ----
export const loginUrl = (p: AuthProvider) => `${API_URL}/api/auth/${p}/login`;

export async function fetchProviders(): Promise<AuthProviders> {
  return json(await req("/api/auth/providers"));
}

/** null when not logged in (401); throws on other failures. */
export async function fetchMe(): Promise<Me | null> {
  const res = await req("/api/auth/me");
  if (res.status === 401) return null;
  return json(res);
}

export async function logout(): Promise<void> {
  await req("/api/auth/logout", { method: "POST" });
}

// ---- catalog ----
export async function fetchGames(p: { category?: string; platform?: Platform; sort_by?: SortBy }): Promise<Game[]> {
  const q = new URLSearchParams();
  if (p.category) q.set("category", p.category);
  if (p.platform) q.set("platform", p.platform);
  if (p.sort_by) q.set("sort_by", p.sort_by);
  return json(await req(`/api/games?${q}`));
}

export async function fetchGame(id: number): Promise<GameDetail> {
  return json(await req(`/api/games/${id}`));
}

export async function fetchDailyTop5(): Promise<DailyRecommendations> {
  return json(await req("/api/recommendations/today"));
}

/** Records an interaction. Resolves true if stored; false if not logged in (401) or on any failure. Never throws. */
export async function track(game_id: number, interaction_type: InteractionType): Promise<boolean> {
  try {
    const res = await req("/api/interactions", { method: "POST", body: JSON.stringify({ game_id, interaction_type }) });
    return res.ok;
  } catch {
    return false;
  }
}

// ---- chat history (RF-2.4) ----
export async function fetchChatSessions(): Promise<ChatSessionInfo[]> {
  return json(await req("/api/chat/sessions"));
}
export async function fetchChatMessages(sessionId: string): Promise<ChatMessageView[]> {
  return json(await req(`/api/chat/${sessionId}/messages`));
}

/** Streams POST /api/chat (SSE over fetch, since EventSource cannot POST). Pass `signal` to stop generation. */
export async function* streamChat(message: string, sessionId?: string, signal?: AbortSignal): AsyncGenerator<ChatEvent> {
  const res = await req("/api/chat", { method: "POST", signal, body: JSON.stringify({ message, session_id: sessionId }) });
  if (!res.ok || !res.body) throw new ApiError(res.status, `chat failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const event = /^event: (.+)$/m.exec(block)?.[1];
      const data = /^data: (.+)$/m.exec(block)?.[1];
      if (event && data) yield { type: event, ...JSON.parse(data) } as ChatEvent;
    }
  }
}
