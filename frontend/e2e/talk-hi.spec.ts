import { test, expect } from '@playwright/test';

// Phase 15 acceptance flow, entirely in Hindi with the backend mocked:
// parent joins by room code (no account) -> switches to हिन्दी -> speaks
// (mocked SpeechRecognition) an income objection -> sees the grounded fact
// card with the Demo badge -> taps "किसी इंसान से बात करें" -> the live
// status chip shows Open.
const OBJECTION = 'क्या इससे पर्याप्त कमाई होगी?';
const REPLY = 'वाराणसी में इस करियर का माध्य वेतन डेटाबेस से आया आँकड़ा है।';
const FACT = {
  key: 'median_salary',
  label: 'माध्य मासिक वेतन',
  value: 19500,
  unit: '₹/माह',
  source: 'demo_synth_2026',
  source_year: 2026,
  is_demo: true,
};

const convWithTurns = (status: string) => ({
  id: 1,
  student_id: 3,
  room_id: 7,
  lang: 'hi',
  status,
  created_at: '2026-10-06T10:00:00',
  turns: [
    {
      id: 1, speaker: 'parent', text: OBJECTION, lang: 'hi', intent: 'object',
      topic: 'income', sentiment: 'negative', intensity: 0.6, facts_json: null,
      fallback_used: false, created_at: '2026-10-06T10:01:00',
    },
    {
      id: 2, speaker: 'assistant', text: REPLY, lang: 'hi', intent: 'inform',
      topic: 'income', sentiment: 'neutral', intensity: 0, facts_json: [FACT],
      fallback_used: false, created_at: '2026-10-06T10:01:02',
    },
  ],
});

test('parent guest joins by code and completes the Hindi chat + escalation flow', async ({ page }) => {
  // Voice-in works without Chrome: the Web Speech API is stubbed.
  await page.addInitScript((transcript) => {
    class FakeRecognition {
      lang = '';
      continuous = false;
      interimResults = false;
      onresult: ((e: unknown) => void) | null = null;
      onerror: ((e: unknown) => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        setTimeout(() => {
          this.onresult?.({ results: [[{ transcript }]] });
          this.onend?.();
        }, 150);
      }
      stop() {}
    }
    (window as unknown as { SpeechRecognition: unknown }).SpeechRecognition = FakeRecognition;
  }, OBJECTION);

  // --- Auth / room -----------------------------------------------------------
  await page.route('**/auth/guest', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'guest-jwt', token_type: 'bearer', room_code: 'ABC123', room_id: 7, student_id: 3, name: 'रमेश' }),
    })
  );
  await page.route('**/auth/me', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ user_id: 2, email: 'guest-x@guest.kaushalpath.invalid', role: 'parent', lang: 'hi', student_id: null }),
    })
  );
  await page.route('**/rooms/ABC123/consensus', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ranking: [], agreement_index: 0, next_step: '' }) })
  );
  await page.route('**/rooms/ABC123', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 'ABC123',
        room_id: 7,
        student_id: 3,
        members: [{ user_id: 1, role: 'student' }, { user_id: 2, role: 'parent' }],
        weights: [],
        votes: [],
        objections: [],
      }),
    })
  );

  // --- Conversation engine (mocked deterministic backend) --------------------
  await page.route('**/conversations', (r) =>
    r.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ ...convWithTurns('active'), turns: [] }),
    })
  );
  await page.route('**/conversations/1/turns', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ reply: REPLY, lang: 'hi', intent: 'inform', topic: 'income', facts: [FACT], followups: [], escalation_suggested: false, fallback_used: false }),
    })
  );
  await page.route('**/conversations/1/escalate', (r) =>
    r.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ id: 5, status: 'open', assigned_counsellor_id: null, in_pool: true, case_pack: null }),
    })
  );
  await page.route('**/conversations/1/escalation', (r) =>
    r.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 5, status: 'open', assigned_counsellor_id: null, in_pool: true, case_pack: null }),
    })
  );
  // Registered after the specific subresource routes so polling gets the thread.
  await page.route('**/conversations/1', (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(convWithTurns('active')) })
  );

  // 1. Guest join with just the room code and a name.
  await page.goto('/room/join');
  await page.fill('input.uppercase', 'abc123');
  await page.getByLabel('Your name').fill('रमेश');
  await page.getByRole('button', { name: 'Join as family (no account)' }).click();

  // 2. Inside the room; flip the whole UI to हिन्दी.
  await expect(page.getByText('ABC123')).toBeVisible({ timeout: 10000 });
  await page.getByRole('button', { name: 'Toggle language' }).click();
  await page.getByRole('button', { name: 'बात करें' }).click();

  // 3. Speak the income objection (mocked recognition auto-sends it).
  await page.getByLabel('बोलकर सवाल पूछें').click();
  await expect(page.getByText(OBJECTION)).toBeVisible({ timeout: 10000 });

  // 4. Grounded fact card under the assistant reply, with the Demo badge.
  await expect(page.getByText(REPLY)).toBeVisible();
  await expect(page.getByText('19,500')).toBeVisible();
  await expect(page.getByText('₹/माह')).toBeVisible();
  await expect(page.getByText(/demo/i).first()).toBeVisible();

  // 5. One-tap human hand-off: phone/slot/language sheet, live Open status.
  await page.getByRole('button', { name: 'किसी इंसान से बात करें' }).click();
  await page.getByLabel('फ़ोन नंबर').fill('9876543210');
  await page.getByRole('button', { name: 'कॉल का अनुरोध भेजें' }).click();
  await expect(page.getByTestId('escalation-status')).toContainText('खुरा है', { timeout: 10000 });
});
