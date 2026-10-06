import { describe, it, expect } from 'vitest';
import { suggestAction } from './resistance';
import type { DistrictRow } from '../api/client';

function district(overrides: Partial<DistrictRow> = {}): DistrictRow {
  return {
    district: 'TestDistrict',
    state: 'UP',
    lat: 26.8,
    lon: 80.9,
    n: 10,
    avg_rs: 0.4,
    share_high: 0.2,
    top_topics: [],
    shift: { softened: 1, hardened: 1, unchanged: 8 },
    is_suppressed: false,
    ...overrides,
  };
}

describe('suggestAction (Phase 16 rules)', () => {
  it('returns no action for a suppressed small group', () => {
    expect(suggestAction(district({ is_suppressed: true, top_topics: ['safety'] }))).toBe(
      'admin_dash.action_suppressed',
    );
  });

  it('prioritises safety outreach', () => {
    expect(suggestAction(district({ top_topics: ['income', 'safety'] }))).toBe(
      'admin_dash.action_safety',
    );
  });

  it('maps cost / income to fee-and-income facts', () => {
    expect(suggestAction(district({ top_topics: ['cost'] }))).toBe('admin_dash.action_cost');
    expect(suggestAction(district({ top_topics: ['income'] }))).toBe('admin_dash.action_cost');
  });

  it('maps distance to local-provider outreach', () => {
    expect(suggestAction(district({ top_topics: ['distance'] }))).toBe('admin_dash.action_distance');
  });

  it('maps social to success stories and security to generic counselling', () => {
    expect(suggestAction(district({ top_topics: ['social'] }))).toBe('admin_dash.action_social');
    expect(suggestAction(district({ top_topics: ['security'] }))).toBe('admin_dash.action_security');
  });

  it('falls back to generic action when broadly high without a known concern', () => {
    expect(suggestAction(district({ top_topics: ['other'], share_high: 0.7 }))).toBe(
      'admin_dash.action_general',
    );
  });

  it('monitors when resistance is low and no concern is flagged', () => {
    expect(suggestAction(district({ top_topics: ['other'], share_high: 0.1 }))).toBe(
      'admin_dash.action_monitor',
    );
  });
});
