// Mirrors backend/app/schemas.py. Keep in sync by hand (TODO P1-06: consider generating from /openapi.json).

export type Platform = "pc" | "browser" | "all";
export type SortBy = "release-date" | "popularity" | "alphabetical" | "relevance";
export type InteractionType = "view" | "click" | "saved" | "played" | "disliked";

export interface Game {
  id: number;
  title: string;
  thumbnail?: string | null;
  short_description?: string | null;
  game_url?: string | null;
  genre?: string | null;
  platform?: string | null;
  publisher?: string | null;
  developer?: string | null;
  release_date?: string | null;
  freetogame_profile_url?: string | null;
}

export interface GameDetail extends Game {
  status?: string | null;
  description?: string | null;
  minimum_system_requirements?: Record<string, string> | null;
  screenshots: { id: number; image: string }[];
}

export interface ChatSessionInfo { id: string; title: string; updated_at: string }
export interface ChatMessageView { role: "user" | "assistant"; text: string; games: Game[] }

export type AuthProvider = "google" | "discord";
export interface Me { id: string; email: string; name: string | null; avatar_url: string | null }
export interface AuthProviders { providers: AuthProvider[]; dev_auth: boolean }

export interface DailyRecommendations {
  date: string;
  source: "ml" | "fallback_popular";
  games: Game[];
}

// SSE events emitted by POST /api/chat (contract documented in docs/HANDOFF.md section 6)
export type ChatEvent =
  | { type: "session"; session_id: string }
  | { type: "token"; text: string }
  | { type: "tool_call"; name: string }
  | { type: "games"; games: Game[] }
  | { type: "error"; message: string }
  | { type: "done" };
