"use client";

import React, { useEffect, useState } from "react";
import { fetchDashboard, getStoredUser, UserSession } from "@/lib/api";
import Link from "next/link";

export default function AlumniDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
    fetchDashboard("alumni")
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load alumni dashboard");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-slate-500">
        <div className="inline-block w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium">Loading Alumni Portal...</p>
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
              Sign In as Alumni
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
            <span className="text-xs font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2.5 py-0.5 rounded border border-teal-200">
              Verified Alumnus &bull; Class of 2021
            </span>
            <span className="text-xs text-slate-400">&bull;</span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              {data?.profile?.giver_band || "Top Rated"} Giver
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
            {data?.user?.full_name || "Vikram Malhotra"}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {data?.profile?.designation || "Senior Software Engineer"} @ <strong className="text-slate-800 font-semibold">{data?.profile?.company || "Google"}</strong> &bull; Rating: <strong className="text-slate-900 font-semibold">★ {data?.profile?.avg_rating || "4.9"}</strong> ({data?.profile?.total_sessions || 12} completed sessions)
          </p>
        </div>

        {/* Capacity & Response Metrics */}
        <div className="flex items-center gap-4 bg-slate-50 border border-slate-200/80 p-3.5 rounded-xl">
          <div>
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Weekly Capacity</p>
            <p className="text-base font-bold text-slate-900">
              {data?.capacity?.active_slots_this_week ?? 2} / {data?.capacity?.weekly_cap ?? 3} <span className="text-xs font-normal text-slate-500">booked</span>
            </p>
          </div>
          <div className="border-l border-slate-200 pl-3">
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Reply Time / Rate</p>
            <p className="text-xs font-semibold text-teal-700">
              ~{data?.availability?.avg_reply_minutes ?? 120} min &bull; {data?.availability?.response_rate ?? 95}% rate
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: Incoming Student Requests & Capacity Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Incoming Student Asks */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Incoming Mentee Requests</h2>
              <p className="text-xs text-slate-500">Intent-refined asks from verified students (No cold-spam)</p>
            </div>
            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded font-medium">
              Protected In-App Comms
            </span>
          </div>

          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:border-teal-500/50 shadow-xs space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-sm text-slate-900">Aarav Sharma</h3>
                    <span className="text-[10px] bg-blue-50 text-blue-700 font-semibold px-2 py-0.5 rounded border border-blue-200">
                      3rd Year, B.Tech CS (IIIT-D)
                    </span>
                    <span className="text-[10px] text-teal-700 font-bold bg-teal-50 px-1.5 py-0.5 rounded">
                      Same-College (Free)
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Requested: <strong className="text-slate-800">System Design Review for High-Throughput Log Aggregator</strong>
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400">Received 3 hours ago</span>
                </div>
              </div>

              {/* Request Quality & Intent Details (F6, F7) */}
              <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3 space-y-1.5 text-xs">
                <div className="flex items-center space-x-1.5 text-slate-700 font-medium text-[11px]">
                  <span className="text-teal-600 font-bold">&check; Intent Quality Verified:</span>
                  <span>Student provided GitHub repo link + architecture diagram + 3 specific bottlenecks.</span>
                </div>
                <p className="text-slate-600 text-xs italic bg-white p-2 rounded border border-slate-100">
                  &ldquo;I have built an initial event pipeline in Go and Kafka, but I am facing partitioning rebalance lag under bursty loads. Looking for 30 minutes of guidance on custom partitioners and consumer backpressure.&rdquo;
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-slate-500">Proposed Slot: Tomorrow, 6:00 PM - 6:30 PM (Google Meet)</span>
                <div className="flex items-center space-x-2">
                  <button className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors">
                    Decline
                  </button>
                  <button className="px-4 py-1.5 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-2xs transition-colors">
                    Accept & Schedule
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Capacity, Escrow, and Vouching Controls */}
        <div className="space-y-6">
          {/* Capacity Control Box (F12) */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-slate-900">Safety & Capacity Gate</h3>
            <p className="text-xs text-slate-500">
              Prevents mentor burnout. Once your weekly cap is reached, WarmPath auto-hides you from new student discovery.
            </p>

            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">Weekly Capacity Cap:</span>
                <span className="font-bold text-slate-900">3 sessions / week</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">Monthly Free Sessions:</span>
                <span className="font-bold text-teal-600">4 / 4 fulfilled</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600 font-medium">Current Status:</span>
                <span className="font-bold text-emerald-600 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
                  Active Now
                </span>
              </div>
            </div>
          </div>

          {/* Cross-College Earnings & Escrow (F18) */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-slate-900">Earnings & Escrow (Cross-College)</h3>
            <p className="text-xs text-slate-500">
              Cross-college sessions payout in credits released after completion and rating (80% giver / 20% platform fee).
            </p>
            <div className="pt-2 flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500">Available Balance</p>
                <p className="text-lg font-bold text-slate-900">140 <span className="text-xs text-slate-500 font-normal">credits</span></p>
              </div>
              <button className="text-xs bg-slate-900 text-white font-semibold px-3 py-1.5 rounded-lg hover:bg-teal-600 transition">
                Redeem Credits
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
