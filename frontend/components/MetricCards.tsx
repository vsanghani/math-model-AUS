"use client";

import type { HorizonDelta, SimulationResponse } from "@/lib/types";
import { aud, pct, pp, signedAudBn } from "@/lib/format";

function tone(value: number, invert = false): string {
  const v = invert ? -value : value;
  if (Math.abs(value) < 1e-12) return "text-stone-600";
  return v >= 0 ? "text-moss" : "text-rust";
}

function Card({
  title,
  horizon,
  primary,
  secondary,
  className,
}: {
  title: string;
  horizon: string;
  primary: string;
  secondary: string;
  className?: string;
}) {
  return (
    <article className={`border border-stone-300 bg-white/60 px-4 py-3 ${className ?? ""}`}>
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-stone-500">
        {horizon} · {title}
      </p>
      <p className="mt-1 font-serif text-2xl leading-none">{primary}</p>
      <p className="mt-1.5 text-[12px] text-stone-500">{secondary}</p>
    </article>
  );
}

function pair(d: HorizonDelta) {
  return [
    {
      title: "Δ real GDP",
      primary: signedAudBn(d.cumulative_gdp),
      secondary: `Level in ${d.year}: ${pct(d.gdp_pct)} (${signedAudBn(d.gdp_level)})`,
      className: tone(d.cumulative_gdp),
    },
    {
      title: "Δ GDP per capita",
      primary: `${d.avg_gdp_per_capita >= 0 ? "+" : "−"}${aud(Math.abs(d.avg_gdp_per_capita))}`,
      secondary: `Average annual gap · terminal ${pct(d.gdp_per_capita_pct)}`,
      className: tone(d.avg_gdp_per_capita),
    },
    {
      title: "Δ fiscal position",
      primary: signedAudBn(d.cumulative_fiscal),
      secondary: `Cumulative budget balance vs current NOM · ${d.year} flow ${signedAudBn(d.fiscal_level)}`,
      className: tone(d.cumulative_fiscal),
    },
    {
      title: "Δ rental price index",
      primary: pct(d.rent_index_pct),
      secondary: `Index points ${d.rent_index_level >= 0 ? "+" : "−"}${Math.abs(d.rent_index_level).toFixed(3)} · dependency ${pp(d.dependency_ratio_pp)}`,
      className: tone(d.rent_index_pct, true),
    },
  ];
}

export function MetricCards({ data }: { data: SimulationResponse }) {
  const haTen = pair(data.ha_deltas_10y);
  const ha25 = pair(data.ha_deltas_25y);
  const on25 = pair(data.on_deltas_25y);

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="font-serif text-xl text-navy">Home Affairs minus current NOM</h2>
        <p className="font-mono text-[10px] uppercase tracking-wider text-stone-500">
          Undiscounted · real 2025 dollars
        </p>
      </div>
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-stone-500">
          10-year window · 2025–{data.ha_deltas_10y.year}
        </p>
        <div className="grid gap-px bg-stone-300 sm:grid-cols-2 xl:grid-cols-4">
          {haTen.map((c) => (
            <Card key={`ha10-${c.title}`} horizon="10y" {...c} />
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-stone-500">
          25-year window · 2025–{data.ha_deltas_25y.year}
        </p>
        <div className="grid gap-px bg-stone-300 sm:grid-cols-2 xl:grid-cols-4">
          {ha25.map((c) => (
            <Card key={`ha25-${c.title}`} horizon="25y" {...c} />
          ))}
        </div>
      </div>
      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-stone-500">
          One Nation vs current NOM · 25-year window
        </p>
        <div className="grid gap-px bg-stone-300 sm:grid-cols-2 xl:grid-cols-4">
          {on25.map((c) => (
            <Card key={`on25-${c.title}`} horizon="ON 25y" {...c} />
          ))}
        </div>
      </div>
    </div>
  );
}
