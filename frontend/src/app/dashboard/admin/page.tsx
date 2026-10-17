"use client";

import React, { useEffect, useState } from "react";
import { fetchDashboard, getStoredUser, UserSession } from "@/lib/api";
import Link from "next/link";

export default function AdminDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
    fetchDashboard("admin")
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load institution admin dashboard");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-slate-500">
        <div className="inline-block w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium">Loading Institution Console...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="p-6 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 space-y-3">
          <h2 className="font-bold text-base">Access Restricted (403 / Admin Privileges Required)</h2>
          <p className="text-xs">{error}</p>
          <div className="pt-2">
            <Link
              href="/login"
              className="text-xs bg-rose-600 text-white font-semibold px-4 py-2 rounded-xl hover:bg-rose-700 transition"
            >
              Sign In as Institution Admin
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
            <span className="text-xs font-bold uppercase tracking-wider text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded border border-rose-200">
              Institution Admin Console
            </span>
            <span className="text-xs text-slate-400">&bull;</span>
            <span className="text-xs font-semibold text-slate-700">Indraprastha Institute of Information Technology Delhi (IIIT-D)</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
            Alumni Governance & Verification Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Admin: <strong className="text-slate-800 font-semibold">{data?.user?.full_name || "Dr. Arvind Sharma"}</strong> &bull; Superuser Audit Enabled
          </p>
        </div>

        {/* Pilot Target Status (F34) */}
        <div className="flex items-center gap-3 bg-slate-50 border border-slate-200 p-3 rounded-xl text-xs">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
          <div>
            <p className="text-[10px] uppercase font-bold text-slate-400">Launch Gate Target</p>
            <p className="font-semibold text-slate-800">50 Verified Givers Gate: <strong className="text-emerald-600 font-bold">Passed (50/50)</strong></p>
          </div>
        </div>
      </div>

      {/* KPI Cards: Fulfillment Rate, Response Times, Active Givers */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-1">
          <p className="text-xs text-slate-500 font-medium">Verified Active Givers</p>
          <p className="text-2xl font-extrabold text-slate-900">{data?.active_givers_count ?? 50}</p>
          <p className="text-[11px] text-teal-600 font-medium">Target met &bull; Ready for scale</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-1">
          <p className="text-xs text-slate-500 font-medium">Request Fulfillment Rate</p>
          <p className="text-2xl font-extrabold text-slate-900">{data?.fulfillment_metrics?.fulfilled_percentage ?? 78}%</p>
          <p className="text-[11px] text-emerald-600 font-medium">&uarr; Exceeds 60% in 72h benchmark</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-1">
          <p className="text-xs text-slate-500 font-medium">Avg Response Time</p>
          <p className="text-2xl font-extrabold text-slate-900">{data?.fulfillment_metrics?.avg_response_hours ?? 4.2}h</p>
          <p className="text-[11px] text-teal-600 font-medium">Within 72h pilot SLA</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-1">
          <p className="text-xs text-slate-500 font-medium">Open Moderation Reports</p>
          <p className="text-2xl font-extrabold text-rose-600">{data?.reports_queue?.length ?? 1}</p>
          <p className="text-[11px] text-rose-600 font-medium">Requires Admin resolution</p>
        </div>
      </div>

      {/* Main Grid: Verification Queue & Skill Gaps */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Alumni Verification Queue (F2) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Alumni Verification Queue (F2)</h2>
              <p className="text-xs text-slate-500">Cross-referenced against official university student graduation lists</p>
            </div>
            <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
              {data?.verification_queue?.length ?? 2} Pending Review
            </span>
          </div>

          <div className="space-y-3">
            <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-xs">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-sm text-slate-900">Nikhil Aggarwal</h3>
                    <span className="text-[10px] bg-amber-50 text-amber-700 font-bold px-2 py-0.5 rounded border border-amber-200">
                      Pending Verification
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-0.5">
                    Batch: <strong className="text-slate-800">2020 B.Tech CSE</strong> &bull; Employer: <strong className="text-slate-800">Microsoft India</strong>
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <button className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg font-medium">
                    Reject
                  </button>
                  <button className="px-4 py-1.5 text-xs bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-semibold shadow-2xs">
                    Approve Alumnus
                  </button>
                </div>
              </div>

              <div className="bg-slate-50 rounded-lg p-2.5 text-xs flex items-center justify-between text-slate-600">
                <span>CSV Match Score: <strong className="text-emerald-700 font-bold">100% Match</strong> (Roll No: 2016045)</span>
                <span>Work Email: <code className="text-slate-800 font-mono text-[11px]">nikhil@microsoft.com</code></span>
              </div>
            </div>
          </div>

          {/* Safety & Moderation Queue (F24, F32) */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-sm text-slate-900">Incident Review & Scam Queue (F31, F32)</h3>
              <span className="text-[10px] bg-rose-50 text-rose-700 font-bold px-2 py-0.5 rounded border border-rose-200">
                1 Flagged
              </span>
            </div>

            <div className="p-3 bg-rose-50/50 border border-rose-200/80 rounded-lg space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-rose-900">Flagged Chat Message: Off-platform payment request</span>
                <span className="text-[10px] text-rose-600 font-medium">Scam Rule #14 Triggered</span>
              </div>
              <p className="text-slate-600">
                User requested payment via UPI instead of platform escrow wallet. Message was automatically intercepted and quarantined.
              </p>
              <div className="flex items-center justify-end space-x-2 pt-1">
                <button className="px-2.5 py-1 text-xs bg-slate-200 text-slate-700 rounded hover:bg-slate-300">Dismiss</button>
                <button className="px-3 py-1 text-xs bg-rose-600 text-white font-semibold rounded hover:bg-rose-700">Suspend Account</button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Skill Gap Analysis (F28) */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-2xs">
            <h3 className="font-bold text-sm text-slate-900">Skill Gap Analysis (F28)</h3>
            <p className="text-xs text-slate-500">
              Compares high-frequency student requests against active alumni mentor supply
            </p>

            <div className="space-y-3 pt-1">
              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className="text-slate-700">LLM Fine-Tuning & RAG</span>
                  <span className="text-rose-600 font-bold">Deficit (-42%)</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div className="bg-rose-500 h-2 rounded-full" style={{ width: "28%" }}></div>
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">85 Student asks vs 4 Givers</p>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className="text-slate-700">Distributed Systems</span>
                  <span className="text-emerald-600 font-bold">Balanced (+15%)</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: "75%" }}></div>
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">40 Student asks vs 18 Givers</p>
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium mb-1">
                  <span className="text-slate-700">Product Management</span>
                  <span className="text-amber-600 font-bold">Tight (-18%)</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2">
                  <div className="bg-amber-500 h-2 rounded-full" style={{ width: "45%" }}></div>
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">32 Student asks vs 7 Givers</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
