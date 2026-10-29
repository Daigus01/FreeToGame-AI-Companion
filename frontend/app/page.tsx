// Home: Top 5 widget + catalog (grid + filters) + chat. STATUS: done (skeleton level).
// Assistant recommendations replace the catalog grid while active (D-16); "Ver todo el catálogo" or any filter change exits.
// TODO(P1-07): pagination/virtualisation, loading skeletons, error + degraded-mode banner (RNF-3).
"use client";
import { useEffect, useRef, useState } from "react";
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
  // Games recommended by the assistant (D-16): shown IN the catalog grid instead of in the chat. null = normal catalog.
  const [recs, setRecs] = useState<Game[] | null>(null);
  const catalogRef = useRef<HTMLElement>(null);

  function showRecommendations(list: Game[]) {
    setRecs(list);
    // on small screens the chat sits below the catalog: bring the results into view
    requestAnimationFrame(() => catalogRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

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
        {/* Changing a filter means "I want the catalog again": leave recommendation mode */}
        <Filters value={filters} onChange={(f) => { setRecs(null); setFilters(f); }} />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <section ref={catalogRef} className="space-y-3 scroll-mt-4" aria-label="Catálogo">
          {recs && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-indigo-950 ring-1 ring-indigo-400 px-3 py-2" role="status">
              <span className="text-sm">
                <b>Recomendados por el asistente</b> · {recs.length} {recs.length === 1 ? "juego" : "juegos"}
              </span>
              <button className="text-sm bg-slate-700 hover:bg-slate-600 px-3 py-1 rounded" onClick={() => setRecs(null)}>
                Ver todo el catálogo
              </button>
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {(recs ?? games.slice(0, 60)).map((g) => <GameCard key={g.id} game={g} onOpen={setOpen} />)}
          </div>
        </section>
      </div>
      <ChatWidget onRecommend={showRecommendations} />
      {open !== null && <GameModal gameId={open} onClose={() => setOpen(null)} />}
    </main>
  );
}
