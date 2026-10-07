/**
 * Phase 16 — rule-based "suggested awareness action" per district.
 *
 * Deliberately pure and deterministic (rules, not ML): an administrator needs a
 * stable, explainable hint they can audit. The function returns an i18n key
 * (never prose) so the copy stays translatable and testable. It only reads the
 * aggregated, already-suppressed district facts from the dashboard API.
 */
import type { DistrictRow } from '../api/client';

export type SuggestedActionKey =
  | 'admin_dash.action_suppressed'
  | 'admin_dash.action_safety'
  | 'admin_dash.action_cost'
  | 'admin_dash.action_distance'
  | 'admin_dash.action_social'
  | 'admin_dash.action_security'
  | 'admin_dash.action_general'
  | 'admin_dash.action_monitor';

/** Threshold above which a district is treated as broadly high-resistance. */
const HIGH_SHARE = 0.5;

export function suggestAction(district: DistrictRow): SuggestedActionKey {
  // Suppressed groups carry no actionable detail (k < 5); show nothing to avoid
  // steering outreach off a single family.
  if (district.is_suppressed) return 'admin_dash.action_suppressed';

  const topics = district.top_topics ?? [];

  // Most specific concern wins, ordered by the scheme's typical intervention.
  if (topics.includes('safety')) return 'admin_dash.action_safety';
  if (topics.includes('cost') || topics.includes('income')) return 'admin_dash.action_cost';
  if (topics.includes('distance')) return 'admin_dash.action_distance';
  if (topics.includes('social')) return 'admin_dash.action_social';
  if (topics.includes('security')) return 'admin_dash.action_security';

  // No recognised concern but broadly high resistance — generic counselling.
  const shareHigh = district.share_high ?? 0;
  if (shareHigh >= HIGH_SHARE) return 'admin_dash.action_general';

  return 'admin_dash.action_monitor';
}
