"use client";

import React, { useEffect, useState } from "react";
import {
  fetchDashboard,
  getStoredUser,
  UserSession,
  fetchVerificationQueue,
  adminVerifyAction,
  previewRosterCsv,
  uploadRosterCsv,
} from "@/lib/api";
import Link from "next/link";

export default function AdminDashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  // Live Verification Queue State
  const [pendingQueue, setPendingQueue] = useState<any[]>([]);
  const [reviewReason, setReviewReason] = useState<{ [key: string]: string }>({});
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // CSV Roster Upload State
  const [csvContent, setCsvContent] = useState(
    "Name,Email,Batch,Branch,Roll_Number\n" +
    "Divya Mittal,divya.mittal@alumni.iiitd.ac.in,2021,Computer Science,2017056\n" +
    "Anoop Kashyap,anoop@alumni.iiitd.ac.in,2022,ECE,2018041\n" +
    "Error Test Row,invalid-email-address,2020,Computer Science,2016099\n" +
    "Karan Saxena,karan.saxena@alumni.iiitd.ac.in,not-a-year,Computer Science,2017088"
  );
  const [csvPreview, setCsvPreview] = useState<any>(null);
  const [csvUploading, setCsvUploading] = useState(false);
  const [csvMessage, setCsvMessage] = useState<string | null>(null);

  const loadAdminData = async () => {
    try {
      setLoading(true);
      const dash = await fetchDashboard("admin");
      setData(dash);
      const qRes = await fetchVerificationQueue();
      if (qRes && qRes.queue) {
        setPendingQueue(qRes.queue);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load institution admin dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setUser(getStoredUser());
    loadAdminData();
  }, []);

  const handleVerifyAction = async (requestId: string, action: "approve" | "reject") => {
    const reason = reviewReason[requestId] || (action === "approve" ? "Verified against university records" : "Degree document could not be validated");
    try {
      setActionLoading(requestId);
      await adminVerifyAction(requestId, action, reason);
      setActionSuccess(`Request ${action === "approve" ? "Approved" : "Rejected"}: ${reason}`);
      setTimeout(() => setActionSuccess(null), 4000);
      // Remove from local queue
      setPendingQueue((prev) => prev.filter((r) => r.request_id !== requestId));
    } catch (err: any) {
      alert("Action error: " + err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePreviewCsv = async () => {
    try {
      setCsvMessage(null);
      const res = await previewRosterCsv(csvContent);
      setCsvPreview(res);
    } catch (err: any) {
      alert("Preview error: " + err.message);
    }
  };

  const handleUploadCsv = async () => {
    try {
      setCsvUploading(true);
      setCsvMessage(null);
      const res = await uploadRosterCsv(1, csvContent, false);
      setCsvMessage(`Successfully committed ${res.records_imported} valid alumni records (${res.errors_skipped} invalid rows skipped).`);
      setCsvPreview(null);
      setTimeout(() => setCsvMessage(null), 5000);
    } catch (err: any) {
      alert("Upload error: " + err.message);
    } finally {
      setCsvUploading(false);
    }
  };

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
            <span className="text-xs font-semibold text-slate-700">
              Indraprastha Institute of Information Technology Delhi (IIIT-D)
            </span>
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
            <p className="font-semibold text-slate-800">
              50 Verified Givers Gate: <strong className="text-emerald-600 font-bold">Passed (50/50)</strong>
            </p>
          </div>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-center space-x-2 animate-in fade-in">
          <svg className="w-4 h-4 text-emerald-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          <span className="font-medium">{actionSuccess}</span>
        </div>
      )}

      {/* KPI Cards */}
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
          <p className="text-xs text-slate-500 font-medium">Pending Verifications</p>
          <p className="text-2xl font-extrabold text-rose-600">{pendingQueue.length}</p>
          <p className="text-[11px] text-rose-600 font-medium">Awaiting Admin decision</p>
        </div>
      </div>

      {/* Main Grid: Live Verification Review Queue & CSV Upload Manager */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Cols: Live Verification Review Queue (F2, F3) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Alumni Verification Review Queue (F2)</h2>
              <p className="text-xs text-slate-500">Degree certificate uploads, employer validations, and pending appeals</p>
            </div>
            <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
              {pendingQueue.length} Pending Actions
            </span>
          </div>

          <div className="space-y-4">
            {pendingQueue.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-xs text-slate-400">
                &check; Verification queue is completely clear! All alumni and employers verified.
              </div>
            ) : (
              pendingQueue.map((req) => (
                <div
                  key={req.request_id}
                  className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="font-bold text-sm text-slate-900">{req.full_name}</h3>
                        <span className="text-[10px] bg-amber-50 text-amber-800 font-bold px-2 py-0.5 rounded border border-amber-200">
                          {req.request_type.replace("_", " ").toUpperCase()}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 font-semibold text-slate-600">
                          Role: {req.role}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-1">
                        Batch: <strong className="text-slate-800">{req.batch ? `Class of ${req.batch}` : "N/A"}</strong> &bull; Branch: {req.branch || "General"} &bull; Org: <strong className="text-slate-800">{req.company || "N/A"}</strong>
                      </p>
                    </div>

                    <div className="text-right text-[10px] text-slate-400">
                      Submitted: {new Date(req.submitted_at).toLocaleDateString()}
                    </div>
                  </div>

                  {/* Document and Details Reference */}
                  <div className="bg-slate-50 rounded-xl p-3 text-xs space-y-1.5 border border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600">Email: <strong className="text-slate-900 font-mono">{req.email}</strong></span>
                      {req.document_ref && (
                        <span className="text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200 font-mono text-[11px]">
                          Attached: {req.document_ref}
                        </span>
                      )}
                    </div>
                    {req.cin && (
                      <p className="text-[11px] text-slate-500 font-mono">
                        CIN: <strong className="text-slate-800">{req.cin}</strong> &bull; GSTIN: {req.gstin || "N/A"}
                      </p>
                    )}
                  </div>

                  {/* Decision Controls */}
                  <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
                    <input
                      type="text"
                      placeholder="Reason for decision (e.g. Verified against 2020 graduation ledger)"
                      value={reviewReason[req.request_id] || ""}
                      onChange={(e) =>
                        setReviewReason({ ...reviewReason, [req.request_id]: e.target.value })
                      }
                      className="flex-1 w-full px-3 py-1.5 text-xs border border-slate-300 rounded-xl"
                    />
                    <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
                      <button
                        onClick={() => handleVerifyAction(req.request_id, "reject")}
                        disabled={actionLoading === req.request_id}
                        className="px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 rounded-xl border border-rose-200 transition"
                      >
                        Reject
                      </button>
                      <button
                        onClick={() => handleVerifyAction(req.request_id, "approve")}
                        disabled={actionLoading === req.request_id}
                        className="px-4 py-1.5 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-xs transition"
                      >
                        Approve & Grant Badge
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Official Alumni CSV Roster Manager (F2) */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="font-bold text-sm text-slate-900">Upload Official Alumni CSV Roster (F2)</h3>
                <p className="text-xs text-slate-500">
                  Matches Name + Email + Batch for instant automated alumnus verification
                </p>
              </div>
              <span className="text-[11px] font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-600">
                IIIT Delhi (ID: 1)
              </span>
            </div>

            {csvMessage && (
              <div className="p-3 bg-teal-50 border border-teal-200 text-teal-800 text-xs rounded-xl font-medium">
                {csvMessage}
              </div>
            )}

            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">CSV Data (Header: Name, Email, Batch, Branch, Roll_Number)</label>
              <textarea
                rows={5}
                value={csvContent}
                onChange={(e) => setCsvContent(e.target.value)}
                className="w-full p-3 font-mono text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={handlePreviewCsv}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 border border-slate-300 rounded-xl transition"
              >
                Validate & Preview Rows
              </button>
              <button
                type="button"
                onClick={handleUploadCsv}
                disabled={csvUploading}
                className="px-4 py-1.5 text-xs font-semibold bg-slate-900 hover:bg-teal-600 text-white rounded-xl shadow-xs transition disabled:opacity-50"
              >
                {csvUploading ? "Uploading..." : "Commit Roster to Database"}
              </button>
            </div>

            {/* CSV Preview and Error Rows Display */}
            {csvPreview && (
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 space-y-3 text-xs animate-in fade-in">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">
                    Preview: {csvPreview.valid_count} Valid &bull;{" "}
                    <span className="text-rose-600">{csvPreview.error_count} Error Rows</span>
                  </span>
                  <span className="text-slate-400 text-[11px]">Total: {csvPreview.total_rows} rows</span>
                </div>

                {csvPreview.error_rows && csvPreview.error_rows.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="font-semibold text-rose-700 text-[11px]">Errors Detected (Will Be Skipped):</p>
                    {csvPreview.error_rows.map((err: any, idx: number) => (
                      <div key={idx} className="p-2 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-[11px]">
                        <strong>Line {err.line}:</strong> {err.error}
                      </div>
                    ))}
                  </div>
                )}

                {csvPreview.valid_preview && csvPreview.valid_preview.length > 0 && (
                  <div>
                    <p className="font-semibold text-emerald-700 text-[11px] mb-1">Valid Rows Preview:</p>
                    <div className="divide-y divide-slate-200 bg-white rounded-lg border border-slate-200 overflow-hidden">
                      {csvPreview.valid_preview.slice(0, 3).map((r: any, idx: number) => (
                        <div key={idx} className="p-2 flex justify-between text-[11px]">
                          <span>{r.name} ({r.email})</span>
                          <span className="font-mono text-slate-500">Batch {r.batch} &bull; {r.branch}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Skill Gaps and Moderation Rules */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 shadow-2xs">
            <h3 className="font-bold text-sm text-slate-900">Skill Gap Analysis (F28)</h3>
            <p className="text-xs text-slate-500">
              Student demand vs active verified alumni supply
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
            </div>
          </div>

          {/* Verification Badge Guidelines */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-2xs text-xs">
            <h3 className="font-bold text-sm text-slate-900">Verification Levels & Badges (F3)</h3>
            <div className="space-y-2">
              <div className="p-2 rounded-lg bg-teal-50 border border-teal-200 text-teal-900">
                <span className="font-bold">&bull; Verified Alumnus:</span> Confirmed via CSV roster match, approved document, or 2 peer vouches.
              </div>
              <div className="p-2 rounded-lg bg-purple-50 border border-purple-200 text-purple-900">
                <span className="font-bold">&bull; Verified Professional:</span> Corporate email OTP + validated CIN/GSTIN format.
              </div>
              <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900">
                <span className="font-bold">&bull; Trusted Giver:</span> Earned after 5+ completed sessions with $\ge 4.5$ star rating.
              </div>
              <div className="p-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-900">
                <span className="font-bold">&bull; Pending:</span> Hidden from student search & recommendations; blocked from posting.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
