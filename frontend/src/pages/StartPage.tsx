import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'wouter';
import { Globe, User, Users, Wallet, ShieldAlert, Home, ArrowRight, ArrowLeft } from 'lucide-react';
import { LanguageSwitcher } from '../components/LanguageSwitcher';

/**
 * Phase 17 — icon-first onboarding for low-literacy parents. At most three taps
 * (language -> who is speaking -> a concern) before the shared chat, each step a
 * large tappable icon rather than a wall of text. Purely navigational: a concern
 * routes onward to /talk (carried as a ?concern= query for a future composer
 * pre-seed; /talk currently ignores the param — see ACCESSIBILITY_EVIDENCE.md).
 */
const CONCERNS = [
  { key: 'income', Icon: Wallet },
  { key: 'safety', Icon: ShieldAlert },
  { key: 'distance', Icon: Home },
] as const;

export const StartPage: React.FC = () => {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const [step, setStep] = useState(0);

  const goTalk = (concern?: string) =>
    setLocation(concern ? `/talk?concern=${concern}` : '/talk');

  const Option = ({ label, Icon, onClick }: { label: string; Icon: React.ElementType; onClick: () => void }) => (
    <button
      type="button"
      onClick={onClick}
      className="card flex w-full items-center gap-4 text-left text-xl font-medium hover:border-accent"
    >
      <Icon className="h-10 w-10 shrink-0 text-accent" aria-hidden="true" />
      {label}
    </button>
  );

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      {/* High Quality HD Doodles */}
      <div className="hidden lg:block absolute inset-0 pointer-events-none flex items-center justify-between px-[5%]">
        <img src="/doodles/doodle_learning.jpg" alt="" className="w-[350px] h-[350px] object-contain mix-blend-multiply opacity-90 transition-transform duration-1000 hover:scale-105" />
        <img src="/doodles/doodle_success.jpg" alt="" className="w-[400px] h-[400px] object-contain mix-blend-multiply opacity-90 transition-transform duration-1000 hover:scale-105" />
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen max-w-md flex-col gap-4 p-5">
      <header className="py-2">
        <p className="text-sm text-textSecondary">{t('start.step', { current: step + 1, total: 3 })}</p>
        <h1 className="text-2xl font-bold text-accent">{t('start.title')}</h1>
      </header>

      {step === 0 && (
        <div className="space-y-3" role="group" aria-label={t('start.q_lang')}>
          <h2 className="text-lg">{t('start.q_lang')}</h2>
          <LanguageSwitcher />
          <button type="button" className="btn-primary mt-2 flex items-center gap-2" onClick={() => setStep(1)}>
            {t('common.next')} <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3" role="group" aria-label={t('start.q_who')}>
          <h2 className="text-lg">{t('start.q_who')}</h2>
          <Option label={t('start.who_parent')} Icon={Users} onClick={() => setStep(2)} />
          <Option label={t('start.who_student')} Icon={User} onClick={() => goTalk()} />
          <BackButton onClick={() => setStep(0)} />
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3" role="group" aria-label={t('start.q_concern')}>
          <h2 className="text-lg">{t('start.q_concern')}</h2>
          {CONCERNS.map(({ key, Icon }) => (
            <Option key={key} label={t(`start.concern_${key}`)} Icon={Icon} onClick={() => goTalk(key)} />
          ))}
          <button type="button" className="card flex w-full items-center gap-2 text-left text-lg" onClick={() => goTalk()}>
            <Globe className="h-8 w-8 text-accent" aria-hidden="true" />
            {t('start.concern_skip')}
          </button>
          <BackButton onClick={() => setStep(1)} />
        </div>
      )}
    </div>
    </div>
  );
};

const BackButton: React.FC<{ onClick: () => void }> = ({ onClick }) => {
  const { t } = useTranslation();
  return (
    <button type="button" onClick={onClick} className="flex items-center gap-1 text-textSecondary hover:text-accent">
      <ArrowLeft className="h-4 w-4" aria-hidden="true" /> {t('common.back')}
    </button>
  );
};
