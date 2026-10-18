import React from 'react';

export type VerificationType = 'alumni' | 'employer' | 'expert';
export type RatingBandType = 'rising' | 'trusted' | 'top_rated';
export type AvailabilityType = 'active_now' | 'available_today' | 'inactive';

interface VerificationBadgeProps {
  type: VerificationType;
  className?: string;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({ type, className = '' }) => {
  if (type === 'alumni') {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800 ${className}`} title="Verified against university registrar roll">
        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/></svg>
        Verified Alumni
      </span>
    );
  }
  if (type === 'employer') {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 ${className}`} title="Verified corporate entity CIN/GST">
        <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2h-3a1 1 0 01-1-1v-2a1 1 0 00-1-1H9a1 1 0 00-1 1v2a1 1 0 01-1 1H4a1 1 0 110-2V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z" clipRule="evenodd"/></svg>
        Verified Employer
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 ${className}`} title="Endorsed academic domain mentor">
      ★ Verified Expert
    </span>
  );
};

interface RatingBandBadgeProps {
  band: RatingBandType;
  stars?: number;
  sessionCount?: number;
  className?: string;
}

export const RatingBandBadge: React.FC<RatingBandBadgeProps> = ({ band, stars, sessionCount, className = '' }) => {
  if (band === 'rising') {
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-50 dark:bg-sky-950 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800 ${className}`} title="Fair-start boost applied in ranking">
        ⚡ Rising (Boosted)
      </span>
    );
  }
  if (band === 'trusted') {
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 ${className}`} title="Consistently rated >4.5 stars">
        🛡️ Trusted {stars ? `(${stars}★)` : ''}
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 ${className}`} title="Top 5% giver across institution">
      🏆 Top Rated {stars ? `(${stars}★)` : ''} {sessionCount ? `• ${sessionCount} sessions` : ''}
    </span>
  );
};

interface AvailabilityBadgeProps {
  status: AvailabilityType;
  todayWindow?: string;
  responseRate?: string;
  avgReply?: string;
  className?: string;
}

export const AvailabilityBadge: React.FC<AvailabilityBadgeProps> = ({
  status,
  todayWindow = '8-10 PM',
  responseRate = '94%',
  avgReply = '18m',
  className = '',
}) => {
  if (status === 'active_now') {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 ${className}`} title={`Active right now • ${responseRate} response rate • avg reply ${avgReply}`}>
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping inline-block" />
        Active now ({responseRate} reply)
      </span>
    );
  }
  if (status === 'available_today') {
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 ${className}`} title={`Available today during window ${todayWindow}`}>
        <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
        Available today ({todayWindow})
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 ${className}`} title="Capacity reached or inactive">
      <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />
      Inactive
    </span>
  );
};

export const ProofOfWorkBadge: React.FC<{ repoUrl?: string; label?: string; className?: string }> = ({
  repoUrl = 'https://github.com/aditi/distributed-raft',
  label = 'Verified Proof of Work',
  className = '',
}) => (
  <a
    href={repoUrl}
    target="_blank"
    rel="noopener noreferrer"
    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-cyan-50 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800 hover:underline ${className}`}
    title={`Tied to repository ${repoUrl}`}
  >
    🔗 {label} ↗
  </a>
);

export const VouchedBadge: React.FC<{ giverName?: string; company?: string; className?: string }> = ({
  giverName = 'Rohan Sharma',
  company = 'Microsoft',
  className = '',
}) => (
  <span
    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-fuchsia-50 dark:bg-fuchsia-950 text-fuchsia-700 dark:text-fuchsia-300 border border-fuchsia-200 dark:border-fuchsia-800 ${className}`}
    title={`Referral vouch from ${giverName} at ${company}`}
  >
    🎖️ Vouched by {giverName} at {company}
  </span>
);
