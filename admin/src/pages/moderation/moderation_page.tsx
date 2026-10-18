import React, { useState } from 'react';
import { EmptyState } from '../../core/empty_state';

interface ReportItem {
  id: string;
  reporter: string;
  reason: string;
  evidence: string;
  status: 'pending' | 'resolved';
}

export const ModerationPage: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([
    {
      id: '7777',
      reporter: 'Aditi Sharma (Student)',
      reason: 'scam',
      evidence: 'Candidate asking for 500 INR via UPI handle payme@upi for offline referral link',
      status: 'pending',
    },
  ]);
  const [learnedRule, setLearnedRule] = useState<string | null>(null);

  const handleResolve = (id: string) => {
    setReports((prev) => prev.map((r) => (r.id === id ? { ...r, status: 'resolved' } : r)));
    setLearnedRule('Rule learned: "(?i)(?:paytm|gpay|phonepe|upi_handle|send\\\\s*money)" added into scam_rules table (Action: BLOCK)');
  };

  const pendingReports = reports.filter((r) => r.status === 'pending');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-brand-dark dark:text-white mb-1">
          Safety Moderation &amp; Incident Learning
        </h2>
        <p className="text-sm text-brand-slate dark:text-slate-400">
          Review reported conversations, block financial scam extortion, and automate pattern learning into the defensive rules engine.
        </p>
      </div>

      {learnedRule && (
        <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-start gap-3">
          <span className="text-xl">🛡️</span>
          <div>
            <p className="text-xs font-bold text-emerald-900 dark:text-emerald-200">Incident Learning Engine: Active Rule Generated</p>
            <p className="text-xs text-emerald-800 dark:text-emerald-300 font-mono mt-0.5">{learnedRule}</p>
          </div>
        </div>
      )}

      {pendingReports.length === 0 ? (
        <EmptyState
          icon="🛡️"
          title="Moderation Queue is Clean"
          description="There are currently zero pending incident reports. The real-time regex & NLP scam middleware automatically blocks high-risk contact extortion."
          actionLabel="Simulate Incoming Incident"
          onAction={() => {
            setReports([
              {
                id: '8888',
                reporter: 'Rohan Sharma (Giver)',
                reason: 'off_platform',
                evidence: 'Attempted to share personal WhatsApp link before session was scheduled',
                status: 'pending',
              },
            ]);
            setLearnedRule(null);
          }}
        />
      ) : (
        <div className="space-y-4">
          {pendingReports.map((report) => (
            <div
              key={report.id}
              className="p-6 rounded-3xl bg-white dark:bg-brand-cardDark border border-slate-200 dark:border-brand-borderDark shadow-xs space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-red-600 dark:text-red-400 uppercase tracking-wide">
                  Report #{report.id} &bull; Category: {report.reason.toUpperCase()}
                </span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950 text-amber-700 font-bold border border-amber-200">
                  Needs Review
                </span>
              </div>
              <p className="text-xs text-brand-slate">
                <strong>Reporter:</strong> {report.reporter}
              </p>
              <div className="p-3.5 bg-slate-50 dark:bg-slate-900/40 rounded-2xl border border-slate-200 dark:border-slate-800 text-xs font-mono">
                "{report.evidence}"
              </div>
              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-brand-slate">
                  Recommended Action: Suspend user &amp; extract regex pattern
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleResolve(report.id)}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition focus:outline-none"
                  >
                    Suspend Offender &amp; Learn Rule
                  </button>
                  <button
                    onClick={() => handleResolve(report.id)}
                    className="px-3 py-2 bg-slate-100 dark:bg-slate-800 text-brand-slate rounded-xl text-xs font-bold hover:bg-slate-200"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
