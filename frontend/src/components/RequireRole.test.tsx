import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const { setLocation } = vi.hoisted(() => ({ setLocation: vi.fn() }));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'en', changeLanguage: () => {} } }),
}));
vi.mock('wouter', () => ({
  useLocation: () => ['/', setLocation],
}));
vi.mock('../api/client', () => ({
  getMe: vi.fn().mockResolvedValue({ user_id: 1, email: 'c@x.io', role: 'counsellor', lang: 'en', student_id: null }),
}));

import { RequireRole } from './RequireRole';
import { useAuthStore } from '../store/useStore';

const Child = () => <div>secret</div>;

describe('RequireRole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ token: null, role: null, studentId: null });
  });

  it('redirects to /login when there is no token', () => {
    render(
      <RequireRole roles={['counsellor', 'admin']}>
        <Child />
      </RequireRole>
    );
    expect(setLocation).toHaveBeenCalledWith('/login');
    expect(screen.queryByText('secret')).not.toBeInTheDocument();
  });

  it('shows the denied screen for a role that is not allowed', () => {
    useAuthStore.setState({ token: 't', role: 'student', studentId: 1 });
    render(
      <RequireRole roles={['counsellor', 'admin']}>
        <Child />
      </RequireRole>
    );
    expect(screen.getByText('guard.denied_title')).toBeInTheDocument();
    expect(screen.queryByText('secret')).not.toBeInTheDocument();
  });

  it('renders children for an allowed role', () => {
    useAuthStore.setState({ token: 't', role: 'counsellor', studentId: null });
    render(
      <RequireRole roles={['counsellor', 'admin']}>
        <Child />
      </RequireRole>
    );
    expect(screen.getByText('secret')).toBeInTheDocument();
    expect(screen.queryByText('guard.denied_title')).not.toBeInTheDocument();
  });
});
