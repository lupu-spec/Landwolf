/** Freshness reflects a successful import, never a failed attempt or publisher validity. */
export type SourceHealth = {
  color: "green" | "yellow" | "red" | "neutral";
  label: string;
};
const HOUR = 60 * 60;
export function sourceHealth(
  automated: boolean,
  lastSuccess: number | null,
  now = Date.now() / 1000,
): SourceHealth {
  if (!automated)
    return { color: "neutral", label: "Directory only · not imported" };
  if (lastSuccess === null)
    return { color: "red", label: "No successful retrieval recorded" };
  if (
    !Number.isFinite(lastSuccess) ||
    !Number.isFinite(now) ||
    lastSuccess <= 0 ||
    lastSuccess > now
  )
    return {
      color: "red",
      label: "Invalid retrieval timestamp · check source details",
    };
  const age = now - lastSuccess;
  if (age <= 24 * HOUR)
    return { color: "green", label: "Updated within the past 24 hours" };
  if (age < 36 * HOUR)
    return {
      color: "yellow",
      label: "Updated more than 24 but less than 36 hours ago",
    };
  return { color: "red", label: "Last update was 36 or more hours ago" };
}
export function sourceTimestamp(value: number | null): string {
  if (value === null) return "Not yet retrieved";
  const instant = new Date(value * 1000);
  if (!Number.isFinite(value) || value <= 0 || Number.isNaN(instant.getTime()))
    return "Invalid timestamp";
  return instant.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}
