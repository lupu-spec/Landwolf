/** Hypothetical inputs, not a valuation or a substitute for missing evidence. */
export function bidRange(bid: number, downside = 5, upside = 20) {
  if (
    ![bid, downside, upside].every(Number.isFinite) ||
    bid <= 0 ||
    bid > 1_000_000_000 ||
    downside < 0 ||
    downside >= 100 ||
    upside < 0 ||
    upside > 1000
  )
    return null;
  const low = Math.round(bid * (1 - downside / 100) * 100) / 100;
  const likely = Math.round(bid * 100) / 100;
  const high = Math.round(bid * (1 + upside / 100) * 100) / 100;
  if (low <= 0 || high > 1_000_000_000) return null;
  return { low, likely, high };
}

export function similarFilters(record: {
  state: string;
  county: string | null;
  acres: number | null;
  category: string;
}): Record<string, string> {
  return {
    state: record.state,
    location: record.county ?? "",
    min_acres:
      record.acres === null ? "" : String(Math.floor(record.acres * 100) / 100),
    category: record.category,
    max_price: "",
    source: "",
  };
}
