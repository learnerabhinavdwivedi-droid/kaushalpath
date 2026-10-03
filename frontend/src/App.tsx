import React from 'react';
import { Route, Switch } from 'wouter';
import { LandingPage } from './pages/LandingPage';
import { AuthPage } from './pages/AuthPage';
import { ProfilePage } from './pages/ProfilePage';
import { AssessmentPage } from './pages/AssessmentPage';
import { ResultsPage } from './pages/ResultsPage';
import { SettingsPage } from './pages/SettingsPage';
import { CareerDetailPage } from './pages/CareerDetailPage';
import { RoomCreatePage } from './pages/RoomCreatePage';
import { RoomJoinPage } from './pages/RoomJoinPage';
import { RoomHomePage } from './pages/RoomHomePage';

export const App: React.FC = () => {
  return (
    <div className="font-sans antialiased bg-background text-textPrimary min-h-screen">
      <Switch>
        <Route path="/" component={LandingPage} />
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
        <Route path="/career/:id" component={CareerDetailPage} />
        <Route path="/room/new" component={RoomCreatePage} />
        <Route path="/room/join" component={RoomJoinPage} />
        <Route path="/room/:code" component={RoomHomePage} />
        <Route>
          {/* 404 Route */}
          <div className="flex flex-col items-center justify-center min-h-screen">
            <h1 className="text-4xl font-bold">404</h1>
            <p className="mt-4">Page not found</p>
          </div>
        </Route>
      </Switch>
    </div>
  );
};

export default App;
