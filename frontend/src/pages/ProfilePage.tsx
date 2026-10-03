import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore, useProfileStore } from '../store/useStore';
import { useLocation } from 'wouter';
import { getMe, saveConstraints } from '../api/client';

function budgetToBand(budget: number): string {
  if (budget <= 20000) return 'low';
  if (budget <= 60000) return 'mid';
  return 'high';
}

export const ProfilePage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const profile = useProfileStore();
  const { studentId, setStudentId } = useAuthStore();
  const [, setLocation] = useLocation();

  const [eduLevel, setEduLevel] = useState(profile.edu_level || '10th');
  const [district, setDistrict] = useState(profile.district || '');
  const [stateName, setStateName] = useState(profile.state || 'Maharashtra');
  const [budget, setBudget] = useState(profile.budget || 50000);
  const [duration, setDuration] = useState(profile.duration || 12);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let sid = studentId;
      if (sid == null) {
        const me = await getMe();
        sid = me.student_id;
        setStudentId(me.student_id);
      }
      if (sid == null) throw new Error(t('common.error'));

      profile.setProfile({
        edu_level: eduLevel,
        district,
        state: stateName,
        budget,
        duration,
      });

      await saveConstraints(sid, {
        edu_level: eduLevel,
        district,
        state: stateName,
        budget_band: budgetToBand(budget),
        income_band: profile.income_band || null,
        relocate_ok: false,
        language: i18n.language,
        max_duration_months: duration,
      });

      setLocation('/assessment');
    } catch (err: any) {
      setError(err.message || t('common.error'));
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-6 max-w-md mx-auto pt-12">
      <h2 className="text-3xl font-bold mb-8 text-accent">{t('profile.title')}</h2>

      {error && <div className="bg-red-100 text-red-900 p-4 rounded-lg mb-6">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="edu_level" className="block text-lg font-medium mb-2">{t('profile.edu_level')}</label>
          <select id="edu_level" className="input-field" value={eduLevel} onChange={e => setEduLevel(e.target.value)}>
            <option value="10th">10th Pass</option>
            <option value="12th">12th Pass</option>
            <option value="ITI">ITI</option>
          </select>
        </div>

        <div>
          <label htmlFor="district" className="block text-lg font-medium mb-2">{t('profile.district')}</label>
          <input
            id="district"
            type="text"
            required
            className="input-field"
            value={district}
            onChange={e => setDistrict(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="state" className="block text-lg font-medium mb-2">{t('profile.state')}</label>
          <input
            id="state"
            type="text"
            required
            className="input-field"
            value={stateName}
            onChange={e => setStateName(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="budget" className="block text-lg font-medium mb-2">{t('profile.budget')}</label>
          <input
            id="budget"
            type="number"
            className="input-field"
            value={budget}
            onChange={e => setBudget(Number(e.target.value))}
          />
        </div>

        <div>
          <label htmlFor="duration" className="block text-lg font-medium mb-2">{t('profile.duration')}</label>
          <input
            id="duration"
            type="number"
            className="input-field"
            value={duration}
            onChange={e => setDuration(Number(e.target.value))}
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full mt-8">
          {loading ? t('common.loading') : t('common.next')}
        </button>
      </form>
    </div>
  );
};
