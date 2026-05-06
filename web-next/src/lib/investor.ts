/**
 * Shared investor math utilities.
 * Used by: listing-card.tsx, deal/page.tsx, dashboard/page.tsx, strategy/page.tsx
 */

export const GTA_RENT: Record<number, number> = {
  0: 1900, 1: 2200, 2: 2800, 3: 3500, 4: 4200,
};

export const NBHD_MULT: Record<string, number> = {
  "king west":      1.15,
  "yorkville":      1.25,
  "annex":          1.10,
  "distillery":     1.08,
  "liberty village":1.10,
  "leslieville":    1.05,
  "roncesvalles":   1.05,
  "beaches":        1.08,
  "forest hill":    1.20,
  "rosedale":       1.25,
  "lawrence park":  1.15,
  "midtown":        1.08,
  "downtown":       1.12,
  "east york":      0.98,
  "scarborough":    0.95,
  "north york":     1.02,
  "etobicoke":      1.00,
  "mississauga":    0.96,
  "brampton":       0.92,
  "markham":        0.98,
  "vaughan":        0.97,
  "richmond hill":  0.98,
  "oakville":       1.05,
};

export interface InvestorMetrics {
  down: number;
  mortgage: number;
  rent: number;
  expenses: number;
  grossYield: number;
  capRate: number;
  cashflow: number;
  cashOnCash: number;
  ptr: number;        // price-to-rent ratio (annual)
  noi: number;
}

export interface DealVerdict {
  label: "Strong Buy" | "Good Deal" | "Appreciation Play" | "Pass";
  color: string;
  score: number;      // 0–100 confidence score
  reasons: string[];  // 1-3 plain-English reasons
}

/**
 * Core investor math. Assumptions: 20% down, 25yr amort, 6.5% rate, 30% expense ratio.
 */
export function calcInvestor(
  price: number,
  beds: number,
  neighbourhood?: string,
  downPct = 0.20,
  interestRate = 0.065,
  hoaMonthly = 0,
  expenseRatio = 0.30,
): InvestorMetrics {
  const down = price * downPct;
  const principal = price - down;
  const r = interestRate / 12;
  const n = 300; // 25yr × 12
  const mortgage = Math.round(principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1));

  const nbhdKey = (neighbourhood || "").toLowerCase();
  const nbhdMult = Object.entries(NBHD_MULT).find(([k]) => nbhdKey.includes(k))?.[1] ?? 1.0;
  const bedCapped = Math.min(Math.max(Math.round(beds || 1), 0), 4);
  const rent = Math.round((GTA_RENT[bedCapped] ?? 2200) * nbhdMult);

  const expenses = Math.round(rent * expenseRatio) + hoaMonthly;
  const noi = rent - expenses;
  const grossYield = (rent * 12) / price * 100;
  const capRate = (noi * 12) / price * 100;
  const cashflow = noi - mortgage;
  const cashOnCash = down > 0 ? (cashflow * 12) / down * 100 : 0;
  const ptr = price / (rent * 12); // price-to-rent ratio (lower = better for investors)

  return { down, mortgage, rent, expenses, grossYield, capRate, cashflow, cashOnCash, ptr, noi };
}

/**
 * Score a deal 0–100 and return a verdict label + reasoning.
 * GTA context: PTR typically 30–45 (high cost market), cap rates typically 3–5%.
 */
export function getDealVerdict(
  cashOnCash: number,
  capRate: number,
  ptr: number,
): DealVerdict {
  const reasons: string[] = [];

  // PTR score — GTA-calibrated (lower is rarer and better)
  let ptrScore = 0;
  if (ptr < 28)      { ptrScore = 20; reasons.push(`Strong PTR ${ptr.toFixed(1)}× — rare in GTA`); }
  else if (ptr < 35) { ptrScore = 12; reasons.push(`Decent PTR ${ptr.toFixed(1)}×`); }
  else if (ptr < 45) { ptrScore = 5;  }
  else               { reasons.push(`High PTR ${ptr.toFixed(1)}× — price is expensive vs rent`); }

  // Cash-on-cash score
  let cocScore = 0;
  if (cashOnCash >= 6)       { cocScore = 25; reasons.push(`${cashOnCash.toFixed(1)}% cash-on-cash is excellent for GTA`); }
  else if (cashOnCash >= 2)  { cocScore = 16; reasons.push(`${cashOnCash.toFixed(1)}% cash-on-cash is positive`); }
  else if (cashOnCash >= -2) { cocScore = 8;  reasons.push("Near break-even cash flow"); }
  else                       { cocScore = 0;  reasons.push(`Negative cash flow of ${cashOnCash.toFixed(1)}%`); }

  // Cap rate score — GTA 3–5% is the typical range
  let capScore = 0;
  if (capRate >= 5)      { capScore = 20; reasons.push(`${capRate.toFixed(1)}% cap rate — above GTA average`); }
  else if (capRate >= 4) { capScore = 14; }
  else if (capRate >= 3) { capScore = 8;  }
  else                   { reasons.push(`${capRate.toFixed(1)}% cap rate — below GTA average`); }

  const baseScore = 35; // GTA baseline — high-cost markets start here
  const total = Math.min(100, baseScore + ptrScore + cocScore + capScore);

  if (total >= 78) return { label: "Strong Buy",        color: "#2ed573", score: total, reasons: reasons.slice(0, 3) };
  if (total >= 60) return { label: "Good Deal",         color: "#7bed9f", score: total, reasons: reasons.slice(0, 3) };
  if (total >= 47) return { label: "Appreciation Play", color: "#ffa502", score: total, reasons: reasons.slice(0, 3) };
  return              { label: "Pass",                  color: "#cf6357", score: total, reasons: reasons.slice(0, 3) };
}

/** Format a dollar cash flow with +/- sign */
export function fmtCashflow(cf: number): string {
  const abs = Math.abs(cf).toLocaleString("en-CA");
  return cf >= 0 ? `+$${abs}` : `-$${abs}`;
}
