// RF-1.3 detail modal. STATUS: done (basic). TODO(P1-08): screenshot carousel, a11y focus trap, ESC to close.
"use client";
import { useEffect, useState } from "react";
import { fetchGame, track } from "@/lib/api";
import type { GameDetail } from "@/lib/types";

export default function GameModal({ gameId, onClose }: { gameId: number; onClose: () => void }) {
  const [g, setG] = useState<GameDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetchGame(gameId).then(setG).catch((e) => setErr(String(e)));
    track(gameId, "click"); // feeds RF-3.2
  }, [gameId]);
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div className="bg-slate-900 rounded-lg max-w-3xl w-full max-h-[90vh] overflow-auto p-5" onClick={(e) => e.stopPropagation()}>
        {err && <p className="text-red-400">{err}</p>}
        {!g && !err && <p>Cargando…</p>}
        {g && (
          <>
            <div className="flex justify-between"><h2 className="text-2xl font-bold">{g.title}</h2><button onClick={onClose}>✕</button></div>
            <p className="text-sm text-slate-400">{[g.genre, g.platform, g.developer, g.publisher, g.release_date].filter(Boolean).join(" · ")}</p>
            <div className="grid grid-cols-2 gap-2 my-3">
              {g.screenshots.slice(0, 4).map((s) => /* eslint-disable-next-line @next/next/no-img-element */ <img key={s.id} src={s.image} alt="" className="rounded" />)}
            </div>
            <p className="text-sm whitespace-pre-line">{g.description}</p>
            {g.minimum_system_requirements && (
              <ul className="mt-3 text-xs text-slate-300">
                {Object.entries(g.minimum_system_requirements).map(([k, v]) => v && <li key={k}><b>{k}:</b> {v}</li>)}
              </ul>
            )}
            <div className="mt-4 flex gap-2 flex-wrap">
              {g.game_url && <a className="bg-indigo-500 px-3 py-1 rounded" href={g.game_url} target="_blank" rel="noreferrer">Jugar / Descargar</a>}
              {/* TODO(P1-05): library buttons need real auth + `games` synced (P1-02, P1-04) */}
              {(["saved", "played", "disliked"] as const).map((t) => (
                <button key={t} className="bg-slate-700 px-3 py-1 rounded text-sm" onClick={() => track(g.id, t)}>
                  {{ saved: "Guardar", played: "Jugado", disliked: "No me interesa" }[t]}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
