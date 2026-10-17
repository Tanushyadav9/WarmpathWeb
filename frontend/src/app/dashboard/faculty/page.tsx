"use client";

import React, { useEffect, useState } from "react";
import { fetchDashboard, getStoredUser, UserSession } from "@/lib/api";
import Link from "next/link";

export default function FacultyDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
    fetchDashboard("faculty")
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load faculty dashboard");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-slate-500">
        <div className="inline-block w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium">Loading Faculty Portal...</p>
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
              Sign In as Faculty
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Faculty Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded border border-indigo-200">
              Verified Faculty Expert
            </span>
            <span className="text-xs text-slate-400">&bull;</span>
            <span className="text-xs font-medium text-slate-600">Department of Computer Science & AI</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-1">
            {data?.user?.full_name || "Dr. Pankaj"}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Specialization: <strong className="text-slate-800 font-semibold">Deep Learning, NLP & Distributed Graph Processing</strong> &bull; IIIT Delhi
          </p>
        </div>

        {/* Honorarium / Time Compensation (F25) */}
        <div className="bg-slate-50 border border-slate-200/80 p-3.5 rounded-xl">
          <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Faculty Mentor Honorarium</p>
          <p className="text-base font-bold text-slate-900">
            Compensated Time: <span className="text-indigo-600">60 credits / hour</span>
          </p>
          <p className="text-[10px] text-slate-400 mt-0.5">Subsidized by institutional endowment fund</p>
        </div>
      </div>

      {/* Main Grid: Academic Consultations & Research Guidance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Academic & Project Consultation Requests</h2>
              <p className="text-xs text-slate-500">Students seeking thesis, research paper, or domain problem advice</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 hover:border-indigo-400 shadow-xs space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-sm text-slate-900">Rohan Verma &bull; Final Year B.Tech</h3>
                  <p className="text-xs text-slate-600 mt-0.5 font-medium">
                    Topic: <strong className="text-slate-800">Fine-tuning LoRA adapters on low-resource Indic languages</strong>
                  </p>
                </div>
                <span className="text-[10px] bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded border border-indigo-200">
                  Research Review
                </span>
              </div>

              <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                &ldquo;We have evaluated quantized 4-bit Llama-3 checkpoints on Hindi datasets and need advice on parameter budget allocation and validation metrics before drafting our ACL submission.&rdquo;
              </p>

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-slate-400">Preferred window: Friday, 3:00 PM - 3:45 PM</span>
                <div className="flex items-center space-x-2">
                  <button className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg">Decline</button>
                  <button className="px-4 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition">
                    Accept Consultation
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Office Hours & Verified Profile */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-2xs">
            <h3 className="font-bold text-sm text-slate-900">Office Hours Schedule</h3>
            <p className="text-xs text-slate-500">Fixed institutional advising slots synced with Google Calendar</p>
            <div className="space-y-2 text-xs pt-2">
              <div className="flex items-center justify-between p-2 rounded bg-slate-50">
                <span className="font-medium text-slate-700">Tuesdays: 4:00 PM - 5:30 PM</span>
                <span className="text-emerald-600 font-semibold text-[11px]">Open (1 slot left)</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-50">
                <span className="font-medium text-slate-700">Thursdays: 3:00 PM - 4:30 PM</span>
                <span className="text-slate-400 font-semibold text-[11px]">Fully Booked</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
