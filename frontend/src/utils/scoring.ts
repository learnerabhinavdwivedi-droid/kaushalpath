import type { CompareResultItem, MemberWeights, WeightsInput } from '../api/client';

// Fixed criterion order shared by the compare table, radar chart and the
// consensus what-if preview. Each maps to an i18n label key.
export const CRITERIA: (keyof WeightsInput)[] = [
  'cost',
  'duration',
  'salary',
  'local_jobs',
  'distance',
];

export const CRITERIA_LABEL: Record<string, string> = {
  cost: 'weights.cost',
  duration: 'weights.duration',
  salary: 'weights.salary',
  local_jobs: 'weights.local_jobs',
  distance: 'weights.distance',
};

// Plain-language source note per criterion (provenance is never hidden).
export const CRITERIA_SOURCE: Record<string, string> = {
  cost: 'Course fee (catalogue)',
  duration: 'Course length (catalogue)',
  salary: 'Market avg salary (market data)',
  local_jobs: 'Demand index (market data)',
  distance: 'Nearest centre vs your district',
};

// Deterministic re-scoring: weighted mean of the normalised (0..1) criteria per
// member, averaged across members. Mirrors compare_svc so a client-side what-if
// preview agrees with what POST /rooms/{code}/compare would return for the same
// weights — no server mutation, still fully reproducible.
export function familyRanking(
  results: CompareResultItem[],
  weights: MemberWeights[],
  override?: Partial<WeightsInput> & { user_id: number }
): { occupation_id: number; occupation_name: string; family_score: number }[] {
  return results
    .map((r) => {
      const totals = weights.map((w) => {
        const eff: WeightsInput = { ...w, ...(override && override.user_id === w.user_id ? override : {}) };
        return CRITERIA.reduce((sum, c) => sum + (eff[c] ?? 0) * r.criteria[c], 0);
      });
      const family = totals.length ? totals.reduce((a, b) => a + b, 0) / totals.length : 0;
      return {
        occupation_id: r.occupation_id,
        occupation_name: r.occupation_name,
        family_score: Math.round(family * 10000) / 10000,
      };
    })
    .sort((a, b) => b.family_score - a.family_score);
}

// Which criterion most explains a given option's lead — used for the
// one-sentence "why this ranks higher" line (reason codes, never a model).
export function topDriver(
  winner: CompareResultItem,
  weights: MemberWeights[]
): string {
  const avgWeight = (c: keyof WeightsInput) =>
    weights.reduce((s, w) => s + w[c], 0) / (weights.length || 1);
  let best = CRITERIA[0];
  let bestScore = -Infinity;
  for (const c of CRITERIA) {
    const score = avgWeight(c) * winner.criteria[c];
    if (score > bestScore) {
      bestScore = score;
      best = c;
    }
  }
  return best;
}
