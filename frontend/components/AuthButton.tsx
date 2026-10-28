// Login/logout (D-11: Google + Discord OAuth). STATUS: done against the API contract; real providers pending (P1-11).
"use client";
import { useEffect, useState } from "react";
import { fetchMe, fetchProviders, loginUrl, logout } from "@/lib/api";
import type { AuthProvider, Me } from "@/lib/types";

const LABEL: Record<AuthProvider, string> = { google: "Google", discord: "Discord" };

export default function AuthButton({ onChange }: { onChange?: (me: Me | null) => void }) {
  const [me, setMe] = useState<Me | null | undefined>(undefined); // undefined = loading
  const [providers, setProviders] = useState<AuthProvider[]>([]);

  useEffect(() => {
    fetchMe().then((m) => { setMe(m); onChange?.(m); }).catch(() => setMe(null));
    fetchProviders().then((p) => setProviders(p.providers)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (me === undefined) return null;
  if (me)
    return (
      <div className="flex items-center gap-2 text-sm">
        {me.avatar_url && /* eslint-disable-next-line @next/next/no-img-element */ <img src={me.avatar_url} alt="" className="w-7 h-7 rounded-full" referrerPolicy="no-referrer" />}
        <span>{me.name ?? me.email}</span>
        <button className="bg-slate-700 px-2 py-1 rounded" onClick={async () => { await logout(); setMe(null); onChange?.(null); window.location.reload(); }}>
          Salir
        </button>
      </div>
    );
  if (providers.length === 0) return <span className="text-xs text-slate-500">Login no configurado</span>;
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-slate-400">Entrar con</span>
      {providers.map((p) => (
        <a key={p} href={loginUrl(p)} className="bg-indigo-500 hover:bg-indigo-400 px-3 py-1 rounded">{LABEL[p]}</a>
      ))}
    </div>
  );
}
