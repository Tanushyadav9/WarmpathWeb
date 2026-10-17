"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { loginAsRole, resetDatabase, getStoredUser, UserSession } from "@/lib/api";

const ROLES = [
  { id: "student", label: "Student", persona: "Aarav Sharma (IIITD)", path: "/dashboard/student", color: "bg-blue-600" },
  { id: "alumni", label: "Alumni", persona: "Vikram Malhotra (Google)", path: "/dashboard/alumni", color: "bg-teal-600" },
  { id: "faculty", label: "Faculty", persona: "Dr. Pankaj (AI/ML)", path: "/dashboard/faculty", color: "bg-indigo-600" },
  { id: "recruiter", label: "Recruiter", persona: "Priya (Razorpay)", path: "/dashboard/recruiter", color: "bg-purple-600" },
  { id: "founder", label: "Founder", persona: "Kunal (Postman)", path: "/dashboard/founder", color: "bg-amber-600" },
  { id: "institution_admin", label: "Admin", persona: "Dr. Arvind (IIITD)", path: "/dashboard/admin", color: "bg-rose-600" },
];

export default function DemoSwitcher() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserSession | null>(null);
  const [loadingRole, setLoadingRole] = useState<string | null>(null);
  const [resetting, setResetting] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setCurrentUser(getStoredUser());
  }, []);

  const handleSwitch = async (roleId: string, path: string) => {
    try {
      setLoadingRole(roleId);
      const res = await loginAsRole(roleId);
      setCurrentUser(res.user);
      setMessage(`Switched to ${res.user.full_name} (${res.user.role})`);
      setTimeout(() => setMessage(null), 3500);
      router.push(path);
      router.refresh();
    } catch (err: any) {
      alert("Failed to switch persona: " + err.message);
    } finally {
      setLoadingRole(null);
    }
  };

  const handleReset = async () => {
    if (!confirm("Are you sure you want to reset the database to original demo seed state?")) {
      return;
    }
    try {
      setResetting(true);
      await resetDatabase();
      setMessage("Database successfully reset to pristine seed state!");
      setTimeout(() => setMessage(null), 4000);
      router.refresh();
      window.location.reload();
    } catch (err: any) {
      alert("Failed to reset database: " + err.message);
    } finally {
      setResetting(false);
    }
  };

  return (
    <aside aria-label="Demo Persona Switcher" className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur-md border-t border-slate-700/80 text-white px-4 py-2.5 shadow-2xl">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Left: Indicator */}
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-coral-500/20 text-coral-300 border border-coral-500/30 tracking-wide uppercase">
            Demo Mode Active
          </span>
          <span className="hidden sm:inline text-slate-400">|</span>
          <span className="text-slate-300 hidden sm:inline">
            Active: <strong className="text-teal-400 font-semibold">{currentUser?.full_name || "Guest"}</strong>{" "}
            {currentUser?.role ? `(${currentUser.role})` : ""}
          </span>
        </div>

        {/* Center: Persona Switcher Buttons */}
        <div className="flex items-center flex-wrap gap-1.5">
          <span className="text-slate-400 mr-1 hidden md:inline font-medium">Switch Persona:</span>
          {ROLES.map((r) => {
            const isActive = currentUser?.role === r.id;
            return (
              <button
                key={r.id}
                onClick={() => handleSwitch(r.id, r.path)}
                disabled={loadingRole !== null || resetting}
                title={r.persona}
                className={`px-2.5 py-1 rounded-md font-medium transition-all duration-150 flex items-center space-x-1 ${
                  isActive
                    ? "bg-teal-500 text-navy-900 font-bold ring-2 ring-teal-300 shadow"
                    : "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600"
                } disabled:opacity-50`}
              >
                <span>{r.label}</span>
                {loadingRole === r.id && (
                  <span className="inline-block w-2.5 h-2.5 border-2 border-current border-t-transparent rounded-full animate-spin ml-1" />
                )}
              </button>
            );
          })}
        </div>

        {/* Right: Reset Demo DB Button & Toast */}
        <div className="flex items-center space-x-2">
          {message && (
            <span className="text-emerald-400 font-medium text-[11px] animate-pulse bg-emerald-950/60 border border-emerald-700/50 px-2 py-0.5 rounded">
              {message}
            </span>
          )}
          <button
            onClick={handleReset}
            disabled={resetting}
            title="Reset all tables back to the initial demo seed dataset"
            className="px-3 py-1 bg-coral-600 hover:bg-coral-700 text-white font-medium rounded-md transition-colors flex items-center space-x-1 shadow disabled:opacity-50"
          >
            <svg
              className={`w-3.5 h-3.5 ${resetting ? "animate-spin" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>{resetting ? "Resetting..." : "Reset Demo DB"}</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
