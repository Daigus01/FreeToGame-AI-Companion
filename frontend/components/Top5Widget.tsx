// RF-3.4 daily Top 5. STATUS: done against the API contract; backend path untested with a DB (P3-04).
"use client";
import { useEffect, useState } from "react";
import { fetchDailyTop5 } from "@/lib/api";
import type { DailyRecommendations } from "@/lib/types";
import GameCard from "./GameCard";

export default function Top5Widget({ onOpen }: { onOpen: (id: number) => void }) {
  const [data, setData] = useState<DailyRecommendations | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => { fetchDailyTop5().then(setData).catch(() => setErr(true)); }, []);
  if (err) return null; // widget is optional: never block the page
  return (
    <section>
      <h2 className="text-lg font-semibold mb-2">
        Tu Top 5 de hoy {data?.source === "fallback_popular" && <span className="text-xs text-slate-400">(populares: aún aprendiendo tus gustos)</span>}
      </h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {data?.games.map((g) => <GameCard key={g.id} game={g} onOpen={onOpen} compact />)}
      </div>
    </section>
  );
}
