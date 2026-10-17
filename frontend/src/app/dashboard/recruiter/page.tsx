"use client";

import React, { useEffect, useState } from "react";
import { fetchDashboard, getStoredUser, UserSession } from "@/lib/api";
import Link from "next/link";

export default function RecruiterDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
    fetchDashboard("recruiter")
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load recruiter dashboard");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-slate-500">
        <div className="inline-block w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium">Loading Recruiter Portal...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 space-y-3">
          <h2 className="font-bold text-base">Access Restricted (403 / Session Required)</h2>
          <p className="text-xs">{error}</p>
          <div className="pt-2">
            <Link
              href="/login"
              className="text-xs bg-rose-600 text-white font-semibold px-4 py-2 rounded-xl hover:bg-rose-700 transition"
            >
              Sign In as Recruiter
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Recruiter Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2.5 py-0.5 rounded border border-purple-200 flex items-center gap-1">
              <svg className="w-3.5 h-3.5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Verified Employer &bull; CIN Validated
            </span>
            <span className="text-xs text-slate-400">&bull;</span>
            <span className="text-xs font-semibold text-slate-600">Razorpay Software Pvt Ltd</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
            {data?.user?.full_name || "Priya (Tech Recruiter)"}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Active Searches: <strong className="text-slate-800">Backend SWE, Site Reliability Engineer &bull; 2025 Batch</strong>
          </p>
        </div>

        <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs rounded-xl shadow-xs transition">
          + Post New Referral Role
        </button>
      </div>

      {/* Main Grid: Pre-matched Candidates */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Pre-Matched Verified Candidates</h2>
              <p className="text-xs text-slate-500">Filtered by semantic resume parsing + verified GitHub proof of work</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:border-purple-300 shadow-xs space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-sm text-slate-900">Aarav Sharma</h3>
                    <span className="text-[10px] bg-emerald-50 text-emerald-700 font-bold px-2 py-0.5 rounded border border-emerald-200">
                      94% Match Score
                    </span>
                    <span className="text-[10px] text-slate-500 font-medium">IIIT Delhi &bull; B.Tech CS</span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">
                    Seeking: <strong className="text-slate-800">Software Engineer - Distributed Systems</strong>
                  </p>
                </div>
                <button className="px-3 py-1.5 text-xs font-semibold bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition">
                  Invite to Hiring Chat
                </button>
              </div>

              {/* Proof of work tags */}
              <div className="flex items-center gap-3 text-xs text-slate-600 pt-1">
                <span className="flex items-center gap-1 text-[11px] bg-slate-100 px-2 py-0.5 rounded">
                  <svg className="w-3.5 h-3.5 text-slate-700" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                  </svg>
                  GitHub: Tanushyadav9/warmpath (Verified Commits)
                </span>
                <span className="text-[11px] bg-slate-100 px-2 py-0.5 rounded">
                  Resume: Parsed & Student Confirmed
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Active Postings */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-slate-900">Active Job & Referral Postings</h3>
            <div className="border border-slate-100 rounded-lg p-3 bg-slate-50/50 space-y-1">
              <h4 className="text-xs font-bold text-slate-800">Software Engineer (Backend)</h4>
              <p className="text-[11px] text-slate-500">Razorpay &bull; Bengaluru (Hybrid)</p>
              <p className="text-[10px] text-purple-700 font-medium">8 qualified applicants matched</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
