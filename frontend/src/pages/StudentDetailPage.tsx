import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useRoute } from 'wouter';
import { StudentDetail, getStudentDetail, submitOverride } from '../api/client';
import { ReasonChip } from '../components/ReasonChip';
import { SourceBadge } from '../components/SourceBadge';
import { OverrideDialog } from '../components/OverrideDialog';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

export const StudentDetailPage: React.FC = () => {
  const { t } = useTranslation();
  const [match, params] = useRoute('/counsellor/students/:id');
  const id = match ? Number(params?.id) : NaN;

  const [detail, setDetail] = useState<StudentDetail | null>(null);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    try {
      setDetail(await getStudentDetail(id));
    } catch (e: any) {
      setError(e.message || t('common.error'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const applyOverride = async (occupationId: number, note: string) => {
    setSubmitting(true);
    try {
      await submitOverride(id, occupationId, note);
      setDialogOpen(false);
      await load(); // override list + audit refresh from the server
    } catch (e: any) {
      setError(e.message || t('common.error'));
    } finally {
      setSubmitting(false);
    }
  };

  if (error && !detail) return <p className="p-8 text-red-600">{error}</p>;
  if (!detail) return <p className="p-8 text-textSecondary">{t('common.loading')}</p>;

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="staff" />

      <div className="relative z-10 p-4 max-w-3xl mx-auto space-y-4 min-h-screen">
      <div className="flex justify-between items-center py-2">
        <h1 className="text-2xl font-bold text-accent">
          {t('student.title')} #{detail.student_id}
        </h1>
        <button className="btn-primary" onClick={() => setDialogOpen(true)}>
          {t('student.override_button')}
        </button>
      </div>
      {error && <p className="text-red-600">{error}</p>}

      <div className="card">
        <h2 className="font-bold text-lg mb-2">{t('student.profile')}</h2>
        <p className="text-textSecondary">
          {detail.district}, {detail.state} · {detail.edu_level} · {detail.language} ·{' '}
          {t('student.budget')}: {detail.budget_band}
        </p>
        {detail.assessment ? (
          <div className="mt-3 text-sm">
            <span className="font-bold">{t('student.assessment')}: </span>
            {detail.assessment.status} · {detail.assessment.items_answered} {t('student.items')} ·{' '}
            {t('student.confidence')} {(detail.assessment.confidence * 100).toFixed(0)}%
            <div className="mt-2 grid grid-cols-3 md:grid-cols-6 gap-2">
              {Object.entries(detail.assessment.riasec).map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded p-2 text-center">
                  <div className="font-bold text-accent">{k}</div>
                  <div className="text-textSecondary">{v.toFixed(1)}</div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-amber-600 mt-2 text-sm">{t('student.no_assessment')}</p>
        )}
      </div>

      <div className="card">
        <h2 className="font-bold text-lg mb-2">{t('student.recommendations')}</h2>
        {detail.recommendations.length === 0 ? (
          <p className="text-textSecondary">{t('student.no_recs')}</p>
        ) : (
          <ol className="space-y-3">
            {detail.recommendations.slice(0, 3).map((r) => (
              <li key={`${r.rank}-${r.occupation_id}`} className="border-b border-gray-100 pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold">{r.rank}.</span>
                  <span className="font-bold text-accent">{r.occupation_name}</span>
                  <SourceBadge isDemo={r.is_demo} />
                  <span className="text-xs text-textSecondary ml-auto">{r.score.toFixed(2)}</span>
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {r.reasons.slice(0, 3).map((x, i) => (
                    <ReasonChip key={i} reason={{ ...x, type: x.type ?? ('positive' as const) }} />
                  ))}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="card">
        <h2 className="font-bold text-lg mb-2">{t('student.room')}</h2>
        {detail.room ? (
          <p className="text-textSecondary">
            {t('student.room_code')}: <span className="font-mono font-bold">{detail.room.code}</span>{' '}
            · {detail.room.members} {t('student.members')} · {detail.room.votes}{' '}
            {t('student.votes')} · {detail.room.objections} {t('student.objections')} ·{' '}
            {detail.room.consensus_reached ? t('student.consensus_yes') : t('student.consensus_no')}
          </p>
        ) : (
          <p className="text-textSecondary">{t('student.no_room')}</p>
        )}
      </div>

      <div className="card">
        <h2 className="font-bold text-lg mb-2">{t('student.overrides')}</h2>
        {detail.overrides.length === 0 ? (
          <p className="text-textSecondary">{t('student.no_overrides')}</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {detail.overrides.map((o, i) => (
              <li key={i} className="bg-gray-50 rounded p-2">
                <span className="font-bold text-accent">{o.occupation_name}</span>
                <span className="ml-2 text-textSecondary">{o.created_at}</span>
                <p className="mt-1">{o.note}</p>
              </li>
            ))}
          </ul>
        )}
      </div>

      {dialogOpen && (
        <OverrideDialog
          recommendations={detail.recommendations}
          submitting={submitting}
          onClose={() => setDialogOpen(false)}
          onSubmit={applyOverride}
        />
      )}
      </div>
    </div>
  );
};
