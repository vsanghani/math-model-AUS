"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SimulationResponse, YearPoint } from "@/lib/types";

const NAVY = "#1f3a5f";
const OCHRE = "#b45309";
const NAVY_DASH = "#7c90a8";
const OCHRE_DASH = "#d4a574";

const SECTORS: { key: string; label: string }[] = [
  { key: "construction_housing", label: "Construction" },
  { key: "healthcare_aged_care", label: "Health & aged care" },
  { key: "education_export_services", label: "Education exports" },
  { key: "general_industry", label: "General industry" },
];

function merge(data: SimulationResponse) {
  return data.baseline.series.map((b, i) => {
    const p = data.policy.series[i];
    return { year: b.year, b, p };
  });
}

function ChartFrame({
  title,
  caption,
  children,
}: {
  title: string;
  caption: string;
  children: React.ReactNode;
}) {
  return (
    <figure className="border border-stone-300 bg-white/50 p-4">
      <figcaption>
        <h3 className="font-serif text-base text-navy">{title}</h3>
        <p className="mb-3 mt-1 text-[11px] leading-relaxed text-stone-500">{caption}</p>
      </figcaption>
      <div className="h-64 w-full">{children}</div>
    </figure>
  );
}

function axisMoney(v: number) {
  const bn = v / 1e9;
  return `${bn.toFixed(0)}`;
}

function tooltipStyle(): React.CSSProperties {
  return {
    background: "#f4efe6",
    border: "1px solid #d6d3d1",
    borderRadius: 0,
    fontSize: 12,
  };
}

export function ComparisonCharts({ data }: { data: SimulationResponse }) {
  const rows = merge(data);

  const gdp = rows.map(({ year, b, p }) => ({
    year,
    "Baseline GDP": b.gdp / 1e9,
    "Policy GDP": p.gdp / 1e9,
    "Baseline GDP/capita": b.gdp_per_capita,
    "Policy GDP/capita": p.gdp_per_capita,
  }));

  const dep = rows.map(({ year, b, p }) => ({
    year,
    "Baseline 65+/15–64": b.dependency_ratio * 100,
    "Policy 65+/15–64": p.dependency_ratio * 100,
  }));

  const fiscal = rows.map(({ year, b, p }) => ({
    year,
    "Baseline balance": b.fiscal_balance / 1e9,
    "Policy balance": p.fiscal_balance / 1e9,
  }));

  const wages = rows.map(({ year, b, p }) => ({
    year,
    "Baseline construction": b.sector_wage_pressure.construction_housing * 100,
    "Policy construction": p.sector_wage_pressure.construction_housing * 100,
    "Baseline health": b.sector_wage_pressure.healthcare_aged_care * 100,
    "Policy health": p.sector_wage_pressure.healthcare_aged_care * 100,
    "Baseline education": b.sector_wage_pressure.education_export_services * 100,
    "Policy education": p.sector_wage_pressure.education_export_services * 100,
  }));

  const lastB = data.baseline.series.at(-1) as YearPoint;
  const lastP = data.policy.series.at(-1) as YearPoint;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-serif text-xl text-navy">Side-by-side trajectories</h2>
        <div className="flex gap-4 font-mono text-[10px] uppercase tracking-wider">
          <span className="text-navy">Navy · Treasury baseline</span>
          <span className="text-ochre">Ochre · policy shock</span>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartFrame
          title="Headline real GDP"
          caption="AUD billions, 2025 prices. CES output from capital and nested labour."
        >
          <ResponsiveContainer>
            <LineChart data={gdp} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e7e5e4" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}`} />
              <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(1)} bn`, ""]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="Baseline GDP" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Policy GDP" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          title="Real GDP per capita"
          caption="AUD per person. Capital deepening can lift the per-capita path even as the level of GDP falls."
        >
          <ResponsiveContainer>
            <LineChart data={gdp} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e7e5e4" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                domain={["auto", "auto"]}
              />
              <Tooltip
                contentStyle={tooltipStyle()}
                formatter={(v: number) => [v.toLocaleString("en-AU", { maximumFractionDigits: 0 }), ""]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="Baseline GDP/capita" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Policy GDP/capita" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          title="Old-age dependency ratio"
          caption="Population 65+ divided by population 15–64, percent. Lower NOM ages the pyramid faster."
        >
          <ResponsiveContainer>
            <LineChart data={dep} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e7e5e4" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
              <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(1)}%`, ""]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="Baseline 65+/15–64" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Policy 65+/15–64" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          title="Net Commonwealth / State fiscal balance"
          caption="AUD billions. Age Pension wait of 8 years for new migrants is applied; health still follows the full age structure."
        >
          <ResponsiveContainer>
            <LineChart data={fiscal} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e7e5e4" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={axisMoney} />
              <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(1)} bn`, ""]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="Baseline balance" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Policy balance" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>
      </div>

      <ChartFrame
        title="Sectoral wage pressure"
        caption="Percent gap between frictional labour supply and shifting sectoral demand (construction, health, education). Positive is excess demand."
      >
        <ResponsiveContainer>
          <LineChart data={wages} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e7e5e4" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(1)}%`} />
            <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(2)}%`, ""]} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="Baseline construction" stroke={NAVY} dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="Policy construction" stroke={OCHRE} dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="Baseline health" stroke={NAVY_DASH} dot={false} strokeDasharray="4 3" strokeWidth={1.4} />
            <Line type="monotone" dataKey="Policy health" stroke={OCHRE_DASH} dot={false} strokeDasharray="4 3" strokeWidth={1.4} />
            <Line type="monotone" dataKey="Baseline education" stroke={NAVY} dot={false} strokeDasharray="1 3" strokeWidth={1.3} />
            <Line type="monotone" dataKey="Policy education" stroke={OCHRE} dot={false} strokeDasharray="1 3" strokeWidth={1.3} />
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>

      <div className="grid gap-px bg-stone-300 sm:grid-cols-4">
        {SECTORS.map((s) => (
          <div key={s.key} className="bg-paper px-4 py-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-stone-500">{s.label}</p>
            <p className="mt-1 text-[13px] text-stone-700">
              2050 labour share {((lastP.sector_shares[s.key] ?? 0) * 100).toFixed(1)}% policy vs{" "}
              {((lastB.sector_shares[s.key] ?? 0) * 100).toFixed(1)}% baseline
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
