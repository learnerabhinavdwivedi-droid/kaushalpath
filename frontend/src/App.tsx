import React, { lazy, Suspense, useEffect } from 'react';
import { Route, Switch, useLocation } from 'wouter';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { LandingPage } from './pages/LandingPage';

// Phase 9 perf: route-level code splitting — every page except the landing
// page loads as its own chunk on demand (LandingPage stays eager so `/`
// first-paint and the smoke test are unaffected).
const AuthPage = lazy(() => import('./pages/AuthPage').then((m) => ({ default: m.AuthPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage })));
const AssessmentPage = lazy(() => import('./pages/AssessmentPage').then((m) => ({ default: m.AssessmentPage })));
const ResultsPage = lazy(() => import('./pages/ResultsPage').then((m) => ({ default: m.ResultsPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const CareerDetailPage = lazy(() => import('./pages/CareerDetailPage').then((m) => ({ default: m.CareerDetailPage })));
const RoomCreatePage = lazy(() => import('./pages/RoomCreatePage').then((m) => ({ default: m.RoomCreatePage })));
const RoomJoinPage = lazy(() => import('./pages/RoomJoinPage').then((m) => ({ default: m.RoomJoinPage })));
const RoomHomePage = lazy(() => import('./pages/RoomHomePage').then((m) => ({ default: m.RoomHomePage })));
const TalkPage = lazy(() => import('./pages/TalkPage').then((m) => ({ default: m.TalkPage })));
const CohortPage = lazy(() => import('./pages/CohortPage').then((m) => ({ default: m.CohortPage })));
const StudentDetailPage = lazy(() => import('./pages/StudentDetailPage').then((m) => ({ default: m.StudentDetailPage })));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })));
const ResistancePage = lazy(() => import('./pages/ResistancePage').then((m) => ({ default: m.ResistancePage })));
const AdminResistancePage = lazy(() => import('./pages/AdminResistancePage').then((m) => ({ default: m.AdminResistancePage })));
const AuditPage = lazy(() => import('./pages/AuditPage').then((m) => ({ default: m.AuditPage })));
const StyleGuidePage = lazy(() => import('./pages/StyleGuidePage'));
const SparkLabPage = lazy(() => import('./pages/SparkLabPage'));
const StartPage = lazy(() => import('./pages/StartPage').then((m) => ({ default: m.StartPage })));
import { RouteWipe } from './components/ui/RouteWipe';
import { RequireRole } from './components/RequireRole';
import { ModelVersionFooter } from './components/ModelVersionFooter';
import { OfflineBanner } from './components/OfflineBanner';
import { ReadThisScreen } from './components/ReadThisScreen';
import { applyDisplayPrefs } from './lib/displayPrefs';
import { EASE } from './lib/motion';

const STAFF_ROLES = ['counsellor', 'admin', 'scheme_admin'];
// Phase 16: the scheme-administrator dashboard is a superset of the counsellor
// cohort view, so it is gated to the two administrator roles only.
const ADMIN_ROLES = ['admin', 'scheme_admin'];

const RouteFallback: React.FC = () => (
  <div className="flex min-h-screen items-center justify-center bg-page">
    <span className="h-8 w-8 animate-spin rounded-full border-4 border-orange-deep border-t-transparent" />
  </div>
);

export const App: React.FC = () => {
  const [location] = useLocation();
  const reduced = useReducedMotion();
  // Phase 17: apply persisted font-size / high-contrast prefs on boot.
  useEffect(() => {
    applyDisplayPrefs();
  }, []);
  return (
    <div className="min-h-screen bg-page font-sans text-ink antialiased">
      <RouteWipe />
      <OfflineBanner />
      {/* Phase 8 route transition: exit 250ms (opacity + y -20), enter 450ms
          (opacity + y 30->0); opacity-only when prefers-reduced-motion. */}
      <AnimatePresence mode="wait">
        <motion.div
          key={location}
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          exit={
            reduced
              ? { opacity: 0, transition: { duration: 0.15 } }
              : { opacity: 0, y: -20, transition: { duration: 0.25, ease: EASE } }
          }
          transition={{ duration: reduced ? 0.2 : 0.45, ease: EASE }}
        >
          <Suspense fallback={<RouteFallback />}>
          <Switch location={location}>
        <Route path="/" component={LandingPage} />
        {/* Phase 17: icon-first, 3-tap onboarding for low-literacy parents. */}
        <Route path="/start" component={StartPage} />
        {/* Phase 1: design-system style guide (tokens + primitives). */}
        <Route path="/styleguide" component={StyleGuidePage} />
        {/* Phase 2+: SparkLab-style marketing shell (navbar + footer + sections). */}
        <Route path="/home" component={SparkLabPage} />
        <Route path="/login">
          {() => <AuthPage mode="login" />}
        </Route>
        <Route path="/register">
          {() => <AuthPage mode="register" />}
        </Route>
        <Route path="/profile" component={ProfilePage} />
        <Route path="/assessment" component={AssessmentPage} />
        <Route path="/results" component={ResultsPage} />
        <Route path="/settings" component={SettingsPage} />
        {/* Phase 15: the shared learner + parent chat. */}
        <Route path="/talk" component={TalkPage} />
        <Route path="/career/:id" component={CareerDetailPage} />
        <Route path="/room/new" component={RoomCreatePage} />
        <Route path="/room/join" component={RoomJoinPage} />
        <Route path="/room/:code" component={RoomHomePage} />
        {/* Phase 8: counsellor/admin dashboard, guarded client-side; backend re-checks. */}
        <Route path="/counsellor">
          {() => (
            <RequireRole roles={STAFF_ROLES}>
              <CohortPage />
            </RequireRole>
          )}
        </Route>
        <Route path="/counsellor/analytics">
          {() => (
            <RequireRole roles={STAFF_ROLES}>
              <AnalyticsPage />
            </RequireRole>
          )}
        </Route>
        <Route path="/counsellor/resistance">
          {() => (
            <RequireRole roles={STAFF_ROLES}>
              <ResistancePage />
            </RequireRole>
          )}
        </Route>
        {/* Phase 16: scheme-administrator resistance dashboard (admin + scheme_admin). */}
        <Route path="/admin/resistance">
          {() => (
            <RequireRole roles={ADMIN_ROLES}>
              <AdminResistancePage />
            </RequireRole>
          )}
        </Route>
        <Route path="/counsellor/audit">
          {() => (
            <RequireRole roles={STAFF_ROLES}>
              <AuditPage />
            </RequireRole>
          )}
        </Route>
        <Route path="/counsellor/students/:id">
          {() => (
            <RequireRole roles={STAFF_ROLES}>
              <StudentDetailPage />
            </RequireRole>
          )}
        </Route>
        <Route>
          {/* 404 Route */}
          <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-5 text-center">
            <p className="font-display text-[120px] font-extrabold leading-none text-ink">404</p>
            <p className="font-mono text-lg text-muted">Page not found</p>
            <a href="/" className="btn-primary mt-4 no-underline">
              Back to home
            </a>
          </div>
        </Route>
      </Switch>
          </Suspense>
        </motion.div>
      </AnimatePresence>
      <ReadThisScreen />
      <ModelVersionFooter />
    </div>
  );
};

export default App;
