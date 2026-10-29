// STATUS: done (presentational). Used by the catalog grid (also for chat suggestions, D-16) and the Top5 widget (RF-1.1, RF-2.3, RF-3.4).
import type { Game } from "@/lib/types";

export default function GameCard({ game, onOpen, compact = false }: { game: Game; onOpen: (id: number) => void; compact?: boolean }) {
  return (
    <button
      onClick={() => onOpen(game.id)}
      className="text-left rounded-lg overflow-hidden bg-slate-900 hover:ring-2 hover:ring-indigo-400 transition"
    >
      {game.thumbnail && /* eslint-disable-next-line @next/next/no-img-element */
        <img src={game.thumbnail} alt={game.title} className="w-full aspect-video object-cover" loading="lazy" />}
      <div className="p-3">
        <div className="font-semibold">{game.title}</div>
        <div className="text-xs text-slate-400">{[game.genre, game.platform].filter(Boolean).join(" · ")}</div>
        {!compact && <p className="mt-1 text-sm text-slate-300 line-clamp-2">{game.short_description}</p>}
      </div>
    </button>
  );
}
