const ACREAGE_LIMIT = 10_000_000;
export const acreagePresets: Record<string, readonly [number, number]> = {
  "5-50": [5, 50],
  "0.01-5": [0.01, 5],
  "50-500": [50, 500],
  "500-10000000": [500, ACREAGE_LIMIT],
};

export function acreageRange(
  preset: string,
  minimum: string,
  maximum: string,
): readonly [number, number] {
  const range =
    preset === "custom"
      ? [Number(minimum), Number(maximum)]
      : acreagePresets[preset];
  const low = range?.[0];
  const high = range?.[1];
  if (
    low === undefined ||
    high === undefined ||
    !Number.isFinite(low) ||
    !Number.isFinite(high) ||
    low <= 0 ||
    high < low ||
    high > ACREAGE_LIMIT
  )
    throw new Error(
      "Enter a valid acreage range: minimum must not exceed maximum.",
    );
  return [low, high];
}

export function huntName(
  location: string,
  low: number,
  high: number,
  auction: boolean,
): string {
  const size = high === ACREAGE_LIMIT ? `${low}+` : `${low}–${high}`;
  return `${location} · ${size} acres${auction ? " · Auctions" : ""}`.slice(
    0,
    80,
  );
}
