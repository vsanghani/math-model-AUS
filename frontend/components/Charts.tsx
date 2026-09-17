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
const MOSS = "#3f6212";
const OCHRE = "#b45309";
const NAVY_DASH = "#7c90a8";
const MOSS_DASH = "#65a30d";

const SECTORS: { key: string; label: string }[] = [
  { key: "construction_housing", label: "Construction" },
  { key: "healthcare_aged_care", label: "Health & aged care" },
  { key: "education_export_services", label: "Education exports" },
  { key: "general_industry", label: "General industry" },
];

function merge(data: SimulationResponse) {
  return data.current.series.map((c, i) => ({
    year: c.year,
    c,
    h: data.home_affairs.series[i],
    o: data.one_nation.series[i],
  }));
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
  return `${v.toFixed(0)}`;
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

  const nom = rows.map(({ year, c, h, o }) => ({
    year,
    "Current NOM": c.nom / 1000,
    "Home Affairs": h.nom / 1000,
    "One Nation": o.nom / 1000,
  }));

  const gdp = rows.map(({ year, c, h, o }) => ({
    year,
    "Current GDP": c.gdp / 1e9,
    "Home Affairs GDP": h.gdp / 1e9,
    "One Nation GDP": o.gdp / 1e9,
    "Current GDP/capita": c.gdp_per_capita,
    "Home Affairs GDP/capita": h.gdp_per_capita,
    "One Nation GDP/capita": o.gdp_per_capita,
  }));

  const dep = rows.map(({ year, c, h, o }) => ({
    year,
    "Current 65+/15–64": c.dependency_ratio * 100,
    "Home Affairs 65+/15–64": h.dependency_ratio * 100,
    "One Nation 65+/15–64": o.dependency_ratio * 100,
  }));

  const fiscal = rows.map(({ year, c, h, o }) => ({
    year,
    "Current balance": c.fiscal_balance / 1e9,
    "Home Affairs balance": h.fiscal_balance / 1e9,
    "One Nation balance": o.fiscal_balance / 1e9,
  }));

  const wages = rows.map(({ year, c, h }) => ({
    year,
    "Current construction": c.sector_wage_pressure.construction_housing * 100,
    "Home Affairs construction": h.sector_wage_pressure.construction_housing * 100,
    "Current health": c.sector_wage_pressure.healthcare_aged_care * 100,
    "Home Affairs health": h.sector_wage_pressure.healthcare_aged_care * 100,
  }));

  const lastC = data.current.series.at(-1) as YearPoint;
  const lastH = data.home_affairs.series.at(-1) as YearPoint;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-serif text-xl text-navy">Trajectories versus current NOM</h2>
        <div className="flex flex-wrap gap-4 font-mono text-[10px] uppercase tracking-wider">
          <span className="text-navy">Navy · current ABS 292k</span>
          <span className="text-moss">Moss · Home Affairs</span>
          <span className="text-ochre">Ochre · One Nation</span>
        </div>
      </div>

      <ChartFrame
        title="Net overseas migration"
        caption="Thousands of persons per year. 2025 is the shared pre-announcement rate; Burke’s targets bind from 2026."
      >
        <ResponsiveContainer>
          <LineChart data={nom} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e7e5e4" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}k`} />
            <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(0)}k`, ""]} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="stepAfter" dataKey="Current NOM" stroke={NAVY} dot={false} strokeWidth={1.8} />
            <Line type="stepAfter" dataKey="Home Affairs" stroke={MOSS} dot={false} strokeWidth={1.8} />
            <Line type="stepAfter" dataKey="One Nation" stroke={OCHRE} dot={false} strokeWidth={1.8} />
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>

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
              <Line type="monotone" dataKey="Current GDP" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Home Affairs GDP" stroke={MOSS} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="One Nation GDP" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          title="Real GDP per capita"
          caption="AUD per person. A smaller labour force raises K/L, so the per-capita gap is much narrower than the GDP-level gap."
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
              <Line type="monotone" dataKey="Current GDP/capita" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Home Affairs GDP/capita" stroke={MOSS} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="One Nation GDP/capita" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          title="Old-age dependency ratio"
          caption="Population 65+ divided by population 15–64, percent. Cutting NOM ages the pyramid faster."
        >
          <ResponsiveContainer>
            <LineChart data={dep} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e7e5e4" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
              <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(1)}%`, ""]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="Current 65+/15–64" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Home Affairs 65+/15–64" stroke={MOSS} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="One Nation 65+/15–64" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame
          title="Net Commonwealth / State fiscal balance"
          caption="AUD billions. Age Pension wait of 8 years for new migrants; health still follows the full age structure."
        >
          <ResponsiveContainer>
            <LineChart data={fiscal} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#e7e5e4" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={axisMoney} />
              <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(1)} bn`, ""]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="Current balance" stroke={NAVY} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="Home Affairs balance" stroke={MOSS} dot={false} strokeWidth={1.8} />
              <Line type="monotone" dataKey="One Nation balance" stroke={OCHRE} dot={false} strokeWidth={1.8} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>
      </div>

      <ChartFrame
        title="Sectoral wage pressure — construction and health"
        caption="Percent gap between frictional labour supply and demand. Burke’s skilled-list tilt lifts construction and health demand even as total NOM falls."
      >
        <ResponsiveContainer>
          <LineChart data={wages} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e7e5e4" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(1)}%`} />
            <Tooltip contentStyle={tooltipStyle()} formatter={(v: number) => [`${v.toFixed(2)}%`, ""]} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="Current construction" stroke={NAVY} dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="Home Affairs construction" stroke={MOSS} dot={false} strokeWidth={1.5} />
            <Line type="monotone" dataKey="Current health" stroke={NAVY_DASH} dot={false} strokeDasharray="4 3" strokeWidth={1.4} />
            <Line type="monotone" dataKey="Home Affairs health" stroke={MOSS_DASH} dot={false} strokeDasharray="4 3" strokeWidth={1.4} />
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>

      <div className="grid gap-px bg-stone-300 sm:grid-cols-4">
        {SECTORS.map((s) => (
          <div key={s.key} className="bg-paper px-4 py-3">
            <p className="font-mono text-[10px] uppercase tracking-wider text-stone-500">{s.label}</p>
            <p className="mt-1 text-[13px] text-stone-700">
              2050 labour share {((lastH.sector_shares[s.key] ?? 0) * 100).toFixed(1)}% Home Affairs vs{" "}
              {((lastC.sector_shares[s.key] ?? 0) * 100).toFixed(1)}% current
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
