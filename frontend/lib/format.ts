export function audBn(value: number, digits = 1): string {
  const bn = value / 1e9;
  const abs = Math.abs(bn);
  const formatted = abs.toLocaleString("en-AU", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return `${bn < 0 ? "−" : ""}$${formatted} bn`;
}

export function aud(value: number, digits = 0): string {
  const abs = Math.abs(value);
  const formatted = abs.toLocaleString("en-AU", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return `${value < 0 ? "−" : ""}$${formatted}`;
}

export function people(value: number): string {
  const sign = value < 0 ? "−" : "";
  const abs = Math.abs(value);
  if (abs >= 1e6) {
    return `${sign}${(abs / 1e6).toFixed(2)} m`;
  }
  return `${sign}${(abs / 1e3).toFixed(0)} k`;
}

export function pct(value: number, digits = 2): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(digits)}%`;
}

export function signedAudBn(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${audBn(Math.abs(value))}`;
}

export function pp(value: number, digits = 2): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(digits)} pp`;
}
