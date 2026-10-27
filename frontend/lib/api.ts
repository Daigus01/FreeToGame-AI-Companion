// Typed client for the backend. STATUS: skeleton, untested (P1-06).
// TODO(P1-04): replace DEV_USER_ID header with real auth (cookie/JWT).
import type { ChatEvent, DailyRecommendations, Game, GameDetail, InteractionType, Platform, SortBy } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DEV_USER_ID = process.env.NEXT_PUBLIC_DEV_USER_ID ?? "00000000-0000-0000-0000-000000000001";

function headers(): HeadersInit {
  return { "Content-Type": "application/json", "X-User-Id": DEV_USER_ID };
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export async function fetchGames(p: { category?: string; platform?: Platform; sort_by?: SortBy }): Promise<Game[]> {
  const q = new URLSearchParams();
  if (p.category) q.set("category", p.category);
  if (p.platform) q.set("platform", p.platform);
  if (p.sort_by) q.set("sort_by", p.sort_by);
  return json(await fetch(`${API_URL}/api/games?${q}`, { headers: headers() }));
}

export async function fetchGame(id: number): Promise<GameDetail> {
  return json(await fetch(`${API_URL}/api/games/${id}`, { headers: headers() }));
}

export async function fetchDailyTop5(): Promise<DailyRecommendations> {
  return json(await fetch(`${API_URL}/api/recommendations/today`, { headers: headers() }));
}

export async function track(game_id: number, interaction_type: InteractionType): Promise<void> {
  // fire-and-forget; failures must never break the UI
  fetch(`${API_URL}/api/interactions`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ game_id, interaction_type }),
  }).catch(() => {});
}

/** Streams POST /api/chat (SSE over fetch, since EventSource cannot POST). */
export async function* streamChat(message: string, sessionId?: string): AsyncGenerator<ChatEvent> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok || !res.body) throw new Error(`chat failed: ${res.status}`);
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
