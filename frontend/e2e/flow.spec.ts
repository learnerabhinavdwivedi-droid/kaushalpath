import { test, expect } from '@playwright/test';

test('register -> profile -> assessment flow', async ({ page }) => {
  // Auth + identity.
  await page.route('**/auth/register', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ access_token: 'fake-jwt-token', token_type: 'bearer' })
  }));
  await page.route('**/auth/me', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ user_id: 1, email: 't@example.com', role: 'student', lang: 'en', student_id: 1 })
  }));

  // Constraint intake.
  await page.route('**/assessment/student**', route => route.fulfill({
    status: 201,
    contentType: 'application/json',
    body: JSON.stringify({})
  }));

  // Adaptive session: serve one interest item, then finish on answer.
  await page.route('**/assessment/session**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      assessment_id: 1,
      status: 'in_progress',
      done: false,
      items_answered: 0,
      confidence: 0.0,
      item: { id: 'q1', section: 'interest', text: 'Do you like fixing things?', scale: [1, 2, 3, 4, 5] }
    })
  }));
  await page.route('**/assessment/answer', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      assessment_id: 1, status: 'complete', done: true, items_answered: 1, confidence: 0.8, item: null
    })
  }));

  // Recommendations (backend shape; the client maps it into cards).
  await page.route('**/recommend', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      recommendations: [{
        rank: 1,
        occupation_id: 42,
        occupation_name: 'Electrician',
        course_id: 7,
        course_name: 'ITI Electrician',
        score: 0.82,
        reasons: [{ code: 'INTEREST_MATCH', description: 'Matches your hands-on interest', source: 'Assessment' }],
        is_demo: true
      }]
    })
  }));

  // 1. Landing
  await page.goto('/');
  await page.evaluate(() => window.localStorage.clear());
  await page.goto('/');
  await expect(page.getByText('Welcome to KaushalPath')).toBeVisible();
  await page.getByText('Get Started').click();

  // 2. Register
  await expect(page.getByRole('heading', { name: 'Register' })).toBeVisible();
  await page.getByLabel('Email').fill(`test_${Date.now()}@example.com`);
  await page.getByLabel('Password').fill('password123');
  await page.check('input[type="checkbox"]');
  await page.getByRole('button', { name: 'Register' }).click();

  // 3. Profile
  await expect(page.getByRole('heading', { name: 'Your Profile' })).toBeVisible({ timeout: 10000 });
  await page.getByLabel('District').fill('Pune');
  await page.getByLabel('State').fill('Maharashtra');
  await page.getByRole('button', { name: 'Next' }).click();

  // 4. Assessment serves the first item.
  await expect(page.getByText('Do you like fixing things?')).toBeVisible({ timeout: 10000 });
});
