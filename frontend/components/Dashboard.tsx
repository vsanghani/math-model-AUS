"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Controls } from "@/components/Controls";
import { ComparisonCharts } from "@/components/Charts";
import { MetricCards } from "@/components/MetricCards";
import { DEFAULT_PARAMS, type SimulationParams, type SimulationResponse } from "@/lib/types";

export function Dashboard() {
  const [params, setParams] = useState<SimulationParams>(DEFAULT_PARAMS);
  const [data, setData] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const seq = useRef(0);

  const run = useCallback(async (next: SimulationParams) => {
    const id = ++seq.current;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(next),
      });
      const body = await res.json();
      if (id !== seq.current) return;
      if (!res.ok) {
        const detail = body?.detail;
        throw new Error(
          typeof detail === "string" ? detail : "Simulation request was rejected.",
        );
      }
      setData(body as SimulationResponse);
    } catch (err) {
      if (id !== seq.current) return;
      setError(err instanceof Error ? err.message : "Could not reach the simulation engine.");
    } finally {
      if (id === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void run(params);
    }, 180);
    return () => window.clearTimeout(handle);
  }, [params, run]);

  const subtitle = useMemo(() => {
    const cap = Math.round(params.nom_cap / 1000);
    return `Treasury NOM glide (~255k to 235k) versus a ${cap}k net cap with a scaled-down student/temporary intake. Horizon 2025–2050.`;
  }, [params.nom_cap]);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-stone-300/80">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-8 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-navy">
              Australia · macroeconomic projection
            </p>
            <h1 className="mt-2 font-serif text-3xl leading-tight text-navy md:text-[2.15rem]">
              One Nation migration cap, 2025–2050
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-stone-600">{subtitle}</p>
          </div>
          <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-stone-500">
            {loading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Solving CES / cohort system
              </>
            ) : (
              "Nested CES · cohort-component"
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-8 px-6 py-8 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <Controls params={params} onChange={setParams} />
        </aside>

        <section className="min-w-0 space-y-8">
          {error ? (
            <div className="border border-rust/30 bg-rust/5 px-4 py-3 text-sm text-rust">
              {error} Start the FastAPI backend on port 8000, then refresh.
            </div>
          ) : null}

          {data ? (
            <>
              <MetricCards data={data} />
              <ComparisonCharts data={data} />
              <p className="max-w-4xl text-[12px] leading-relaxed text-stone-500">
                {data.notes} Sliders re-solve both scenarios from a shared 2025 jump-off.
                Cumulative GDP and fiscal figures are undiscounted sums of annual real
                2025-dollar flows. Capital deepening is the endogenous response of{" "}
                <span className="font-mono">K/L</span> when labour growth slows and the
                capital stock adjusts only partially toward its rental first-order condition.
              </p>
            </>
          ) : (
            <div className="h-64 border border-dashed border-stone-300" />
          )}
        </section>
      </main>
    </div>
  );
}
