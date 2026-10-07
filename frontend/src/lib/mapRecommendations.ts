import { RecommendationOut } from '../api/client';

export function mapRecommendations(recs: RecommendationOut[]) {
  return recs.map((r) => ({
    // Primary key of the *stored* recommendation (Phase 8 feedback loop);
    // optional so legacy/localStorage rows still render.
    recId: r.id,
    occupation: {
      id: r.occupation_id,
      title: r.occupation_name,
      description: r.course_name ? `${r.course_name}` : '',
      typical_duration_months: null as number | null,
    },
    reasons: (r.reasons || []).map((x) => ({ ...x, type: 'positive' as const })),
    score: r.score,
    is_demo: r.is_demo,
  }));
}
