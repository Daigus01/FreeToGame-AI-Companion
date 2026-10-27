// RF-1.2 static filters. STATUS: done. Values come from lib/constants.ts (mirror of backend schemas.py).
"use client";
import { CATEGORIES, PLATFORMS, SORT_OPTIONS } from "@/lib/constants";
import type { Platform, SortBy } from "@/lib/types";

export interface FilterState { category?: string; platform: Platform; sort_by: SortBy }

export default function Filters({ value, onChange }: { value: FilterState; onChange: (v: FilterState) => void }) {
  const sel = "bg-slate-800 rounded px-2 py-1 text-sm";
  return (
    <div className="flex flex-wrap gap-2">
      <select className={sel} value={value.platform} onChange={(e) => onChange({ ...value, platform: e.target.value as Platform })}>
        {PLATFORMS.map((p) => <option key={p}>{p}</option>)}
      </select>
      <select className={sel} value={value.category ?? ""} onChange={(e) => onChange({ ...value, category: e.target.value || undefined })}>
        <option value="">todas las categorías</option>
        {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
      </select>
      <select className={sel} value={value.sort_by} onChange={(e) => onChange({ ...value, sort_by: e.target.value as SortBy })}>
        {SORT_OPTIONS.map((s) => <option key={s}>{s}</option>)}
      </select>
    </div>
  );
}
