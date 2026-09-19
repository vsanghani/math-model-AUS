"use client";

import type { SimulationParams } from "@/lib/types";

type SliderSpec = {
  key: keyof SimulationParams;
  label: string;
  hint: string;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
};

const SLIDERS: SliderSpec[] = [
  {
    key: "current_nom",
    label: "Current NOM (ABS)",
    hint: "Year to March 2026, held as status quo",
    min: 200_000,
    max: 350_000,
    step: 5_000,
    format: (v) => `${Math.round(v / 1000)}k`,
  },
  {
    key: "home_affairs_fy_nom",
    label: "Home Affairs 2026–27",
    hint: "Burke target for this financial year",
    min: 180_000,
    max: 300_000,
    step: 5_000,
    format: (v) => `${Math.round(v / 1000)}k`,
  },
  {
    key: "home_affairs_long_run_nom",
    label: "Home Affairs from 2027–28",
    hint: "Ongoing Budget NOM target",
    min: 150_000,
    max: 280_000,
    step: 5_000,
    format: (v) => `${Math.round(v / 1000)}k`,
  },
  {
    key: "sigma_L",
    label: "Labour substitution σ_L",
    hint: "Domestic vs migrant CES elasticity",
    min: 0.8,
    max: 12,
    step: 0.1,
    format: (v) => v.toFixed(1),
  },
  {
    key: "tfp_growth",
    label: "TFP growth",
    hint: "Annual multifactor productivity",
    min: 0,
    max: 0.025,
    step: 0.001,
    format: (v) => `${(v * 100).toFixed(1)}%`,
  },
  {
    key: "housing_supply_elasticity",
    label: "Housing supply elasticity",
    hint: "Flow response of dwelling completions",
    min: 0.05,
    max: 2.0,
    step: 0.05,
    format: (v) => v.toFixed(2),
  },
];

export function Controls({
  params,
  onChange,
}: {
  params: SimulationParams;
  onChange: (next: SimulationParams) => void;
}) {
  return (
    <div className="space-y-6 border border-stone-300 bg-[#efe9dc] p-5">
      <div>
        <h2 className="font-serif text-lg text-navy">Policy levers</h2>
        <p className="mt-1 text-[12px] leading-relaxed text-stone-600">
          Status quo holds the current ABS NOM. Home Affairs follows Burke’s
          17 Sep 2026 targets; elasticities are shared across scenarios.
        </p>
      </div>
      {SLIDERS.map((spec) => {
        const value = params[spec.key];
        return (
          <label key={spec.key} className="block">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[13px] font-medium text-ink">{spec.label}</span>
              <span className="font-mono text-[12px] text-navy">{spec.format(value)}</span>
            </div>
            <p className="mb-2 mt-0.5 text-[11px] text-stone-500">{spec.hint}</p>
            <input
              type="range"
              min={spec.min}
              max={spec.max}
              step={spec.step}
              value={value}
              onChange={(e) =>
                onChange({ ...params, [spec.key]: Number(e.target.value) })
              }
              className="w-full"
            />
          </label>
        );
      })}
      <dl className="grid grid-cols-2 gap-x-3 gap-y-2 border-t border-stone-300 pt-4 font-mono text-[10px] uppercase tracking-wide text-stone-500">
        <div>
          <dt>WHM ballot</dt>
          <dd className="text-ink">45k / 5k</dd>
        </div>
        <div>
          <dt>Student share</dt>
          <dd className="text-ink">{(params.home_affairs_student_share * 100).toFixed(0)}%</dd>
        </div>
        <div>
          <dt>Skill tilt</dt>
          <dd className="text-ink">{params.home_affairs_skill_tilt.toFixed(2)}</dd>
        </div>
        <div>
          <dt>One Nation cap</dt>
          <dd className="text-ink">{Math.round(params.nom_cap / 1000)}k</dd>
        </div>
        <div>
          <dt>ON temp cut</dt>
          <dd className="text-ink">{Math.round(params.one_nation_temp_cut / 1000)}k</dd>
        </div>
      </dl>
    </div>
  );
}
