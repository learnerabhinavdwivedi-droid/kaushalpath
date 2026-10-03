import { test, expect } from '@playwright/test';

// Full family-decision-room demo path (PHASE_7 acceptance):
// student result -> create room -> (parent joined) -> adjust weights -> vote ->
// consensus -> compare. Backend interactions are mocked to keep it hermetic.
test('family decision room: create -> weights -> vote -> consensus', async ({ page }) => {
  // Pretend a student already finished an assessment with one recommendation.
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'fake-jwt-token');
    window.localStorage.setItem(
      'auth-storage',
      JSON.stringify({ state: { token: 'fake-jwt-token', role: 'student', studentId: 1 }, version: 0 })
    );
    window.localStorage.setItem(
      'results-storage',
      JSON.stringify({
        state: {
          recommendations: [
            {
              occupation: { id: 42, title: 'Electrician', description: 'ITI Electrician', typical_duration_months: null },
              reasons: [{ code: 'INTEREST_MATCH', description: 'Hands-on', type: 'positive', source: 'Assessment' }],
              score: 0.82,
              is_demo: true,
            },
            {
              occupation: { id: 43, title: 'Carpenter', description: 'ITI Carpenter', typical_duration_months: null },
              reasons: [],
              score: 0.7,
              is_demo: true,
            },
          ],
        },
        version: 0,
      })
    );
  });

  await page.route('**/auth/me', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ user_id: 1, email: 's@e.com', role: 'student', lang: 'en', student_id: 1 }) })
  );
  await page.route('**/rooms', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 'ABC123', student_id: 1 }) })
  );
  await page.route('**/rooms/ABC123/weights', (r) => r.fulfill({ status: 200, body: JSON.stringify({ status: 'updated' }) }));
  await page.route('**/rooms/ABC123/vote', (r) => r.fulfill({ status: 200, body: JSON.stringify({ status: 'voted' }) }));
  await page.route('**/rooms/ABC123/objection', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 1, raised_by_user_id: 1, occupation_id: 42, topic: 'income', sentiment: 'concern' }) })
  );
  await page.route('**/rooms/ABC123/compare', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        results: [
          { occupation_id: 42, occupation_name: 'Electrician', criteria: { cost: 0.8, duration: 0.6, salary: 0.5, local_jobs: 0.7, distance: 0.9 }, member_totals: { '1': 0.7 }, family_score: 0.7, spread: 0 },
          { occupation_id: 43, occupation_name: 'Carpenter', criteria: { cost: 0.4, duration: 0.5, salary: 0.3, local_jobs: 0.2, distance: 0.3 }, member_totals: { '1': 0.4 }, family_score: 0.4, spread: 0 },
        ],
        disagreement: { occupation_id: null, criterion: null, detail: 'Not enough data to disagree.' },
      }),
    })
  );
  await page.route('**/rooms/ABC123/consensus', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ranking: [{ occupation_id: 42, avg_score: 4.5 }], agreement_index: 0.85, next_step: 'ready for roadmap' }) })
  );
  await page.route('**/rooms/ABC123', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 'ABC123',
        student_id: 1,
        members: [{ user_id: 1, role: 'student' }, { user_id: 2, role: 'parent' }],
        weights: [
          { user_id: 1, cost: 0.2, duration: 0.2, salary: 0.2, local_jobs: 0.2, distance: 0.2 },
          { user_id: 2, cost: 0.5, duration: 0.1, salary: 0.2, local_jobs: 0.1, distance: 0.1 },
        ],
        votes: [],
        objections: [],
      }),
    })
  );

  // 1. Create the room from the results page.
  await page.goto('/room/new');
  await page.getByRole('button', { name: 'Create room' }).click();

  // 2. Room home loads with the code and the two candidate careers.
  await expect(page.getByText('ABC123')).toBeVisible({ timeout: 10000 });
  await expect(page.getByText('Electrician').first()).toBeVisible();

  // 3. Compare tab shows both careers side by side.
  await expect(page.getByText('0.70').first()).toBeVisible();

  // 4. Weights tab: move a slider and save.
  await page.getByRole('button', { name: 'What matters' }).click();
  await page.getByRole('button', { name: 'Save my weights' }).click();

  // 5. Vote tab: rate the top option.
  await page.getByRole('button', { name: 'Vote' }).click();
  await page.getByRole('button', { name: '5' }).first().click();
  await page.getByRole('button', { name: 'Cast vote' }).first().click();

  // 6. Consensus tab: agreement meter + suggested choice.
  await page.getByRole('button', { name: 'Consensus' }).click();
  await expect(page.getByText('85%')).toBeVisible();
});
