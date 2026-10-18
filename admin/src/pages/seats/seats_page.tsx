import React, { useState } from 'react';
import { EmptyState } from '../../core/empty_state';

export const SeatsPage: React.FC = () => {
  const [allocatedSeats, setAllocatedSeats] = useState<number>(50);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-brand-dark dark:text-white mb-1">
          Sponsored Seats &amp; Grants
        </h2>
        <p className="text-sm text-brand-slate dark:text-slate-400">
          Manage institutional student subsidies and CSR scholarship pool allocations for cross-college mentorship sessions.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 bg-white dark:bg-brand-cardDark rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-xs">
          <p className="text-xs text-brand-slate">Sponsored Seats Allocated</p>
          <p className="text-3xl font-bold text-brand-dark dark:text-white mt-1">{allocatedSeats}</p>
          <p className="text-[11px] text-emerald-600 mt-1">Funded by alumni CSR foundation</p>
        </div>
        <div className="p-5 bg-white dark:bg-brand-cardDark rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-xs">
          <p className="text-xs text-brand-slate">Subsidized Sessions Claimed</p>
          <p className="text-3xl font-bold text-brand-teal mt-1">14</p>
          <p className="text-[11px] text-brand-slate mt-1">36 seats remaining</p>
        </div>
        <div className="p-5 bg-white dark:bg-brand-cardDark rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-xs">
          <p className="text-xs text-brand-slate">Free Same-College Sessions</p>
          <p className="text-3xl font-bold text-brand-indigo dark:text-indigo-400 mt-1">28</p>
          <p className="text-[11px] text-brand-slate mt-1">Zero credit cost to students</p>
        </div>
      </div>

      {allocatedSeats === 0 ? (
        <EmptyState
          icon="🎟️"
          title="No Sponsored Seats Allocated"
          description="Grant pools allow underprivileged students to connect across colleges without paying credits."
          actionLabel="Allocate 50 Sponsored Seats"
          onAction={() => setAllocatedSeats(50)}
        />
      ) : (
        <div className="p-6 bg-white dark:bg-brand-cardDark rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-xs space-y-3">
          <h3 className="text-base font-bold text-brand-dark dark:text-white">Active Sponsor Pool: IIIT Delhi Tech Advancement Fund</h3>
          <p className="text-xs text-brand-slate dark:text-slate-400">
            Enrolled students with verified proof-of-work repositories can claim up to 10 sponsored credits per month for cross-college mentorship sessions.
          </p>
          <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2.5 overflow-hidden mt-3">
            <div className="bg-gradient-to-r from-brand-coral to-brand-teal h-2.5 rounded-full" style={{ width: '28%' }} />
          </div>
          <div className="flex justify-between text-xs text-brand-slate pt-1">
            <span>Pool Utilization: 28%</span>
            <span>Allocated: {allocatedSeats} seats</span>
          </div>
        </div>
      )}
    </div>
  );
};
