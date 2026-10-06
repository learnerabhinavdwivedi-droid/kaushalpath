import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react';
import axe from 'axe-core';
import type { ConversationOut } from '../../api/client';

/**
 * Phase 15 — ChatPanel state machine + a11y (vitest, fully offline: the api
 * client is mocked, so no network or LLM is touched; the deterministic
 * fallback engine on the backend is what the real client talks to).
 */

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'hi', changeLanguage: () => {} },
  }),
}));

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<object>('../../api/client');
  return {
    ...actual,
    createConversation: vi.fn(),
    getConversation: vi.fn(),
    sendTurn: vi.fn(),
    escalateConversation: vi.fn(),
    getConversationEscalation: vi.fn(),
  };
});

import {
  createConversation,
  escalateConversation,
  getConversation,
  sendTurn,
} from '../../api/client';
import { ChatPanel } from './ChatPanel';

const turn = (over: Record<string, unknown>) => ({
  id: 1,
  speaker: 'parent',
  text: 'क्या इससे पर्याप्त कमाई होगी?',
  lang: 'hi',
  intent: 'object',
  topic: 'income',
  sentiment: 'negative',
  intensity: 0.5,
  facts_json: null,
  fallback_used: false,
  created_at: '2026-10-06T10:00:00',
  ...over,
});

const CONVERSATION: ConversationOut = {
  id: 1,
  student_id: 1,
  room_id: null,
  lang: 'hi',
  status: 'active',
  created_at: '2026-10-06T10:00:00',
  turns: [
    turn({}),
    turn({
      id: 2,
      speaker: 'assistant',
      text: 'इस क्षेत्र में_median वेतन डेटाबेस से आता है।',
      intent: 'inform',
      sentiment: 'neutral',
      facts_json: [
        {
          key: 'median_salary',
          label: 'Median Monthly Salary',
          value: 19500,
          unit: 'INR/mo',
          source: 'demo_synth_2026',
          source_year: 2026,
          is_demo: true,
        },
      ],
    }),
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  // jsdom exposes no speechSynthesis by default; the panel must still render.
  (getConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(CONVERSATION);
});

afterEach(() => {
  cleanup();
  delete (window as unknown as { SpeechRecognition?: unknown }).SpeechRecognition;
  delete (window as unknown as { speechSynthesis?: unknown }).speechSynthesis;
});

describe('ChatPanel states', () => {
  it('renders loading, then the thread with a grounded fact card', async () => {
    let resolveBoot: (c: ConversationOut) => void = () => {};
    (createConversation as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise((r) => { resolveBoot = r; })
    );

    render(<ChatPanel studentId={1} />);
    expect(screen.getByRole('status')).toHaveTextContent('chat.loading');

    resolveBoot(CONVERSATION);
    expect(await screen.findByText('chat.parent_badge')).toBeInTheDocument();
    // The assistant bubble carries the DB-sourced fact card + demo badge.
    expect(screen.getByText('19,500')).toBeInTheDocument();
    expect(screen.getByText('chat.fact_source')).toBeInTheDocument();
    expect(screen.getByText('results.demo_badge')).toBeInTheDocument();
  });

  it('shows an error state with a retry that recovers', async () => {
    (createConversation as unknown as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new Error('kaboom'))
      .mockResolvedValueOnce(CONVERSATION);

    render(<ChatPanel studentId={1} />);
    expect(await screen.findByText('kaboom')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'chat.retry' }));
    expect(await screen.findByText('chat.assistant_badge')).toBeInTheDocument();
    expect(createConversation).toHaveBeenCalledTimes(2);
  });

  it('hides the mic and shows the typing hint when SpeechRecognition is missing', async () => {
    (createConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(CONVERSATION);
    render(<ChatPanel studentId={1} />);
    await screen.findByText('chat.parent_badge');

    expect(screen.queryByLabelText('chat.mic_start')).not.toBeInTheDocument();
    expect(screen.getByText('chat.typing_hint')).toBeInTheDocument();
  });

  it('renders the mic when the browser exposes SpeechRecognition', async () => {
    class FakeRecognition {
      lang = '';
      continuous = false;
      interimResults = false;
      onresult: ((e: unknown) => void) | null = null;
      onerror: ((e: unknown) => void) | null = null;
      onend: (() => void) | null = null;
      start() {}
      stop() {}
    }
    (window as unknown as { SpeechRecognition: unknown }).SpeechRecognition = FakeRecognition;
    (createConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(CONVERSATION);

    render(<ChatPanel studentId={1} />);
    await screen.findByText('chat.parent_badge');
    expect(screen.getByLabelText('chat.mic_start')).toBeInTheDocument();
  });

  it('tags the message with the chosen speaker (big Learner/Parent switch)', async () => {
    (createConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(CONVERSATION);
    (sendTurn as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      reply: 'ok', lang: 'hi', intent: 'ask', topic: 'income',
      facts: [], followups: [], escalation_suggested: false, fallback_used: false,
    });

    render(<ChatPanel studentId={1} />);
    await screen.findByText('chat.parent_badge');

    fireEvent.click(screen.getByRole('button', { name: /chat.speaker_parent/i }));
    fireEvent.change(screen.getByLabelText('chat.placeholder'), {
      target: { value: 'बेटी के लिए सुरक्षा?' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'chat.send' }));

    await waitFor(() => expect(sendTurn).toHaveBeenCalledTimes(1));
    expect(sendTurn).toHaveBeenCalledWith(1, {
      speaker: 'parent',
      text: 'बेटी के लिए सुरक्षा?',
      occupation_id: null,
      lang: 'hi',
    });
  });

  it('queues the turn offline instead of losing it', async () => {
    (createConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(CONVERSATION);
    (sendTurn as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('You are currently offline. Please check your connection.')
    );

    render(<ChatPanel studentId={1} />);
    await screen.findByText('chat.parent_badge');

    fireEvent.change(screen.getByLabelText('chat.placeholder'), { target: { value: 'hello' } });
    fireEvent.click(screen.getByRole('button', { name: 'chat.send' }));

    expect(await screen.findByRole('status')).toHaveTextContent('chat.queued');
    // Must not spin: exactly one attempt until the network actually returns.
    await waitFor(() => expect(sendTurn).toHaveBeenCalledTimes(1));
  });

  it('escalates through the sheet and shows the live Open status', async () => {
    (createConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(CONVERSATION);
    (escalateConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 5, status: 'open', assigned_counsellor_id: null, in_pool: true, case_pack: null,
    });

    render(<ChatPanel studentId={1} />);
    await screen.findByText('chat.parent_badge');

    fireEvent.click(screen.getByTestId('escalate-open'));
    fireEvent.click(screen.getByTestId('escalate-send'));

    expect(await screen.findByTestId('escalation-status')).toHaveTextContent('chat.status_open');
    expect(escalateConversation).toHaveBeenCalledWith(1, {
      reason: 'chat.escalate_reason',
      contact_phone: null,
      preferred_slot: 'morning',
      preferred_language: 'hi',
      channel: 'callback',
    });
  });

  it('has no detectable axe violations in the ready state', async () => {
    (createConversation as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(CONVERSATION);
    Object.defineProperty(window, 'speechSynthesis', {
      value: { speak: vi.fn(), cancel: vi.fn() },
      configurable: true,
    });

    const { container } = render(<ChatPanel studentId={1} />);
    await screen.findByText('chat.parent_badge');

    const results = await axe.run(container, {
      resultTypes: ['violations'],
      rules: { 'color-contrast': { enabled: false } },
    });
    if (results.violations.length) {
      const summary = results.violations
        .map((v) => `${v.id}: ${v.help} -> ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)
        .join('\n');
      throw new Error(`axe violations:\n${summary}`);
    }
    expect(results.violations).toEqual([]);
  });
});
