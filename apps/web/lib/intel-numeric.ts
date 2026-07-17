export const INTEL_DECIMAL_PLACES = 3;

export function roundIntelNumber(value: number): number {
  const rounded = Number(value.toFixed(INTEL_DECIMAL_PLACES));
  // Normalize negative zero so rendering stays stable.
  return Object.is(rounded, -0) ? 0 : rounded;
}

export function formatIntelNumber(value: number, preserveIntegers = true): string {
  if (!Number.isFinite(value)) return "—";
  if (preserveIntegers && Number.isInteger(value)) return String(value);
  return roundIntelNumber(value).toFixed(INTEL_DECIMAL_PLACES);
}
