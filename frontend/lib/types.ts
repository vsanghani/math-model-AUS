export type SimulationParams = {
  nom_cap: number;
  baseline_nom: number;
  baseline_nom_near: number;
  sigma: number;
  sigma_L: number;
  alpha: number;
  tfp_growth: number;
  delta_k: number;
  real_rate: number;
  capital_adjust_lambda: number;
  housing_supply_elasticity: number;
  housing_demand_income_elasticity: number;
  policy_student_share: number;
};

export type YearPoint = {
  year: number;
  population: number;
  nom: number;
  student_stock: number;
  working_age: number;
  old_age: number;
  dependency_ratio: number;
  prime_working_age_share: number;
  participation_rate: number;
  labour_native: number;
  labour_migrant: number;
  labour_total: number;
  gdp: number;
  gdp_per_capita: number;
  capital: number;
  k_over_l: number;
  wage_index_d: number;
  wage_index_m: number;
  wage_index_avg: number;
  housing_shortfall: number;
  shortfall_index: number;
  rent_index: number;
  education_exports: number;
  sector_shares: Record<string, number>;
  sector_labour_gap: Record<string, number>;
  sector_wage_pressure: Record<string, number>;
  fiscal_balance: number;
  fiscal_balance_to_gdp: number;
  revenue: number;
  outlays: number;
};

export type HorizonDelta = {
  year: number;
  gdp_level: number;
  gdp_pct: number;
  gdp_per_capita_level: number;
  gdp_per_capita_pct: number;
  cumulative_gdp: number;
  avg_gdp_per_capita: number;
  cumulative_fiscal: number;
  fiscal_level: number;
  rent_index_level: number;
  rent_index_pct: number;
  dependency_ratio_pp: number;
  population: number;
};

export type SimulationResponse = {
  baseline: { name: string; series: YearPoint[] };
  policy: { name: string; series: YearPoint[] };
  deltas_10y: HorizonDelta;
  deltas_25y: HorizonDelta;
  parameters: Record<string, number>;
  notes: string;
};

export const DEFAULT_PARAMS: SimulationParams = {
  nom_cap: 130_000,
  baseline_nom: 235_000,
  baseline_nom_near: 255_000,
  sigma: 0.9,
  sigma_L: 5.0,
  alpha: 0.38,
  tfp_growth: 0.01,
  delta_k: 0.055,
  real_rate: 0.045,
  capital_adjust_lambda: 0.18,
  housing_supply_elasticity: 0.3,
  housing_demand_income_elasticity: 0.35,
  policy_student_share: 0.16,
};
