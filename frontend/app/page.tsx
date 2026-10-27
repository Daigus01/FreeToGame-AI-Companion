// Home: Top 5 widget + catalog (grid + filters) + chat. STATUS: done (skeleton level).
// TODO(P1-07): pagination/virtualisation, loading skeletons, error + degraded-mode banner (RNF-3).
"use client";
import { useEffect, useState } from "react";
import { fetchGames } from "@/lib/api";
import type { Game } from "@/lib/types";
import ChatWidget from "@/components/ChatWidget";
import Filters, { type FilterState } from "@/components/Filters";
import GameCard from "@/components/GameCard";
import GameModal from "@/components/GameModal";
import Top5Widget from "@/components/Top5Widget";

export default function Home() {
  const [filters, setFilters] = useState<FilterState>({ platform: "all", sort_by: "popularity" });
  const [games, setGames] = useState<Game[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => {
    setError(null);
    fetchGames(filters).then(setGames).catch((e) => setError(String(e)));
  }, [filters]);

  return (
    <main className="max-w-7xl mx-auto p-4 grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">FreeToGame AI Companion</h1>
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
