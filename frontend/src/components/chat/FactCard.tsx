import React from 'react';
import { useTranslation } from 'react-i18next';
import type { GroundedFact } from '../../api/client';
import { SourceBadge } from '../SourceBadge';

/**
 * One grounded number behind an assistant reply (PS non-negotiable #1): the
 * value always arrives with its source / source_year / is_demo straight from
 * the database — the UI never invents or rounds figures.
 */
export const FactCard: React.FC<{ fact: GroundedFact }> = ({ fact }) => {
  const { t } = useTranslation();
  const value =
    typeof fact.value === 'number'
      ? fact.value.toLocaleString('en-IN', { maximumFractionDigits: 2 })
      : String(fact.value);

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
      <p className="text-sm font-semibold text-textSecondary">{fact.label}</p>
      <div className="flex items-baseline gap-1">
        <p className="text-lg font-bold text-accent">{value}</p>
        {fact.unit ? <span className="text-sm font-medium text-textSecondary">{fact.unit}</span> : null}
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        {fact.source ? (
          <span className="text-xs text-gray-500">
            {t('chat.fact_source', { source: fact.source, year: fact.source_year ?? '—' })}
          </span>
        ) : null}
        <SourceBadge isDemo={fact.is_demo} />
      </div>
    </div>
  );
};
