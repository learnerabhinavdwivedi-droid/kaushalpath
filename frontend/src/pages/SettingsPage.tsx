import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuthStore, useAssessmentStore, useProfileStore, useResultsStore } from '../store/useStore';
import { apiRequest } from '../api/client';
import { useLocation } from 'wouter';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { ArrowLeft, Trash2, LogOut } from 'lucide-react';
import { BackgroundDoodles } from '../components/BackgroundDoodles';
import {
  FONT_SIZES,
  getFontSize,
  getHighContrast,
  setFontSize,
  setHighContrast,
  type FontSize,
} from '../lib/displayPrefs';

export const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const logout = useAuthStore(state => state.logout);
  const resetAssessment = useAssessmentStore(state => state.resetAssessment);
  const setProfile = useProfileStore(state => state.setProfile);
  const setRecommendations = useResultsStore(state => state.setRecommendations);
  // Phase 17: display prefs (font size + high contrast), persisted in localStorage.
  const [fontSize, setFont] = React.useState<FontSize>(getFontSize());
  const [contrast, setContrast] = React.useState<boolean>(getHighContrast());

  const handleDeleteData = async () => {
    if (window.confirm(t('settings.delete_confirm'))) {
      try {
        await apiRequest('/auth/students/me', { method: 'DELETE' });
        // Clear local state
        resetAssessment();
        setRecommendations([]);
        setProfile({ edu_level: '', district: '', budget: 0, duration: 0 });
        logout();
        setLocation('/');
      } catch (e) {
        console.error("Delete failed", e);
      }
    }
  };

  const handleLogout = () => {
    logout();
    setLocation('/');
  };

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="account" />

      <div className="relative z-10 p-4 max-w-md mx-auto">
      <div className="flex items-center gap-4 py-4 mb-6">
        <button onClick={() => window.history.back()} className="p-2" aria-label="Back">
          <ArrowLeft className="w-8 h-8 text-accent" />
        </button>
        <h2 className="text-2xl font-bold">{t('settings.title')}</h2>
      </div>

      <div className="space-y-6">
        <div className="card flex justify-between items-center">
          <span className="text-xl font-medium">{t('settings.language')}</span>
          <LanguageSwitcher />
        </div>

        {/* Phase 17: text size + high contrast for low-vision / low-literacy. */}
        <div className="card space-y-3">
          <span className="text-xl font-medium">{t('settings.text_size')}</span>
          <div className="flex gap-2" role="group" aria-label={t('settings.text_size')}>
            {FONT_SIZES.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={fontSize === s}
                onClick={() => { setFont(s); setFontSize(s); }}
                className={`min-h-[44px] flex-1 rounded-pill border-2 px-3 text-lg font-bold ${
                  fontSize === s ? 'border-accent bg-accent-light' : 'border-gray-200'
                }`}
              >
                {t(`settings.font_${s}`)}
              </button>
            ))}
          </div>
          <label className="flex items-center justify-between text-xl font-medium">
            {t('settings.high_contrast')}
            <input
              type="checkbox"
              className="h-6 w-6"
              checked={contrast}
              onChange={(e) => { setContrast(e.target.checked); setHighContrast(e.target.checked); }}
            />
          </label>
        </div>

        <button 
          onClick={handleLogout}
          className="w-full card flex items-center gap-4 text-xl font-medium text-textSecondary hover:bg-gray-50 text-left"
        >
          <LogOut className="w-6 h-6" />
          {t('auth.login')} / Logout
        </button>

        <button 
          onClick={handleDeleteData}
          className="w-full card flex items-center gap-4 text-xl font-medium text-red-600 hover:bg-red-50 text-left border-red-200"
        >
          <Trash2 className="w-6 h-6" />
          {t('settings.delete_account')}
        </button>
      </div>
      </div>
    </div>
  );
};
