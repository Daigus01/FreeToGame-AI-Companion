// Home: Top 5 widget + catalog (grid + filters) + chat. STATUS: done (skeleton level).
// Chat suggestions (D-16): the games the assistant recommends replace the catalog grid (banner + "Volver al catálogo"),
// instead of being rendered as cards inside the chat. Changing a filter returns to the normal catalog.
// TODO(P1-07): pagination/virtualisation, loading skeletons, error + degraded-mode banner (RNF-3).
"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchGames } from "@/lib/api";
import type { Game } from "@/lib/types";
import AuthButton from "@/components/AuthButton";
import ChatWidget from "@/components/ChatWidget";
import Filters, { type FilterState } from "@/components/Filters";
import GameCard from "@/components/GameCard";
import GameModal from "@/components/GameModal";
import Top5Widget from "@/components/Top5Widget";

const AUTH_ERRORS: Record<string, string> = {
  cancelled: "Cancelaste el inicio de sesión.",
  state: "La sesión de login expiró o no es válida. Inténtalo de nuevo.",
  provider_error: "El proveedor no respondió correctamente. Inténtalo de nuevo.",
  email_unverified: "Tu cuenta no tiene un correo verificado; no podemos usarla para entrar.",
};

export default function Home() {
  const [filters, setFilters] = useState<FilterState>({ platform: "all", sort_by: "popularity" });
  const [games, setGames] = useState<Game[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [suggested, setSuggested] = useState<Game[] | null>(null);
  const catalogRef = useRef<HTMLDivElement>(null);

  const showSuggestions = useCallback((list: Game[]) => {
    setSuggested(list);
    // On narrow screens the chat sits below the catalog: bring the results into view
    catalogRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  useEffect(() => {
    // The backend redirects here with ?auth_error=<code> when a login fails (see api/routes/auth.py)
    const code = new URLSearchParams(window.location.search).get("auth_error");
    if (code) {
      setAuthError(code);
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    setError(null);
    fetchGames(filters).then(setGames).catch((e) => setError(String(e)));
  }, [filters]);

  return (
    <main className="max-w-7xl mx-auto p-4 grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-2xl font-bold">FreeToGame AI Companion</h1>
          <AuthButton />
        </div>
        {authError && (
          <p className="text-amber-300 text-sm" role="alert">
            {AUTH_ERRORS[authError] ?? "No se pudo iniciar sesión."}
          </p>
        )}
        <Top5Widget onOpen={setOpen} />
        <Filters value={filters} onChange={(f) => { setSuggested(null); setFilters(f); }} />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <div ref={catalogRef} className="scroll-mt-4 space-y-3">
          {suggested && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-indigo-950 ring-1 ring-indigo-500 px-3 py-2" role="status">
              <span className="text-sm">
                ✨ Sugeridos por el asistente ({suggested.length})
              </span>
              <button className="text-xs bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded" onClick={() => setSuggested(null)}>
                Volver al catálogo
              </button>
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {(suggested ?? games.slice(0, 60)).map((g) => <GameCard key={g.id} game={g} onOpen={setOpen} />)}
          </div>
        </div>
      </div>
      <ChatWidget onSuggest={showSuggestions} />
      {open !== null && <GameModal gameId={open} onClose={() => setOpen(null)} />}
    </main>
  );
}
