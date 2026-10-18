"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  sendOtp,
  registerAlumni,
  registerEmployer,
  uploadDocument,
  requestPeerVouches,
} from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();

  // Mode: "alumni_faculty" or "employer"
  const [roleGroup, setRoleGroup] = useState<"alumni_faculty" | "employer">("alumni_faculty");
  const [role, setRole] = useState("alumni"); // alumni, faculty, recruiter, founder

  // Common Fields
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [institutionId, setInstitutionId] = useState(1);
  const [batch, setBatch] = useState(2021);
  const [branch, setBranch] = useState("Computer Science");
  const [company, setCompany] = useState("");
  const [headline, setHeadline] = useState("");

  // Employer Specific Fields
  const [cin, setCin] = useState("");
  const [gstin, setGstin] = useState("");

  // OTP State
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [demoOtp, setDemoOtp] = useState<string | null>(null);
  const [sendingOtp, setSendingOtp] = useState(false);

  // Submission & Result States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  // Fallback Action States
  const [docRef, setDocRef] = useState("");
  const [docNotes, setDocNotes] = useState("");
  const [docSubmitted, setDocSubmitted] = useState(false);
  const [vouchersInput, setVouchersInput] = useState("vikram.malhotra@alumni.iiitd.ac.in, tanmay.bhatia@alumni.iiitd.ac.in");
  const [vouchSubmitted, setVouchSubmitted] = useState(false);

  const handleSendOtp = async () => {
    if (!email || !email.includes("@")) {
      setError("Please enter a valid email address first.");
      return;
    }
    setError(null);
    setSendingOtp(true);
    try {
      const res = await sendOtp(email, roleGroup === "employer" ? "employer_registration" : "alumni_registration");
      setOtpSent(true);
      if (res.demo_otp) {
        setDemoOtp(res.demo_otp);
      }
    } catch (err: any) {
      setError(err.message || "Failed to send OTP");
    } finally {
      setSendingOtp(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (roleGroup === "alumni_faculty") {
        const res = await registerAlumni({
          role,
          full_name: fullName,
          email,
          password,
          institution_id: Number(institutionId),
          batch: Number(batch),
          branch,
          otp_code: otpCode,
          company,
          headline,
        });
        setResult(res);
      } else {
        const res = await registerEmployer({
          role,
          full_name: fullName,
          email,
          password,
          company,
          headline,
          cin: cin.trim() || undefined,
          gstin: gstin.trim() || undefined,
          otp_code: otpCode,
        });
        setResult(res);
      }
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleUploadDoc = async () => {
    if (!docRef) return;
    try {
      await uploadDocument(docRef, "degree_certificate", docNotes);
      setDocSubmitted(true);
    } catch (err: any) {
      alert("Document upload error: " + err.message);
    }
  };

  const handlePeerVouches = async () => {
    const emails = vouchersInput
      .split(",")
      .map((e) => e.trim())
      .filter((e) => e.length > 0);
    if (emails.length < 2) {
      alert("Please provide at least two verified batchmate emails.");
      return;
    }
    try {
      await requestPeerVouches(emails, "Batchmate graduation confirmation");
      setVouchSubmitted(true);
    } catch (err: any) {
      alert("Peer vouch request error: " + err.message);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 space-y-8">
      {/* Page Title */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-1.5 bg-teal-50 border border-teal-200 text-teal-800 text-xs px-3 py-1 rounded-full font-semibold">
          <span>Layered Multi-Channel Verification</span>
          <span>&bull;</span>
          <span>F2 & F3</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
          Join WarmPath Network
        </h1>
        <p className="text-sm text-slate-500 max-w-xl mx-auto">
          Trust first, networking second. Institution-verified alumni credentials, zero cold-spam.
        </p>
      </div>

      {/* Role Group Selector */}
      <div className="flex justify-center">
        <div className="bg-slate-100 p-1.5 rounded-2xl flex space-x-1.5 border border-slate-200">
          <button
            type="button"
            onClick={() => {
              setRoleGroup("alumni_faculty");
              setRole("alumni");
              setResult(null);
            }}
            className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${
              roleGroup === "alumni_faculty"
                ? "bg-white text-teal-800 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Alumni & Faculty Mentor
          </button>
          <button
            type="button"
            onClick={() => {
              setRoleGroup("employer");
              setRole("recruiter");
              setResult(null);
            }}
            className={`px-5 py-2 rounded-xl text-xs font-bold transition-all ${
              roleGroup === "employer"
                ? "bg-white text-purple-800 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Recruiter & Founder (Employers)
          </button>
        </div>
      </div>

      {/* Verification Success or Fallback View */}
      {result ? (
        <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm space-y-6 animate-in fade-in">
          {result.auto_approved || result.user?.verification_level === "verified_professional" ? (
            <div className="space-y-4 text-center">
              <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto shadow-inner">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-extrabold text-slate-900">
                {result.auto_approved
                  ? "Identity Verified! Welcome, Verified Alumnus"
                  : "Employer Verified! Welcome, Verified Professional"}
              </h2>
              <p className="text-xs text-slate-600 max-w-lg mx-auto">
                {result.auto_approved
                  ? "Your email, name, and graduation batch matched IIIT Delhi's official alumni roster. Your Verified Alumnus badge is active."
                  : "Your corporate email and statutory credentials have been verified. You can now post jobs and connect with students."}
              </p>
              <div className="pt-4 flex justify-center gap-3">
                <Link
                  href={role === "alumni" ? "/dashboard/alumni" : role === "faculty" ? "/dashboard/faculty" : role === "recruiter" ? "/dashboard/recruiter" : "/dashboard/founder"}
                  className="px-6 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs rounded-xl shadow-sm transition"
                >
                  Enter Portal &rarr;
                </Link>
              </div>
            </div>
          ) : (
            /* Fallback Paths View */
            <div className="space-y-6">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-start space-x-3 text-amber-900 text-xs">
                <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <strong className="font-bold">Verification Pending (No Immediate Roster Match):</strong>
                  <p className="mt-0.5">
                    Your details did not match IIIT Delhi's digital roster list. Choose one of the 2 verification fallbacks below:
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                {/* Fallback A: Document Upload */}
                <div className="border border-slate-200 rounded-2xl p-5 space-y-4 bg-slate-50/50">
                  <div className="flex items-center space-x-2">
                    <span className="w-6 h-6 rounded-full bg-teal-100 text-teal-800 text-xs font-bold flex items-center justify-center">A</span>
                    <h3 className="font-bold text-sm text-slate-900">Upload Degree / College ID</h3>
                  </div>
                  <p className="text-xs text-slate-500">
                    Upload your graduation degree certificate or past student ID card for admin manual review.
                  </p>

                  {docSubmitted ? (
                    <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl font-medium">
                      &check; Document submitted and queued for admin review!
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <input
                        type="text"
                        value={docRef}
                        onChange={(e) => setDocRef(e.target.value)}
                        placeholder="File link or filename (e.g. degree_cert.pdf)"
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl bg-white"
                      />
                      <input
                        type="text"
                        value={docNotes}
                        onChange={(e) => setDocNotes(e.target.value)}
                        placeholder="Additional roll number or remarks"
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl bg-white"
                      />
                      <button
                        onClick={handleUploadDoc}
                        disabled={!docRef}
                        className="w-full py-2 bg-slate-900 text-white text-xs font-semibold rounded-xl hover:bg-teal-600 transition disabled:opacity-50"
                      >
                        Submit Document for Review
                      </button>
                    </div>
                  )}
                </div>

                {/* Fallback B: Peer Vouching */}
                <div className="border border-slate-200 rounded-2xl p-5 space-y-4 bg-slate-50/50">
                  <div className="flex items-center space-x-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-800 text-xs font-bold flex items-center justify-center">B</span>
                    <h3 className="font-bold text-sm text-slate-900">Peer Vouching (2 Batchmates)</h3>
                  </div>
                  <p className="text-xs text-slate-500">
                    Ask two verified alumni from the same graduation year to confirm your credentials. Approval requires both.
                  </p>

                  {vouchSubmitted ? (
                    <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl font-medium">
                      &check; Vouch requests dispatched to batchmates!
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <input
                        type="text"
                        value={vouchersInput}
                        onChange={(e) => setVouchersInput(e.target.value)}
                        placeholder="alumni1@iiitd.ac.in, alumni2@iiitd.ac.in"
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl bg-white"
                      />
                      <p className="text-[10px] text-slate-400">Comma-separated emails of 2 verified batchmates.</p>
                      <button
                        onClick={handlePeerVouches}
                        className="w-full py-2 bg-indigo-600 text-white text-xs font-semibold rounded-xl hover:bg-indigo-700 transition"
                      >
                        Send Peer Vouch Requests
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Registration Form */
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center space-x-2">
              <svg className="w-4 h-4 text-rose-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-5">
            {/* Role Radio Pills */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">Select Role</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {roleGroup === "alumni_faculty" ? (
                  <>
                    <button
                      type="button"
                      onClick={() => setRole("alumni")}
                      className={`p-2.5 rounded-xl border text-xs font-semibold text-center transition ${
                        role === "alumni"
                          ? "bg-teal-50 border-teal-500 text-teal-800 ring-1 ring-teal-500"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      Alumni (Giver)
                    </button>
                    <button
                      type="button"
                      onClick={() => setRole("faculty")}
                      className={`p-2.5 rounded-xl border text-xs font-semibold text-center transition ${
                        role === "faculty"
                          ? "bg-indigo-50 border-indigo-500 text-indigo-800 ring-1 ring-indigo-500"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      Faculty (Domain Mentor)
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => setRole("recruiter")}
                      className={`p-2.5 rounded-xl border text-xs font-semibold text-center transition ${
                        role === "recruiter"
                          ? "bg-purple-50 border-purple-500 text-purple-800 ring-1 ring-purple-500"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      Recruiter (Talent)
                    </button>
                    <button
                      type="button"
                      onClick={() => setRole("founder")}
                      className={`p-2.5 rounded-xl border text-xs font-semibold text-center transition ${
                        role === "founder"
                          ? "bg-amber-50 border-amber-500 text-amber-800 ring-1 ring-amber-500"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      Founder (Startup)
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Basic Info */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Full Legal Name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Rohan Gupta"
                  className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  {roleGroup === "alumni_faculty" ? "Registered College Email" : "Corporate Work Email"}
                </label>
                <div className="flex gap-2">
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={roleGroup === "alumni_faculty" ? "rohan.gupta@alumni.iiitd.ac.in" : "rohan@company.com"}
                    className="flex-1 px-3.5 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={handleSendOtp}
                    disabled={sendingOtp || !email}
                    className="px-3.5 py-2 bg-slate-900 hover:bg-teal-600 text-white font-semibold text-xs rounded-xl transition disabled:opacity-50 whitespace-nowrap"
                  >
                    {sendingOtp ? "Sending..." : "Send OTP"}
                  </button>
                </div>
              </div>
            </div>

            {/* DEMO_MODE Debug Panel for OTP */}
            {demoOtp && (
              <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl text-teal-900 text-xs flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-[10px] bg-teal-600 text-white px-2 py-0.5 rounded uppercase">
                    Demo OTP Mock
                  </span>
                  <span>Received Code: <strong className="font-mono text-sm tracking-wider font-extrabold">{demoOtp}</strong></span>
                </div>
                <button
                  type="button"
                  onClick={() => setOtpCode(demoOtp)}
                  className="text-xs text-teal-700 hover:underline font-bold"
                >
                  Auto-Fill OTP &rarr;
                </button>
              </div>
            )}

            {/* OTP Code & Password */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">6-Digit Verification OTP</label>
                <input
                  type="text"
                  required
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  placeholder="e.g. 123456"
                  className="w-full px-3.5 py-2 text-xs font-mono tracking-widest border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Account Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Role Specific Fields: College/Batch or Company/CIN/GST */}
            {roleGroup === "alumni_faculty" ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-slate-100 pt-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Institution</label>
                  <select
                    value={institutionId}
                    onChange={(e) => setInstitutionId(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-xl bg-white"
                  >
                    <option value={1}>IIIT Delhi</option>
                    <option value={2}>IIT Delhi</option>
                    <option value={3}>BITS Pilani</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Graduation Batch</label>
                  <input
                    type="number"
                    required
                    value={batch}
                    onChange={(e) => setBatch(Number(e.target.value))}
                    className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Branch / Major</label>
                  <input
                    type="text"
                    required
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="Computer Science"
                    className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-xl"
                  />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-slate-100 pt-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Company / Organization</label>
                  <input
                    type="text"
                    required
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    placeholder="e.g. Razorpay Software"
                    className="w-full px-3.5 py-2 text-xs border border-slate-300 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Corporate CIN (Optional)</label>
                  <input
                    type="text"
                    value={cin}
                    onChange={(e) => setCin(e.target.value)}
                    placeholder="21-digit CIN (U72900DL2021PTC123456)"
                    className="w-full px-3.5 py-2 text-xs font-mono border border-slate-300 rounded-xl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">GSTIN Number (Optional)</label>
                  <input
                    type="text"
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value)}
                    placeholder="15-digit GST (07AAAAA0000A1Z5)"
                    className="w-full px-3.5 py-2 text-xs font-mono border border-slate-300 rounded-xl"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !otpCode}
              className="w-full py-3 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-xl shadow-sm transition disabled:opacity-50"
            >
              {loading ? "Verifying Credentials..." : "Complete Registration & Verify"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
