// RF-2.1..2.4 chat UI over SSE. STATUS: done against the contract (lib/api.ts streamChat); needs backend + LLM key to try (P2-04).
// TODO(P2-06): restore history from GET /api/chat/{id}/messages. TODO(P2-08): markdown rendering, stop button.
"use client";
import { useRef, useState } from "react";
import { ApiError, streamChat } from "@/lib/api";
import type { Game } from "@/lib/types";
import GameCard from "./GameCard";

interface Msg { role: "user" | "assistant"; text: string; games?: Game[]; status?: string }

export default function ChatWidget({ onOpen }: { onOpen: (id: number) => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sid = useRef<string | undefined>(undefined);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", text }, { role: "assistant", text: "" }]);
    const patch = (fn: (a: Msg) => Msg) => setMsgs((m) => [...m.slice(0, -1), fn(m[m.length - 1])]);
    try {
      for await (const ev of streamChat(text, sid.current)) {
        if (ev.type === "session") sid.current = ev.session_id;
        else if (ev.type === "token") patch((a) => ({ ...a, text: a.text + ev.text, status: undefined }));
        else if (ev.type === "tool_call") patch((a) => ({ ...a, status: "Consultando catálogo…" }));
        else if (ev.type === "games") patch((a) => ({ ...a, games: ev.games }));
        else if (ev.type === "error") patch((a) => ({ ...a, text: ev.message, status: undefined }));
      }
    } catch (e) {
      const text = e instanceof ApiError && e.status === 401 ? "Inicia sesión (arriba a la derecha) para usar el asistente."
        : e instanceof ApiError && e.status === 503 ? "El asistente no está configurado todavía."
        : "No se pudo conectar con el asistente.";
      patch((a) => ({ ...a, text, status: undefined }));
    } finally { setBusy(false); }
  }

  return (
    <aside className="bg-slate-900 rounded-lg p-3 flex flex-col h-[70vh]">
      <div className="flex-1 overflow-auto space-y-3">
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block rounded px-3 py-2 text-sm ${m.role === "user" ? "bg-indigo-600" : "bg-slate-800"}`}>
              {m.text || m.status || "…"}
            </div>
            {m.games && <div className="grid grid-cols-2 gap-2 mt-2">{m.games.map((g) => <GameCard key={g.id} game={g} onOpen={onOpen} compact />)}</div>}
          </div>
        ))}
      </div>
      <form className="flex gap-2 mt-2" onSubmit={(e) => { e.preventDefault(); void send(); }}>
        <input className="flex-1 bg-slate-800 rounded px-3 py-2 text-sm" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Busco un MMORPG de fantasía para PC…" />
        <button disabled={busy} className="bg-indigo-500 px-3 rounded disabled:opacity-50">Enviar</button>
      </form>
    </aside>
  );
}
