export function computeNilai(
  criteria: { score: number; weight: number }[],
): number {
  const total = criteria.reduce(
    (sum, c) => sum + (c.score / 4) * c.weight,
    0,
  );
  return Math.round(total * 100) / 100;
}

export function predikatOf(nilai: number): string {
  if (nilai >= 85) return "A";
  if (nilai >= 70) return "B";
  if (nilai >= 55) return "C";
  return "D";
}

export function rubricWeightSum(
  criteria: { weight: number }[],
): number {
  return criteria.reduce((sum, c) => sum + Number(c.weight || 0), 0);
}
