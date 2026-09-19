const validPoints = (points = []) => points
  .map((point) => ({ year: Number(point?.year), value: Number(point?.value) }))
  .filter((point) => Number.isInteger(point.year) && Number.isFinite(point.value))
  .sort((a, b) => a.year - b.year)
  .filter((point, index, records) => records.findIndex((item) => item.year === point.year) === index)
  .slice(-5);

/** A deliberately conservative annual OLS projection for planning context. */
export function buildLinearProjection(points, { nonNegative = true } = {}) {
  const historical = validPoints(points);
  if (historical.length < 3) return { historical, projected: [], status: 'insufficient' };

  const meanYear = historical.reduce((sum, point) => sum + point.year, 0) / historical.length;
  const meanValue = historical.reduce((sum, point) => sum + point.value, 0) / historical.length;
  const denominator = historical.reduce((sum, point) => sum + ((point.year - meanYear) ** 2), 0);
  if (!denominator) return { historical, projected: [], status: 'unstable' };
  const slope = historical.reduce(
    (sum, point) => sum + ((point.year - meanYear) * (point.value - meanValue)), 0,
  ) / denominator;
  const intercept = meanValue - (slope * meanYear);
  const last = historical.at(-1);
  const projected = Array.from({ length: 5 }, (_, index) => {
    const year = last.year + index + 1;
    return { year, value: intercept + (slope * year) };
  });
  const range = Math.max(...historical.map(({ value }) => value)) - Math.min(...historical.map(({ value }) => value));
  const invalid = projected.some(({ value }) => !Number.isFinite(value) || (nonNegative && value < 0));
  const excessive = projected.some(({ value }) => Math.abs(value - last.value) > Math.max(Math.abs(last.value), range * 6));
  if (invalid || excessive) return { historical, projected: [], status: 'unstable' };
  return { historical, projected, status: 'available', method: 'Ordinary least-squares linear regression' };
}

