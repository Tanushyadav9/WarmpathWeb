"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { login, loginAsRole } from "@/lib/api";

const DEMO_PERSONAS = [
  { role: "student", name: "Aarav Sharma", email: "aarav.sharma@iiitd.ac.in", desc: "Student Seeker (IIIT-D)", path: "/dashboard/student", color: "border-blue-200 bg-blue-50/50 hover:bg-blue-50" },
  { role: "alumni", name: "Vikram Malhotra", email: "vikram.malhotra@alumni.iiitd.ac.in", desc: "Senior SWE @ Google", path: "/dashboard/alumni", color: "border-teal-200 bg-teal-50/50 hover:bg-teal-50" },
  { role: "faculty", name: "Dr. Pankaj", email: "dr.pankaj@iiitd.ac.in", desc: "Dept. of AI/ML (IIIT-D)", path: "/dashboard/faculty", color: "border-indigo-200 bg-indigo-50/50 hover:bg-indigo-50" },
  { role: "recruiter", name: "Priya", email: "priya.recruiter@razorpay.com", desc: "Tech Hiring @ Razorpay", path: "/dashboard/recruiter", color: "border-purple-200 bg-purple-50/50 hover:bg-purple-50" },
  { role: "founder", name: "Kunal", email: "kunal.founder@postman.com", desc: "Founder @ API Scale", path: "/dashboard/founder", color: "border-amber-200 bg-amber-50/50 hover:bg-amber-50" },
  { role: "institution_admin", name: "Dr. Arvind Sharma", email: "admin@iiitd.ac.in", desc: "Dean / Admin @ IIIT-D", path: "/dashboard/admin", color: "border-rose-200 bg-rose-50/50 hover:bg-rose-50" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStandardLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await login(email, password);
      const role = res.user.role;
      if (role === "student") router.push("/dashboard/student");
      else if (role === "alumni") router.push("/dashboard/alumni");
      else if (role === "faculty") router.push("/dashboard/faculty");
      else if (role === "recruiter") router.push("/dashboard/recruiter");
      else if (role === "founder") router.push("/dashboard/founder");
      else if (role === "institution_admin") router.push("/dashboard/admin");
      else router.push("/");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (persona: typeof DEMO_PERSONAS[0]) => {
    setError(null);
    setLoading(true);
    try {
      await loginAsRole(persona.role);
      router.push(persona.path);
    } catch (err: any) {
      setError("Demo login failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 space-y-10">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Sign In to WarmPath</h1>
        <p className="text-sm text-slate-500">
          Institution-verified authentication with strict role-based data access
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Email & Password Form */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-900">Standard Login</h2>
            <p className="text-xs text-slate-500">Sign in with your registered college or company email</p>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center space-x-2">
              <svg className="w-4 h-4 text-rose-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleStandardLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="aarav.sharma@iiitd.ac.in"
                className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="demo1234"
                className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">Default demo password: <code className="bg-slate-100 px-1 py-0.5 rounded">demo1234</code></p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <span>{loading ? "Authenticating..." : "Sign In"}</span>
            </button>
          </form>
        </div>

        {/* Demo Persona Fast Selector */}
        <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-6 sm:p-8 space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">1-Click Demo Login</h2>
              <span className="text-[10px] bg-teal-100 text-teal-800 font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                Hackathon Jury
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Instantly authenticate as any of the 6 roles without entering passwords
            </p>
          </div>

          <div className="space-y-2.5 pt-2">
            {DEMO_PERSONAS.map((p) => (
              <button
                key={p.role}
                onClick={() => handleQuickLogin(p)}
                disabled={loading}
                className={`w-full text-left p-3 rounded-xl border transition-all duration-150 flex items-center justify-between group ${p.color} disabled:opacity-50`}
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-xs text-slate-900 group-hover:text-teal-700">
                      {p.name}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-white font-medium text-slate-600 border border-slate-200 uppercase">
                      {p.role.replace("institution_", "")}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">{p.desc}</p>
                </div>
                <span className="text-slate-400 group-hover:text-teal-600 group-hover:translate-x-1 transition-all text-xs">
                  &rarr;
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
