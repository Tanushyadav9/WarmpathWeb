import React, { useState } from 'react';
import { EmptyState } from '../../core/empty_state';
import { VerificationBadge } from '../../core/badges';

interface VerificationItem {
  id: string;
  name: string;
  userType: 'student' | 'alumnus' | 'recruiter';
  identifier: string;
  college: string;
  evidence: string;
  isFake: boolean;
  status: 'pending' | 'approved' | 'rejected';
}

export const VerificationPage: React.FC = () => {
  const [items, setItems] = useState<VerificationItem[]>([
    {
      id: 'fake-1',
      name: 'Unknown Impersonator',
      userType: 'alumnus',
      identifier: 'FORGED-9999',
      college: 'IIIT Delhi',
      evidence: 'Degree certificate scan with inconsistent font and non-existent roll registry ID',
      isFake: true,
      status: 'pending',
    },
    {
      id: 'real-1',
      name: 'Raghav Sen',
      userType: 'student',
      identifier: '2022CSB1042',
      college: 'IIIT Delhi',
      evidence: 'Roll number verified against official university pre-registered student master list',
      isFake: false,
      status: 'pending',
    },
  ]);

  const handleDecision = (id: string, decision: 'approved' | 'rejected') => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, status: decision } : item)));
  };

  const pendingItems = items.filter((i) => i.status === 'pending');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-brand-dark dark:text-white mb-1">
          Member Credential Verification Queue
        </h2>
        <p className="text-sm text-brand-slate dark:text-slate-400">
          Validate student rolls, alumni university credentials, and recruiter corporate registration (CIN/GST).
        </p>
      </div>

      {pendingItems.length === 0 ? (
        <EmptyState
          icon="🎓"
          title="All Submissions Verified"
          description="Every member submission has been reviewed. Pre-matching algorithms continue to auto-verify students whose institutional rolls match university registers."
          actionLabel="Load More Verification Candidates"
          onAction={() => {
            setItems([
              {
                id: 'new-1',
                name: 'Neha Verma (Zomato)',
                userType: 'recruiter',
                identifier: 'CIN-U93030DL2010PTC198141',
                college: 'Corporate Partner',
                evidence: 'Ministry of Corporate Affairs CIN match verified for Zomato Limited',
                isFake: false,
                status: 'pending',
              },
            ]);
          }}
        />
      ) : (
        <div className="space-y-4">
          {pendingItems.map((item) => (
            <div
              key={item.id}
              className={`p-6 rounded-3xl bg-white dark:bg-brand-cardDark border shadow-xs space-y-3 ${
                item.isFake
                  ? 'border-red-200 dark:border-red-950/60'
                  : 'border-emerald-200 dark:border-emerald-950/60'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-brand-dark dark:text-white">{item.name}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-brand-slate uppercase font-bold">
                    {item.userType}
                  </span>
                </div>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                    item.isFake
                      ? 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'
                      : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                  }`}
                >
                  {item.isFake ? 'Flagged Identifier' : 'Registry Matched'}
                </span>
              </div>

              <div className="text-xs text-brand-slate space-y-1">
                <p>
                  <strong>Identifier:</strong> <span className="font-mono">{item.identifier}</span> &bull; <strong>College:</strong> {item.college}
                </p>
                <p>
                  <strong>Evidence:</strong> {item.evidence}
                </p>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                <span className="text-xs text-brand-slate">
                  {item.isFake ? 'Action: Reject unverified applicant' : 'Action: Approve and issue official badge'}
                </span>
                <div className="flex items-center gap-2">
                  {item.isFake ? (
                    <button
                      onClick={() => handleDecision(item.id, 'rejected')}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition focus:outline-none"
                    >
                      Reject with Reason ✕
                    </button>
                  ) : (
                    <button
                      onClick={() => handleDecision(item.id, 'approved')}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition focus:outline-none"
                    >
                      Auto-Verify &amp; Issue Badge ✓
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
