import React from 'react';
import {
  VerificationBadge,
  RatingBandBadge,
  AvailabilityBadge,
  ProofOfWorkBadge,
  VouchedBadge,
} from '../../core/badges';

export const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Title & Introduction */}
      <div>
        <h2 className="text-2xl font-bold text-brand-dark dark:text-white mb-1">
          Institutional Analytics Dashboard
        </h2>
        <p className="text-sm text-brand-slate dark:text-slate-400">
          Real-time metrics on mentorship sessions, fulfillment rates, and skill gap supply-demand analytics.
        </p>
      </div>

      {/* Badges System Showcase Bar */}
      <div className="bg-white dark:bg-brand-cardDark p-4 rounded-2xl border border-slate-200 dark:border-brand-borderDark shadow-xs space-y-2">
        <p className="text-xs font-bold uppercase tracking-wider text-brand-slate">
          Unified Badge System
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <VerificationBadge type="alumni" />
          <VerificationBadge type="employer" />
          <VerificationBadge type="expert" />
          <RatingBandBadge band="rising" />
          <RatingBandBadge band="trusted" stars={4.8} />
          <RatingBandBadge band="top_rated" stars={4.9} sessionCount={18} />
          <AvailabilityBadge status="active_now" responseRate="95%" avgReply="18m" />
          <AvailabilityBadge status="available_today" todayWindow="8 to 10 pm" />
          <ProofOfWorkBadge repoUrl="https://github.com/aditi/distributed-raft" />
          <VouchedBadge giverName="Rohan Sharma" company="Microsoft" />
        </div>
      </div>

      {/* Primary KPI Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-brand-cardDark p-5 rounded-3xl shadow-xs border border-slate-200 dark:border-brand-borderDark">
          <p className="text-xs font-semibold text-brand-slate dark:text-slate-400">Total Requests</p>
          <p className="text-3xl font-extrabold text-brand-dark dark:text-white mt-1">2</p>
          <p className="text-[11px] font-semibold text-emerald-600 mt-1">100% Answered within 72h</p>
        </div>
        <div className="bg-white dark:bg-brand-cardDark p-5 rounded-3xl shadow-xs border border-slate-200 dark:border-brand-borderDark">
          <p className="text-xs font-semibold text-brand-slate dark:text-slate-400">Fulfillment Rate</p>
          <p className="text-3xl font-extrabold text-brand-teal mt-1">100%</p>
          <p className="text-[11px] text-brand-slate mt-1">Completed vs Booked</p>
        </div>
        <div className="bg-white dark:bg-brand-cardDark p-5 rounded-3xl shadow-xs border border-slate-200 dark:border-brand-borderDark">
          <p className="text-xs font-semibold text-brand-slate dark:text-slate-400">Active Verified Givers</p>
          <p className="text-3xl font-extrabold text-brand-indigo dark:text-indigo-400 mt-1">2</p>
          <p className="text-[11px] text-emerald-600 mt-1">Both with active status</p>
        </div>
        <div className="bg-white dark:bg-brand-cardDark p-5 rounded-3xl shadow-xs border border-slate-200 dark:border-brand-borderDark">
          <p className="text-xs font-semibold text-brand-slate dark:text-slate-400">Launch Gate</p>
          <p className="text-3xl font-extrabold text-amber-500 mt-1">LOCKED</p>
          <p className="text-[11px] text-brand-slate mt-1">Target: 50 verified givers</p>
        </div>
      </div>

      {/* Skill-Gap Analysis Matrix */}
      <div className="bg-white dark:bg-brand-cardDark p-6 rounded-3xl shadow-xs border border-slate-200 dark:border-brand-borderDark space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-brand-dark dark:text-white flex items-center gap-2">
              <span>📊</span> Institutional Skill-Gap Matrix
            </h3>
            <p className="text-xs text-brand-slate dark:text-slate-400">
              Comparing student mentorship requests against verified alumni covering the skills.
            </p>
          </div>
          <button
            onClick={() => alert('Exporting institution_metrics.csv...')}
            className="text-xs font-bold px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
          >
            Export CSV 📥
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800">
            <div className="flex justify-between text-xs font-bold mb-1">
              <span className="text-brand-dark dark:text-white">Distributed Systems</span>
              <span className="text-emerald-600">Covered (Supply: 8)</span>
            </div>
            <p className="text-[11px] text-brand-slate">3 student requests &bull; 8 verified alumni</p>
            <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 mt-2">
              <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '100%' }} />
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800">
            <div className="flex justify-between text-xs font-bold mb-1">
              <span className="text-brand-dark dark:text-white">FastAPI &amp; Python</span>
              <span className="text-emerald-600">Covered (Supply: 5)</span>
            </div>
            <p className="text-[11px] text-brand-slate">2 student requests &bull; 5 verified alumni</p>
            <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 mt-2">
              <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '100%' }} />
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800">
            <div className="flex justify-between text-xs font-bold mb-1">
              <span className="text-brand-dark dark:text-white">GPU Kernels / Triton</span>
              <span className="text-brand-coral font-bold">Skill Gap (0 Alumni)</span>
            </div>
            <p className="text-[11px] text-brand-slate">4 student requests &bull; 0 verified alumni supply</p>
            <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 mt-2">
              <div className="bg-brand-coral h-2 rounded-full" style={{ width: '0%' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
