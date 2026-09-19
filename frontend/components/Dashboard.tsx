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
    return `Current ABS NOM (${Math.round(params.current_nom / 1000)}k) versus Home Affairs targets of ${Math.round(params.home_affairs_fy_nom / 1000)}k in 2026–27 and ${Math.round(params.home_affairs_long_run_nom / 1000)}k from 2027–28. One Nation remains a ${Math.round(params.nom_cap / 1000)}k cap.`;
  }, [params.current_nom, params.home_affairs_fy_nom, params.home_affairs_long_run_nom, params.nom_cap]);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-stone-300/80">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-8 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-navy">
              Australia · macroeconomic projection
            </p>
            <h1 className="mt-2 font-serif text-3xl leading-tight text-navy md:text-[2.15rem]">
              Home Affairs migration package, 2025–2050
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
              <section className="border border-stone-300 bg-white/40 px-5 py-4">
                <h2 className="font-serif text-lg text-navy">Burke, 17 September 2026</h2>
                <p className="mt-1 text-[12px] leading-relaxed text-stone-600">
                  National Press Club package. Budget NOM is now a target, not a forecast.
                  Composition is tighter on temporary visas even though the cut is milder than One Nation.
                </p>
                <ul className="mt-3 grid gap-2 text-[12px] leading-relaxed text-stone-700 sm:grid-cols-2">
                  <li>NOM 245,000 in 2026–27, then 225,000 a year (from ABS 292,100).</li>
                  <li>Working-holiday ballot: 45,000 second-year and 5,000 third-year places (from 57,000 / 31,000).</li>
                  <li>Student dependants restricted; visa-hopping curtailed.</li>
                  <li>Overstayer detention and removals; visitor visas “no further stay”.</li>
                  <li>Skilled list priority: construction, health, education, enforcement, defence, agriculture.</li>
                  <li>Delivered by ministerial direction after Coalition talks collapsed.</li>
                </ul>
              </section>
              <MetricCards data={data} />
              <ComparisonCharts data={data} />
              <p className="max-w-4xl text-[12px] leading-relaxed text-stone-500">
                {data.notes} Sliders re-solve all three scenarios from a shared 2025 jump-off.
                Home Affairs NOM steps down in 2026 and 2027; current NOM is held at the latest ABS print.
                Cumulative GDP and fiscal figures are undiscounted sums of annual real
                2025-dollar flows.
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
