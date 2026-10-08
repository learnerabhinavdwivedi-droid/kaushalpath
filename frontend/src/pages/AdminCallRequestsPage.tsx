import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'wouter';
import { getCallRequests, getMentorRequests, CallRequestRow, MentorRequestRow } from '../api/client';

export const AdminCallRequestsPage: React.FC = () => {
  const { t } = useTranslation();
  const [callRequests, setCallRequests] = useState<CallRequestRow[]>([]);
  const [mentorRequests, setMentorRequests] = useState<MentorRequestRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([getCallRequests(), getMentorRequests()])
      .then(([calls, mentors]) => {
        setCallRequests(calls);
        setMentorRequests(mentors);
      })
      .catch(e => setError(e.message || t('common.error')))
      .finally(() => setLoading(false));
  }, [t]);

  return (
    <div className="min-h-screen bg-background p-4 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-2 py-4 mb-4">
        <h1 className="text-2xl font-bold text-accent">Family & Mentor Requests</h1>
        <Link href="/counsellor" className="btn-secondary">
          Back to Cohort
        </Link>
      </div>

      {error && <p className="text-error mb-4">{error}</p>}
      
      {loading ? (
        <p className="text-textSecondary">{t('common.loading')}</p>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="card">
            <h2 className="text-xl font-bold mb-4 text-orange">Human Call Requests</h2>
            {callRequests.length === 0 ? (
              <p className="text-textSecondary">No call requests pending.</p>
            ) : (
              <div className="space-y-3">
                {callRequests.map(r => (
                  <div key={r.id} className="p-3 border rounded bg-white">
                    <p className="font-bold">Room #{r.room_id}</p>
                    <p className="text-sm text-textSecondary">Requested by User #{r.requested_by}</p>
                    <div className="flex justify-between items-center mt-2">
                      <span className="text-xs text-gray-500">{new Date(r.created_at || '').toLocaleString()}</span>
                      <span className="px-2 py-1 text-xs font-bold bg-amber-100 text-amber-800 rounded">{r.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="text-xl font-bold mb-4 text-accent">Mentor Requests</h2>
            {mentorRequests.length === 0 ? (
              <p className="text-textSecondary">No mentor requests pending.</p>
            ) : (
              <div className="space-y-3">
                {mentorRequests.map(r => (
                  <div key={r.id} className="p-3 border rounded bg-white">
                    <p className="font-bold">User #{r.user_id}</p>
                    <p className="text-lg text-accent font-mono">{r.phone_number}</p>
                    <div className="flex justify-between items-center mt-2">
                      <span className="text-xs text-gray-500">{new Date(r.created_at || '').toLocaleString()}</span>
                      <span className="px-2 py-1 text-xs font-bold bg-amber-100 text-amber-800 rounded">{r.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
