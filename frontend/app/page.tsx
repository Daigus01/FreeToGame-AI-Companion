// Home: Top 5 widget + catalog (grid + filters) + chat. STATUS: done (skeleton level).
// TODO(P1-07): pagination/virtualisation, loading skeletons, error + degraded-mode banner (RNF-3).
"use client";
import { useEffect, useState } from "react";
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
        <Filters value={filters} onChange={setFilters} />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {games.slice(0, 60).map((g) => <GameCard key={g.id} game={g} onOpen={setOpen} />)}
        </div>
      </div>
      <ChatWidget onOpen={setOpen} />
      {open !== null && <GameModal gameId={open} onClose={() => setOpen(null)} />}
    </main>
  );
}
