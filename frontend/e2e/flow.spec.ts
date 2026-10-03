import { test, expect } from '@playwright/test';

test('register -> assessment -> results flow', async ({ page }) => {
  // Mock the auth endpoint
  await page.route('**/auth/register', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ access_token: 'fake-jwt-token' })
  }));
  // Mock assessment completion
  let questionCount = 0;
  await page.route('**/assessment/next-question', async route => {
    questionCount++;
    if (questionCount > 1) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ is_complete: true })
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_complete: false,
          question: { id: 'q1', text: 'Do you like fixing things?', options: [{ id: 'o1', label: 'Option 1' }] }
        })
      });
    }
  });
  // Mock recommend endpoint
  await page.route('**/recommend', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      recommendations: [{
        occupation: { id: 'occ1', title: 'Electrician', description: 'Fix wires', typical_duration_months: 6 },
        reasons: [{ description: 'Likes fixing', type: 'positive' }]
      }]
    })
  }));

  // 1. Landing
  await page.goto('/');
  await page.evaluate(() => window.localStorage.clear());
  await page.goto('/');
  await expect(page.locator('text=Welcome to KaushalPath')).toBeVisible();
  await page.click('text=Get Started');

  // 2. Register
  await expect(page.getByRole('heading', { name: 'Register' })).toBeVisible();
  const email = `test_${Date.now()}@example.com`;
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill('password123');
  // Check consent
  await page.check('input[type="checkbox"]');
  await page.getByRole('button', { name: 'Register' }).click();

  // Wait for Profile
  await expect(page.getByRole('heading', { name: 'Your Profile' })).toBeVisible({ timeout: 10000 });
  await page.getByLabel('District').fill('Pune');
  await page.getByRole('button', { name: 'Next' }).click();

  // 3. Assessment
  await expect(page.getByText('Do you like fixing things?')).toBeVisible();
});
