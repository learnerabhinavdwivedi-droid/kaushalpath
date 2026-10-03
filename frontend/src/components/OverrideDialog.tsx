import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { RecommendationRow } from '../api/client';

interface OverrideDialogProps {
  recommendations: RecommendationRow[];
  submitting: boolean;
  onClose: () => void;
  onSubmit: (occupationId: number, note: string) => void;
}

/**
 * Counsellor override dialog (Phase 8). The reason note is REQUIRED — every
 * override is audit-logged and the whole point of the trail is explainability.
 */
export const OverrideDialog: React.FC<OverrideDialogProps> = ({
  recommendations,
  submitting,
  onClose,
  onSubmit,
}) => {
  const { t } = useTranslation();
  const options = recommendations.length > 0 ? recommendations : [];
  const [occupationId, setOccupationId] = useState<number | ''>('');
  const [note, setNote] = useState('');

  const valid = occupationId !== '' && note.trim().length > 0;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" role="dialog" aria-modal="true">
      <div className="card w-full max-w-md space-y-4 bg-white">
        <div className="flex justify-between items-center">
          <h3 className="text-xl font-bold text-accent">{t('override.title')}</h3>
          <button onClick={onClose} aria-label={t('common.cancel')} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-sm text-textSecondary">{t('override.hint')}</p>

        <div>
          <label htmlFor="override-occ" className="block font-medium mb-1">{t('override.occupation')}</label>
          <select
            id="override-occ"
            className="input-field"
            value={occupationId}
            onChange={(e) => setOccupationId(e.target.value === '' ? '' : Number(e.target.value))}
          >
            <option value="">{t('override.pick_occupation')}</option>
            {options.map((r) => (
              <option key={r.occupation_id} value={r.occupation_id}>
                {r.occupation_name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="override-note" className="block font-medium mb-1">
            {t('override.reason')} <span className="text-red-500">*</span>
          </label>
          <textarea
            id="override-note"
            className="input-field min-h-[96px]"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={t('override.reason_placeholder')}
          />
          {!valid && note.trim().length === 0 && (
            <p className="text-xs text-textSecondary mt-1">{t('override.reason_required')}</p>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <button className="btn-secondary" onClick={onClose}>
            {t('common.cancel')}
          </button>
          <button
            className="btn-primary disabled:opacity-50"
            disabled={!valid || submitting}
            onClick={() => valid && onSubmit(occupationId as number, note.trim())}
          >
            {submitting ? t('common.loading') : t('override.submit')}
          </button>
        </div>
      </div>
    </div>
  );
};
