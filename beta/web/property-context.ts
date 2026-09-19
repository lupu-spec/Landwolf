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

type LocationRecord = {
  source: string;
  state: string;
  location_description: string | null;
};

export function sourceAddress(record: LocationRecord): string {
  // Only these adapters populate location_description from a street-address field.
  // Never reinterpret legal descriptions, tract IDs, or a county as an address.
  const value = record.location_description?.trim() ?? "";
  if (
    !["usda_resales", "irs_auctions"].includes(record.source) ||
    value.length > 300
  )
    return "";
  const ending = /\b([A-Z]{2}),?\s+\d{5}(?:-\d{4})?$/.exec(value);
  return /^\d+[A-Za-z-]*\s+\S/.test(value) && ending?.[1] === record.state
    ? value
    : "";
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
