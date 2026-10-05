/** Bounded navigation motion; scrolling never activates a destination. */
export function dockScale(distance: number): number {
  if (!Number.isFinite(distance)) return 1;
  const proximity = Math.max(0, 1 - Math.abs(distance) / 115);
  return 1 + 0.42 * proximity * proximity;
}
export function cycleOffset(
  current: number,
  maximum: number,
  direction: number,
  step = 76,
): number {
  if (![current, maximum, direction, step].every(Number.isFinite)) return 0;
  if (maximum <= 0 || step <= 0 || direction === 0)
    return Math.max(0, Math.min(current, Math.max(0, maximum)));
  const position = Math.max(0, Math.min(current, maximum));
  return direction > 0
    ? position >= maximum - 2
      ? 0
      : Math.min(maximum, position + step)
    : position <= 2
      ? maximum
      : Math.max(0, position - step);
}
