import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useRoute } from 'wouter';
import {
  CompareResponse,
  ConsensusResult,
  MeOut,
  ObjectionSentiment,
  ObjectionTopic,
  RoadmapResult,
  RoomSnapshot,
  WeightsInput,
  castVote,
  compareOccupations,
  escalateRoom,
  getConsensus,
  getMe,
  getRoadmap,
  getRoom,
  recordObjection,
  updateWeights,
} from '../api/client';
import { useAuthStore, useResultsStore } from '../store/useStore';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { WeightsPanel } from '../components/WeightsPanel';
import { CompareView } from '../components/CompareView';
import { VoteView } from '../components/VoteView';
import { ConsensusView } from '../components/ConsensusView';
import { RoadmapView } from '../components/RoadmapView';
import { ShareBar } from '../components/ShareBar';
import { AskBox } from '../components/AskBox';

type Tab = 'compare' | 'weights' | 'vote' | 'consensus' | 'roadmap';

const TABS: { id: Tab; label: string }[] = [
  { id: 'compare', label: 'room.tab_compare' },
  { id: 'weights', label: 'room.tab_weights' },
  { id: 'vote', label: 'room.tab_vote' },
  { id: 'consensus', label: 'room.tab_consensus' },
  { id: 'roadmap', label: 'room.tab_roadmap' },
];

export const RoomHomePage: React.FC = () => {
  const { t } = useTranslation();
  const [match, params] = useRoute('/room/:code');
  const [, setLocation] = useLocation();
  const token = useAuthStore((s) => s.token);
  const recommendations = useResultsStore((s) => s.recommendations);

  const code = match ? params?.code : undefined;

  const [me, setMe] = useState<MeOut | null>(null);
  const [snapshot, setSnapshot] = useState<RoomSnapshot | null>(null);
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [consensus, setConsensus] = useState<ConsensusResult | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResult | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [tab, setTab] = useState<Tab>('compare');
  const [error, setError] = useState('');

  const candidates = (recommendations || [])
    .map((r: any) => ({ id: r.occupation.id as number, name: r.occupation.title as string }));

  const load = useCallback(async () => {
    if (!code) return;
    try {
      const snap = await getRoom(code);
      setSnapshot(snap);
      const cons = await getConsensus(code);
      setConsensus(cons);
      if (selectedIds.length) {
        const cmp = await compareOccupations(code, selectedIds);
        setComparison(cmp);
      }
    } catch (e: any) {
      setError(e.message || t('common.error'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, selectedIds]);

  // Boot: resolve identity, seed candidate selection from the student's results.
  useEffect(() => {
    if (!token) {
      setLocation('/login');
      return;
    }
    if (!match) return;
    const boot = async () => {
      try {
        const who = await getMe();
        setMe(who);
        const ids = candidates.slice(0, 3).map((c) => c.id);
        setSelectedIds(ids);
      } catch (e: any) {
        setError(e.message || t('common.error'));
      }
    };
    boot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, match]);

  // (Re)load whenever the room code or the selection changes.
  useEffect(() => {
    if (me && code) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me, code, selectedIds]);

  // Real-time-ish: poll the shared state every few seconds.
  useEffect(() => {
    if (!me || !code) return;
    const id = setInterval(() => load(), 6000);
    return () => clearInterval(id);
  }, [me, code, load]);

  // Roadmap loads lazily for the first selected option.
  useEffect(() => {
    if (tab === 'roadmap' && selectedIds[0] != null && me) {
      getRoadmap(selectedIds[0])
        .then(setRoadmap)
        .catch((e) => setError(e.message));
    }
  }, [tab, selectedIds, me]);

  if (!match) return null;

  const roleLabel = (userId: number): string => {
    if (me && userId === me.user_id) return t('weights.you');
    const m = snapshot?.members.find((x) => x.user_id === userId);
    return m ? `${t(`room.member_${m.role}`)} #${userId}` : `#${userId}`;
  };

  const myVotes: Record<number, number> = {};
  if (me && snapshot) {
    for (const v of snapshot.votes) {
      if (v.user_id === me.user_id) myVotes[v.occupation_id] = v.score;
    }
  }

  const topChoiceName =
    comparison?.results[0]?.occupation_name ||
    candidates.find((c) => c.id === consensus?.ranking[0]?.occupation_id)?.name ||
    '';

  const handleSaveWeights = async (w: WeightsInput) => {
    if (!code) return;
    await updateWeights(code, w);
    await load();
  };

  const handleVote = async (occId: number, score: number) => {
    if (!code) return;
    await castVote(code, occId, score);
    await load();
  };

  const handleObjection = async (
    topic: ObjectionTopic,
    sentiment: ObjectionSentiment,
    occupationId?: number | null
  ) => {
    if (!code) return;
    await recordObjection(code, { topic, sentiment, occupation_id: occupationId ?? null });
    await load();
  };

  const handleEscalate = async () => {
    if (!code) return;
    try {
      await escalateRoom(code, t('room.escalate'), selectedIds[0] ?? null);
      await load();
    } catch (e: any) {
      setError(e.message || t('common.error'));
    }
  };

  const toggleCandidate = (id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 3) return prev; // up to 3 side by side
      return [...prev, id];
    });
  };

  const isCounsellor = me?.role === 'counsellor';

  return (
    <div className="min-h-screen bg-background p-4 max-w-2xl mx-auto pb-24">
      <div className="flex items-center justify-between py-2 mb-2 print-header">
        <h1 className="text-2xl font-bold text-accent">{t('room.title')}</h1>
        <LanguageSwitcher />
      </div>

      <div className="card mb-4 no-print flex items-center justify-between">
        <div>
          <span className="text-sm text-textSecondary">{t('room.room_label')}: </span>
          <span className="font-mono font-bold text-lg">{code}</span>
        </div>
        <button onClick={() => load()} className="btn-secondary">
          {t('room.refresh')}
        </button>
      </div>

      {isCounsellor && (
        <div className="card mb-4 bg-gray-50">
          <p className="font-semibold">{t('room.counsellor_mode')}</p>
          <div className="mt-2 space-y-2">
            <p className="text-sm text-textSecondary">{t('room.suggest_override')}</p>
            <button onClick={handleEscalate} className="btn-primary">
              {t('room.escalate')}
            </button>
          </div>
        </div>
      )}

      {error && <p className="text-error mb-4">{error}</p>}

      {/* Candidate picker */}
      <div className="card mb-4 no-print">
        <p className="font-semibold mb-2">{t('room.select_careers')}</p>
        {candidates.length === 0 ? (
          <p className="text-textSecondary">{t('room.no_candidates')}</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {candidates.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-base">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(c.id)}
                  onChange={() => toggleCandidate(c.id)}
                />
                {c.name}
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto no-print">
        {TABS.map((x) => (
          <button
            key={x.id}
            onClick={() => setTab(x.id)}
            className={`px-4 py-2 rounded-lg font-bold whitespace-nowrap min-h-touch ${
              tab === x.id ? 'bg-accent text-white' : 'bg-white border border-gray-200'
            }`}
          >
            {t(x.label)}
          </button>
        ))}
      </div>

      {tab === 'compare' && (
        <CompareView comparison={comparison} weights={snapshot?.weights ?? []} isDemo />
      )}

      {tab === 'weights' && snapshot && me && (
        <WeightsPanel
          weights={snapshot.weights}
          currentUserId={me.user_id}
          labelFor={roleLabel}
          onSave={handleSaveWeights}
        />
      )}

      {tab === 'vote' && comparison && (
        <VoteView
          occupations={comparison.results.map((r) => ({ id: r.occupation_id, name: r.occupation_name }))}
          myVotes={myVotes}
          onVote={handleVote}
        />
      )}

      {tab === 'consensus' && (
        <ConsensusView
          consensus={consensus}
          comparison={comparison}
          weights={snapshot?.weights ?? []}
          currentUserId={me?.user_id ?? null}
        />
      )}

      {tab === 'roadmap' && <RoadmapView roadmap={roadmap} />}

      {/* Deterministic objection handler (records topic+sentiment) */}
      {topChoiceName && (
        <div className="mt-6">
          <AskBox
            careerTitle={topChoiceName}
            occupationId={selectedIds[0] ?? null}
            onObjection={handleObjection}
          />
        </div>
      )}

      {topChoiceName && <div className="mt-4"><ShareBar choiceName={topChoiceName} /></div>}
    </div>
  );
};
