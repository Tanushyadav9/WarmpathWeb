"use client";

import React, { useEffect, useState } from "react";
import { fetchDashboard, getStoredUser, UserSession } from "@/lib/api";
import Link from "next/link";

export default function StudentDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
    fetchDashboard("student")
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load student dashboard");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-slate-500">
        <div className="inline-block w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium">Loading Student Portal...</p>
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
              Sign In as Student
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-teal-600 bg-teal-50 px-2 py-0.5 rounded border border-teal-100">
              Student Seeker
            </span>
            <span className="text-xs text-slate-400">&bull;</span>
            <span className="text-xs text-slate-500 font-medium">IIIT Delhi</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
            Welcome back, {data?.user?.full_name || "Aarav Sharma"}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Targeting: <strong className="text-slate-800 font-semibold">{data?.profile?.target_role || "Software Engineer (Backend / Distributed Systems)"}</strong>
          </p>
        </div>

        {/* Credit Wallet Pill */}
        <div className="flex items-center gap-4 bg-slate-50 border border-slate-200/80 p-3 rounded-xl">
          <div>
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Credit Wallet</p>
            <p className="text-lg font-bold text-slate-900">{data?.wallet?.balance ?? 50} <span className="text-xs font-normal text-slate-500">credits</span></p>
          </div>
          <div className="border-l border-slate-200 pl-3 text-right">
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Escrow Holds</p>
            <p className="text-sm font-semibold text-teal-600">{data?.wallet?.held_in_escrow ?? 0} <span className="text-xs font-normal text-slate-400">credits</span></p>
          </div>
        </div>
      </div>

      {/* Main Grid: Recommended Givers & Active Requests */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Recommended Givers with "Why this match" */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Recommended Mentors & Alumni</h2>
              <p className="text-xs text-slate-500">Semantic pgvector match on skills, target companies, and batch affinity</p>
            </div>
            <span className="text-xs font-medium text-teal-700 bg-teal-50 px-2 py-1 rounded">
              Free (Same-College Affinity)
            </span>
          </div>

          <div className="space-y-4">
            {data?.recommended_givers && data.recommended_givers.length > 0 ? (
              data.recommended_givers.map((giver: any) => (
                <div
                  key={giver.id}
                  className="bg-white border border-slate-200 rounded-xl p-5 hover:border-teal-500/50 hover:shadow-sm transition-all space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="font-bold text-sm text-slate-900">{giver.full_name}</h3>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                          {giver.giver_band || "Top Rated"}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                          ★ {giver.rating_avg ? giver.rating_avg.toFixed(1) : "4.9"} ({giver.total_sessions || 12} sessions)
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-0.5 font-medium">
                        {giver.designation || "Senior Software Engineer"} @ <span className="text-slate-900 font-semibold">{giver.company || "Google"}</span>
                      </p>
                    </div>

                    <button className="px-3 py-1.5 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-2xs transition-colors">
                      Request Session
                    </button>
                  </div>

                  {/* Why this match pill (F9) */}
                  <div className="bg-teal-50/60 border border-teal-100 rounded-lg p-2.5 flex items-start space-x-2">
                    <svg className="w-4 h-4 text-teal-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-[11px] text-teal-900 leading-relaxed">
                      <strong className="font-semibold text-teal-950">Why this match:</strong> {giver.why_match || "Same college alumnus (IIIT Delhi); shares skills in Distributed Systems and Python; strong reply rate within 4 hours."}
                    </p>
                  </div>

                  {/* Skills badges */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {(giver.skills || ["Distributed Systems", "FastAPI", "Kubernetes", "System Design"]).map((s: string) => (
                      <span key={s} className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center bg-white border border-slate-200 rounded-xl text-slate-400 text-xs">
                No givers matched yet. Check your skill profile.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Active Requests & Matched Opportunities */}
        <div className="space-y-6">
          {/* Active Asks / Sessions */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-2xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-sm text-slate-900">My Requests & Sessions</h3>
              <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium">
                {data?.active_requests?.length || 1} Open
              </span>
            </div>

            <div className="space-y-3">
              <div className="border border-slate-100 rounded-lg p-3 bg-slate-50/50 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-800">Mock System Design Interview</span>
                  <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.2 rounded">
                    Scheduled
                  </span>
                </div>
                <p className="text-[11px] text-slate-500">Mentor: Vikram Malhotra (Alumni, Google)</p>
                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                  <span>Google Meet linked</span>
                  <span className="text-teal-600 font-medium">Tomorrow @ 6:00 PM</span>
                </div>
              </div>
            </div>
          </div>

          {/* Matched Opportunities (Jobs & Referrals) */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-2xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-sm text-slate-900">Pre-Matched Opportunities</h3>
              <span className="text-[10px] bg-teal-50 text-teal-700 px-2 py-0.5 rounded font-medium">
                Verified Employers
              </span>
            </div>

            <div className="space-y-3">
              <div className="border border-slate-100 rounded-lg p-3 hover:bg-slate-50 transition-colors space-y-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-slate-900">Software Engineer - Backend (Referral)</h4>
                  <span className="text-[10px] font-semibold text-teal-600">Razorpay</span>
                </div>
                <p className="text-[11px] text-slate-500">Posted by Priya (Verified Tech Recruiter) &bull; Bengaluru / Remote</p>
                <div className="pt-1.5 flex items-center justify-between">
                  <span className="text-[10px] bg-teal-50 text-teal-700 px-1.5 py-0.5 rounded font-medium">92% Skill Overlap</span>
                  <button className="text-[11px] text-teal-600 font-semibold hover:underline">Apply with 1-Click Asks &rarr;</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
