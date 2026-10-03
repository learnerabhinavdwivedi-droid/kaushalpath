import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useProfileStore } from '../store/useStore';
import { useLocation } from 'wouter';

export const ProfilePage: React.FC = () => {
  const { t } = useTranslation();
  const profile = useProfileStore();
  const [, setLocation] = useLocation();

  const [eduLevel, setEduLevel] = useState(profile.edu_level || '10th');
  const [district, setDistrict] = useState(profile.district || '');
  const [budget, setBudget] = useState(profile.budget || 50000);
  const [duration, setDuration] = useState(profile.duration || 12);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    profile.setProfile({
      edu_level: eduLevel,
      district,
      budget,
      duration
    });
    // Normally you'd POST this to backend API
    setLocation('/assessment');
  };

  return (
    <div className="min-h-screen p-6 max-w-md mx-auto pt-12">
      <h2 className="text-3xl font-bold mb-8 text-accent">{t('profile.title')}</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-lg font-medium mb-2">{t('profile.edu_level')}</label>
          <select className="input-field" value={eduLevel} onChange={e => setEduLevel(e.target.value)}>
            <option value="10th">10th Pass</option>
            <option value="12th">12th Pass</option>
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
          <label className="block text-lg font-medium mb-2">{t('profile.budget')}</label>
          <input 
            type="number" 
            className="input-field" 
            value={budget}
            onChange={e => setBudget(Number(e.target.value))}
          />
        </div>

        <div>
          <label className="block text-lg font-medium mb-2">{t('profile.duration')}</label>
          <input 
            type="number" 
            className="input-field" 
            value={duration}
            onChange={e => setDuration(Number(e.target.value))}
          />
        </div>

        <button type="submit" className="btn-primary w-full mt-8">
          {t('common.next')}
        </button>
      </form>
    </div>
  );
};
