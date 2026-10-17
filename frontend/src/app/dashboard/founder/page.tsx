"use client";

import React, { useEffect, useState } from "react";
import { fetchDashboard, getStoredUser, UserSession } from "@/lib/api";
import Link from "next/link";

export default function FounderDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
    fetchDashboard("founder")
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load founder dashboard");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-slate-500">
        <div className="inline-block w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium">Loading Founder Portal...</p>
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
              Sign In as Founder
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Founder Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200 flex items-center gap-1">
              Verified Founder &bull; DPIIT / MCA Registered
            </span>
            <span className="text-xs text-slate-400">&bull;</span>
            <span className="text-xs font-semibold text-slate-600">Postman / API Tools Ecosystem</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
            {data?.user?.full_name || "Kunal Founder"}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Startup: <strong className="text-slate-800">API Infra Platform (Series A)</strong> &bull; Looking for founding engineers & interns
          </p>
        </div>

        <button className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs rounded-xl shadow-xs transition">
          Host Founder AMA / Office Hour
        </button>
      </div>

      {/* Main Grid: Founder Office Hours & Candidate Pool */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">High-Proof Student Builders</h2>
              <p className="text-xs text-slate-500">Filtered by open-source contributions, hackathon wins, and verified code repositories</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:border-amber-300 shadow-xs space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-sm text-slate-900">Aarav Sharma</h3>
                  <p className="text-xs text-slate-600">IIIT Delhi &bull; Built distributed task scheduler with raft consensus</p>
                </div>
                <button className="px-3 py-1.5 text-xs font-semibold bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition">
                  Book 15-min Founder Chat
                </button>
              </div>

              <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-500">
                <span className="bg-slate-100 px-2 py-0.5 rounded font-mono">Go / Raft</span>
                <span className="bg-slate-100 px-2 py-0.5 rounded font-mono">PostgreSQL</span>
                <span className="bg-slate-100 px-2 py-0.5 rounded font-mono">FastAPI</span>
                <span className="text-teal-600 font-semibold ml-auto">Verified GitHub Commits &check;</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Upcoming Office Hours */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-slate-900">Founder Office Hours</h3>
            <p className="text-xs text-slate-500">1:1 slots for high-conviction student founders</p>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-xs space-y-1">
              <p className="font-semibold text-slate-800">Saturday, 11:00 AM - 1:00 PM</p>
              <p className="text-slate-500 text-[11px]">3 of 4 student slots booked</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
