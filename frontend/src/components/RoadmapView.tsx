import React from 'react';
import { useTranslation } from 'react-i18next';
import type { RoadmapResult } from '../api/client';
import { SourceBadge } from './SourceBadge';

const STEP_LABEL: Record<string, string> = {
  eligibility: 'roadmap.eligibility',
  course: 'roadmap.course',
  centres: 'roadmap.centres',
  certification: 'roadmap.certification',
  placement: 'roadmap.placement',
};

const STEP_ICON: Record<string, string> = {
  eligibility: '🎓',
  course: '📘',
  centres: '📍',
  certification: '📜',
  placement: '💼',
};

interface RoadmapViewProps {
  roadmap: RoadmapResult | null;
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({ roadmap }) => {
  const { t } = useTranslation();

  if (!roadmap) {
    return <div className="card text-textSecondary">{t('common.loading')}</div>;
  }

  const mapQuery = encodeURIComponent(`${roadmap.occupation_name} training centre ${roadmap.district || ''}`);
  const mapUrl = `https://www.google.com/maps/search/?api=1&query=${mapQuery}`;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-bold text-xl">{t('roadmap.title', { career: roadmap.occupation_name })}</h3>
        <SourceBadge isDemo={roadmap.is_demo} />
      </div>
      {roadmap.expected && <p className="text-base text-textSecondary mb-4">{roadmap.expected}</p>}

      <ol className="relative border-l-2 border-gray-200 ml-3 space-y-5">
        {roadmap.steps.map((s) => (
          <li key={s.step} className="ml-6">
            <span className="absolute -left-3 flex items-center justify-center w-6 h-6 rounded-full bg-accent-light text-sm">
              {STEP_ICON[s.type] || '•'}
            </span>
            <div className="font-semibold text-base">{STEP_LABEL[s.type] ? t(STEP_LABEL[s.type]) : s.type}</div>
            <p className="text-textSecondary text-base">{s.detail}</p>
            {s.type === 'centres' && (
              <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-1 text-accent underline text-base"
              >
                {t('roadmap.map_link')}
              </a>
            )}
          </li>
        ))}
      </ol>

      {roadmap.is_demo && (
        <p className="mt-4 text-sm text-textSecondary">{t('roadmap.demo_note')}</p>
      )}
    </div>
  );
};
