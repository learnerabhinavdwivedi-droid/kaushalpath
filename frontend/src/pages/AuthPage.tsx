import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { apiRequest, getMe } from '../api/client';
import { useAuthStore } from '../store/useStore';
import { useLocation, Link } from 'wouter';
import { BackgroundDoodles } from '../components/BackgroundDoodles';

export const AuthPage: React.FC<{ mode: 'login' | 'register' }> = ({ mode }) => {
  const { t } = useTranslation();
  const setAuth = useAuthStore(state => state.setAuth);
  const [, setLocation] = useLocation();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let token: string;
      if (mode === 'register') {
        if (!consent) throw new Error(t('consent.description'));
        const res: any = await apiRequest('/auth/register', {
          method: 'POST',
          body: JSON.stringify({ email, password, role, give_consent: consent })
        });
        token = res.access_token;
      } else {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        const res: any = await apiRequest('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData.toString()
        });
        token = res.access_token;
      }
      // Resolve identity (role + student_id) from the backend before routing.
      localStorage.setItem('token', token);
      const me = await getMe();
      setAuth(token, me.role, me.student_id);
      const isStudent = me.role === 'student';
      setLocation(mode === 'register' && isStudent ? '/profile' : isStudent ? '/assessment' : '/results');
    } catch (err: any) {
      setError(err.message || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-page overflow-hidden">
      <BackgroundDoodles section="auth" />

      <div className="relative z-10 min-h-screen flex flex-col justify-center p-6 max-w-md mx-auto">
        <div className="card shadow-2xl bg-white/95 backdrop-blur-sm border-2 border-accent/10">
        <h2 className="text-3xl font-bold mb-6 text-center text-accent">
          {mode === 'login' ? t('auth.login') : t('auth.register')}
        </h2>
        
        {error && <div className="bg-red-100 text-red-900 p-4 rounded-lg mb-6">{error}</div>}
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-lg font-medium mb-2">{t('auth.email')}</label>
            <input 
              id="email"
              type="email" 
              required 
              className="input-field" 
              value={email}
              onChange={e => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-lg font-medium mb-2">{t('auth.password')}</label>
            <input 
              id="password"
              type="password" 
              required 
              className="input-field" 
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>
          
          {mode === 'register' && (
            <>
              <div>
                <label htmlFor="role" className="block text-lg font-medium mb-2">{t('auth.role')}</label>
                <select id="role" className="input-field" value={role} onChange={e => setRole(e.target.value)}>
                  <option value="student">{t('auth.role_student')}</option>
                  <option value="parent">{t('auth.role_parent')}</option>
                </select>
              </div>
              <label className="flex items-start gap-3 mt-4">
                <input 
                  type="checkbox" 
                  className="w-6 h-6 mt-1 rounded border-gray-300 text-accent focus:ring-accent"
                  checked={consent}
                  onChange={e => setConsent(e.target.checked)}
                />
                <span className="text-lg text-textSecondary">{t('consent.description')}</span>
              </label>
            </>
          )}

          <button type="submit" disabled={loading} className="btn-primary w-full mt-8">
            {loading ? t('common.loading') : (mode === 'login' ? t('auth.login') : t('auth.register'))}
          </button>
        </form>

        <p className="mt-6 text-center text-textSecondary text-base">
          {mode === 'register' ? (
            <>
              {t('auth.already_registered')}{' '}
              <Link
                href="/login"
                className="text-accent font-semibold hover:underline focus:outline-none focus:ring-2 focus:ring-accent rounded inline-flex items-center justify-center min-h-[44px]"
              >
                {t('auth.switch_login')}
              </Link>
            </>
          ) : (
            <>
              {t('auth.no_account')}{' '}
              <Link
                href="/register"
                className="text-accent font-semibold hover:underline focus:outline-none focus:ring-2 focus:ring-accent rounded inline-flex items-center justify-center min-h-[44px]"
              >
                {t('auth.switch_register')}
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
    </div>
  );
};
