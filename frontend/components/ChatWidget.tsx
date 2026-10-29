// RF-2.1..2.4 chat UI over SSE. STATUS: verified in browser with the mock LLM (LLM_PROVIDER=mock); real LLM pending (P2-01).
// Restores the latest conversation on load (P2-06), "Nueva conversación", and a stop button (P2-08, partial).
// Recommended games are NOT rendered here: they go to the catalog grid (D-16, owner decision; deviates from SRS RF-2.3).
// TODO(P2-08): markdown rendering, retry button, per-user usage limit.
"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, fetchChatMessages, fetchChatSessions, streamChat } from "@/lib/api";
import type { ChatMessageView, Game } from "@/lib/types";

type Msg = ChatMessageView & { status?: string };

/** The chat is text-only: recommended games are handed to the page via `onRecommend` and rendered in the catalog (D-16). */
export default function ChatWidget({ onRecommend }: { onRecommend: (games: Game[]) => void }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sid = useRef<string | undefined>(undefined);
  const abort = useRef<AbortController | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Restore the most recent conversation (401 = not logged in -> start empty, silently)
    fetchChatSessions()
      .then(async (list) => {
        if (list.length === 0) return;
        sid.current = list[0].id;
        setMsgs(await fetchChatMessages(list[0].id));
      })
      .catch(() => {});
  }, []);

  // Scroll ONLY the chat box. (element.scrollIntoView would also scroll the page, which on mobile — chat below the
  // catalog — fought with the "bring recommendations into view" scroll in app/page.tsx.)
  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs]);

  function newConversation() {
    sid.current = undefined;
    setMsgs([]);
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", text, games: [] }, { role: "assistant", text: "", games: [] }]);
    const patch = (fn: (a: Msg) => Msg) => setMsgs((m) => [...m.slice(0, -1), fn(m[m.length - 1])]);
    const ctrl = new AbortController();
    abort.current = ctrl;
    try {
      for await (const ev of streamChat(text, sid.current, ctrl.signal)) {
        if (ev.type === "session") sid.current = ev.session_id;
        else if (ev.type === "token") patch((a) => ({ ...a, text: a.text + ev.text, status: undefined }));
        else if (ev.type === "tool_call") patch((a) => ({ ...a, status: "Consultando catálogo…" }));
        else if (ev.type === "games") { patch((a) => ({ ...a, games: ev.games })); onRecommend(ev.games); }
        else if (ev.type === "error") patch((a) => ({ ...a, text: ev.message, status: undefined }));
      }
    } catch (e) {
      if (ctrl.signal.aborted) {
        patch((a) => ({ ...a, text: a.text ? `${a.text} (detenido)` : "(detenido)", status: undefined }));
      } else {
        const t = e instanceof ApiError && e.status === 401 ? "Inicia sesión (arriba a la derecha) para usar el asistente."
          : e instanceof ApiError && e.status === 503 ? "El asistente no está configurado todavía."
          : "No se pudo conectar con el asistente.";
        patch((a) => ({ ...a, text: t, status: undefined }));
      }
    } finally {
      abort.current = null;
      setBusy(false);
    }
  }

  return (
    <aside className="bg-slate-900 rounded-lg p-3 flex flex-col h-[70vh]">
      <div className="flex justify-between items-center mb-2">
        <h2 className="font-semibold text-sm">Asistente</h2>
        <button className="text-xs bg-slate-800 px-2 py-1 rounded disabled:opacity-50" disabled={busy || msgs.length === 0} onClick={newConversation}>
          Nueva conversación
        </button>
      </div>
      <div ref={scroller} className="flex-1 overflow-auto space-y-3" aria-live="polite">
        {msgs.length === 0 && <p className="text-sm text-slate-400">Pregúntame por juegos: «Busco un MMORPG de fantasía para PC que no sea muy antiguo».</p>}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block rounded px-3 py-2 text-sm whitespace-pre-line text-left ${m.role === "user" ? "bg-indigo-600" : "bg-slate-800"}`}>
              {m.text || m.status || "…"}
            </div>
            {m.games.length > 0 && (
              // Past messages (restored conversation) do NOT change the catalog by themselves; this chip re-applies them.
              <button className="block mt-1 text-xs text-indigo-300 hover:text-indigo-200 underline" onClick={() => onRecommend(m.games)}>
                ↗ Ver {m.games.length} {m.games.length === 1 ? "juego recomendado" : "juegos recomendados"} en el catálogo
              </button>
            )}
          </div>
        ))}
      </div>
      <form className="flex gap-2 mt-2" onSubmit={(e) => { e.preventDefault(); void send(); }}>
        <input className="flex-1 bg-slate-800 rounded px-3 py-2 text-sm" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Busco un MMORPG de fantasía para PC…" />
        {busy
          ? <button type="button" onClick={() => abort.current?.abort()} className="bg-slate-600 px-3 rounded">Parar</button>
          : <button className="bg-indigo-500 px-3 rounded">Enviar</button>}
      </form>
    </aside>
  );
}
