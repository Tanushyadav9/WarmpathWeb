"use client";

import React, { useEffect, useState } from "react";
import {
  fetchDashboard,
  getStoredUser,
  UserSession,
  fetchStudentProfile,
  uploadResumeFile,
  updateStudentProfile,
  confirmStudentProfile,
  fetchGitHubProof,
  submitGitHubProof,
  fetchConsents,
  updateConsents,
  withdrawConsent,
  exportUserData,
  deleteUserAccount,
  clearSession,
  checkIntentQuality,
  structureIntent,
  saveStudentIntent,
  fetchRecommendations,
  explainRanking,
} from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function StudentDashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"mentors" | "profile" | "proof" | "privacy">("mentors");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  // Profile & Resume state (F4)
  const [profile, setProfile] = useState<any>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [uploadingResume, setUploadingResume] = useState(false);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [editableSkills, setEditableSkills] = useState<Array<{ name: string; category?: string }>>([]);
  const [newSkillName, setNewSkillName] = useState("");
  const [newSkillCategory, setNewSkillCategory] = useState("Technical");

  // Proof of work state (F5)
  const [githubProof, setGithubProof] = useState<any>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [githubLoading, setGithubLoading] = useState(false);
  const [githubError, setGithubError] = useState<string | null>(null);

  // Consents & DPDP state (F33)
  const [consents, setConsents] = useState<Array<{ purpose: string; granted: boolean }>>([]);
  const [privacyLoading, setPrivacyLoading] = useState(false);
  const [privacyMessage, setPrivacyMessage] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Intent & Matching state (F6, F7, F8, F9, F10)
  const [intentText, setIntentText] = useState("Looking for a mock interview for backend Go and Kubernetes roles.");
  const [intentQuality, setIntentQuality] = useState<any>(null);
  const [checkingQuality, setCheckingQuality] = useState(false);
  const [isSavingIntent, setIsSavingIntent] = useState(false);
  const [structuredIntent, setStructuredIntent] = useState<any>(null);
  const [intentSavedSuccess, setIntentSavedSuccess] = useState(false);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [recsLoading, setRecsLoading] = useState(false);
  const [selectedScope, setSelectedScope] = useState<"own_college" | "cross_college">("own_college");
  const [excludedSummary, setExcludedSummary] = useState<any>(null);
  const [expandedScoreGiverId, setExpandedScoreGiverId] = useState<string | null>(null);

  // Jury Explain Ranking Panel state
  const [showExplainModal, setShowExplainModal] = useState(false);
  const [explainData, setExplainData] = useState<any>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  useEffect(() => {
    setUser(getStoredUser());
    loadDashboardData();
    loadProfileAndProof();
  }, []);

  async function loadRecommendations(scope: "own_college" | "cross_college" = selectedScope) {
    try {
      setRecsLoading(true);
      const res = await fetchRecommendations(scope);
      setRecommendations(res.items || []);
      setExcludedSummary(res.excluded_summary || null);
    } catch (err: any) {
      console.warn("Could not load recommendations", err);
    } finally {
      setRecsLoading(false);
    }
  }

  async function loadDashboardData() {
    try {
      setLoading(true);
      const [dashRes, recsRes] = await Promise.allSettled([
        fetchDashboard("student"),
        fetchRecommendations(selectedScope),
      ]);
      if (dashRes.status === "fulfilled") {
        setData(dashRes.value);
      }
      if (recsRes.status === "fulfilled" && recsRes.value) {
        setRecommendations(recsRes.value.items || []);
        setExcludedSummary(recsRes.value.excluded_summary || null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load student dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function handleCheckQuality(textToCheck: string = intentText) {
    if (!textToCheck.trim()) {
      setIntentQuality({
        quality_score: 0.0,
        is_blocked: true,
        block_reason: "Ask cannot be empty",
        feedback: ["Please describe what you want next."],
        suggested_refinement: "I need a 30-minute mock interview for backend Go and distributed systems roles.",
      });
      return;
    }
    try {
      setCheckingQuality(true);
      const q = await checkIntentQuality(textToCheck);
      setIntentQuality(q);
      return q;
    } catch (err: any) {
      console.warn("Quality check error", err);
    } finally {
      setCheckingQuality(false);
    }
  }

  async function handleSaveIntent(textToSave: string = intentText) {
    if (!textToSave.trim()) return;
    try {
      setIsSavingIntent(true);
      const q = await checkIntentQuality(textToSave);
      setIntentQuality(q);
      if (q.is_blocked) {
        return;
      }
      const res = await saveStudentIntent({ text: textToSave });
      setStructuredIntent(res.structured_intent);
      setIntentSavedSuccess(true);
      setTimeout(() => setIntentSavedSuccess(false), 4000);
      await loadRecommendations(selectedScope);
      loadDashboardData();
    } catch (err: any) {
      alert(`Failed to save intent: ${err.message}`);
    } finally {
      setIsSavingIntent(false);
    }
  }

  async function handleAcceptRefinement(suggestion: string) {
    setIntentText(suggestion);
    setIntentQuality(null);
    await handleSaveIntent(suggestion);
  }

  async function handleOpenExplainRanking() {
    try {
      setShowExplainModal(true);
      setExplainLoading(true);
      const exp = await explainRanking(selectedScope);
      setExplainData(exp);
    } catch (err: any) {
      console.warn("Ranking explanation failed", err);
    } finally {
      setExplainLoading(false);
    }
  }

  async function handleScopeChange(scope: "own_college" | "cross_college") {
    setSelectedScope(scope);
    await loadRecommendations(scope);
  }

  async function loadProfileAndProof() {
    try {
      setProfileLoading(true);
      const [profData, proofData, consentData] = await Promise.allSettled([
        fetchStudentProfile(),
        fetchGitHubProof(),
        fetchConsents(),
      ]);

      if (profData.status === "fulfilled" && profData.value) {
        setProfile(profData.value);
        if (profData.value.merged?.skills) {
          setEditableSkills(profData.value.merged.skills);
        }
      }

      if (proofData.status === "fulfilled" && proofData.value) {
        setGithubProof(proofData.value);
        if (proofData.value.repo_url) {
          setGithubUrl(proofData.value.repo_url);
        }
      }

      if (consentData.status === "fulfilled" && consentData.value) {
        setConsents(consentData.value.consents || []);
      }
    } catch (err) {
      console.warn("Could not load supplementary profile data", err);
    } finally {
      setProfileLoading(false);
    }
  }

  const isConsentGranted = (purpose: string) => {
    return consents.some((c) => c.purpose === purpose && c.granted);
  };

  async function handleToggleConsent(purpose: string, granted: boolean) {
    try {
      setPrivacyLoading(true);
      if (!granted) {
        await withdrawConsent(purpose);
      } else {
        await updateConsents([{ purpose, granted: true }]);
      }
      const updated = await fetchConsents();
      setConsents(updated.consents || []);
      setPrivacyMessage(`Consent for ${purpose} updated successfully.`);
      setTimeout(() => setPrivacyMessage(null), 3000);
      loadDashboardData();
    } catch (err: any) {
      setPrivacyMessage(`Error updating consent: ${err.message}`);
    } finally {
      setPrivacyLoading(false);
    }
  }

  async function handleResumeUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!resumeFile) return;

    if (!isConsentGranted("resume_processing")) {
      alert("Please grant 'Resume Processing' consent in the DPDP Privacy tab first.");
      setActiveTab("privacy");
      return;
    }

    try {
      setUploadingResume(true);
      setProfileMessage(null);
      await uploadResumeFile(resumeFile);
      setProfileMessage("Resume parsed successfully! Please review and confirm your extracted skills below.");
      // Reload profile
      const prof = await fetchStudentProfile();
      setProfile(prof);
      if (prof.merged?.skills) {
        setEditableSkills(prof.merged.skills);
      }
    } catch (err: any) {
      setProfileMessage(`Upload failed: ${err.message}`);
    } finally {
      setUploadingResume(false);
    }
  }

  function handleAddSkill() {
    if (!newSkillName.trim()) return;
    setEditableSkills([...editableSkills, { name: newSkillName.trim(), category: newSkillCategory }]);
    setNewSkillName("");
  }

  function handleRemoveSkill(index: number) {
    setEditableSkills(editableSkills.filter((_, i) => i !== index));
  }

  async function handleSaveAndConfirmProfile() {
    try {
      setProfileLoading(true);
      setProfileMessage(null);
      // Save updated skills
      await updateStudentProfile({
        skills: editableSkills,
      });
      // Explicit student confirmation
      const confirmed = await confirmStudentProfile();
      setProfile(confirmed);
      setProfileMessage("Profile successfully confirmed! Matching embeddings have been regenerated.");
      loadDashboardData();
    } catch (err: any) {
      setProfileMessage(`Error confirming profile: ${err.message}`);
    } finally {
      setProfileLoading(false);
    }
  }

  async function handleGitHubProofSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!githubUrl.trim()) return;
    try {
      setGithubLoading(true);
      setGithubError(null);
      const proof = await submitGitHubProof(githubUrl);
      setGithubProof(proof);
      loadDashboardData();
    } catch (err: any) {
      setGithubError(err.message || "Failed to link GitHub repository");
    } finally {
      setGithubLoading(false);
    }
  }

  async function handleExportData() {
    try {
      const data = await exportUserData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `warmpath-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    }
  }

  async function handleDeleteAccount() {
    try {
      await deleteUserAccount();
      clearSession();
      alert("Your account and all associated profile, resume, and embedding data have been permanently deleted.");
      router.push("/login");
    } catch (err: any) {
      alert(`Account deletion failed: ${err.message}`);
    }
  }

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
            {githubProof && (
              <span className="text-[10px] bg-slate-900 text-amber-300 font-semibold px-2 py-0.5 rounded border border-slate-700">
                ⭐ Proof of work ({githubProof.username})
              </span>
            )}
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

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-200 space-x-8 text-sm font-semibold">
        <button
          onClick={() => setActiveTab("mentors")}
          className={`pb-3 transition-colors ${
            activeTab === "mentors"
              ? "text-teal-600 border-b-2 border-teal-600"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          Mentors & Opportunities
        </button>
        <button
          onClick={() => setActiveTab("profile")}
          className={`pb-3 transition-colors flex items-center space-x-2 ${
            activeTab === "profile"
              ? "text-teal-600 border-b-2 border-teal-600"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          <span>Resume & Skills (F4)</span>
          {profile?.is_confirmed ? (
            <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded font-normal">Confirmed</span>
          ) : (
            <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded font-normal">Pending Review</span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("proof")}
          className={`pb-3 transition-colors flex items-center space-x-2 ${
            activeTab === "proof"
              ? "text-teal-600 border-b-2 border-teal-600"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          <span>Proof of Work (F5)</span>
          {githubProof && (
            <span className="text-[10px] bg-teal-100 text-teal-800 px-1.5 py-0.2 rounded font-normal">Active</span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("privacy")}
          className={`pb-3 transition-colors ${
            activeTab === "privacy"
              ? "text-teal-600 border-b-2 border-teal-600"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          DPDP Privacy & Consents (F33)
        </button>
      </div>

      {/* TAB 1: MENTORS & OPPORTUNITIES (F6, F7, F8, F9, F10) */}
      {activeTab === "mentors" && (
        <div className="space-y-6">
          {/* F6 & F7: Intent Screen: "What do you want next?" */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                    F6 & F7 Intent Core
                  </span>
                  <h2 className="text-base font-bold text-slate-900">What do you want next?</h2>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Turn vague goals into high-signal asks. Our matching engine structures your intent and queries verified mentors.
                </p>
              </div>

              {intentSavedSuccess && (
                <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-xl font-medium animate-fade-in">
                  ✓ Intent structured & matches re-ranked!
                </span>
              )}
            </div>

            {/* Quick Example Asks */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-[11px] font-semibold text-slate-400">Quick Examples:</span>
              <button
                type="button"
                onClick={() => {
                  const t = "Mock interview for backend Go and Kubernetes distributed systems roles.";
                  setIntentText(t);
                  handleCheckQuality(t);
                }}
                className="text-[11px] bg-slate-50 hover:bg-teal-50 hover:text-teal-700 text-slate-600 px-2.5 py-1 rounded-lg border border-slate-200 transition"
              >
                💡 Mock Interview (Go & K8s)
              </button>
              <button
                type="button"
                onClick={() => {
                  const t = "Resume review for Python and Machine Learning data science roles.";
                  setIntentText(t);
                  handleCheckQuality(t);
                }}
                className="text-[11px] bg-slate-50 hover:bg-teal-50 hover:text-teal-700 text-slate-600 px-2.5 py-1 rounded-lg border border-slate-200 transition"
              >
                💡 Resume Review (Python & ML)
              </button>
              <button
                type="button"
                onClick={() => {
                  const t = "Referral and portfolio feedback for senior Frontend Engineer positions.";
                  setIntentText(t);
                  handleCheckQuality(t);
                }}
                className="text-[11px] bg-slate-50 hover:bg-teal-50 hover:text-teal-700 text-slate-600 px-2.5 py-1 rounded-lg border border-slate-200 transition"
              >
                💡 Referral & Portfolio (Frontend)
              </button>
              <button
                type="button"
                onClick={() => {
                  const t = "need help pls";
                  setIntentText(t);
                  handleCheckQuality(t);
                }}
                className="text-[11px] bg-amber-50 hover:bg-amber-100 text-amber-800 px-2 py-1 rounded-lg border border-amber-200 transition"
                title="Test vague request quality step"
              >
                ⚠️ Test Vague Ask (&quot;need help pls&quot;)
              </button>
            </div>

            {/* Input Box */}
            <div className="space-y-3">
              <textarea
                rows={3}
                value={intentText}
                onChange={(e) => {
                  setIntentText(e.target.value);
                  if (intentQuality) setIntentQuality(null);
                }}
                placeholder="Describe your goal: e.g. I need a 45-minute mock system design interview targeting backend roles in Go and Kubernetes..."
                className="w-full text-xs text-slate-800 p-3 border border-slate-300 rounded-xl focus:outline-teal-500 focus:ring-1 focus:ring-teal-500"
              />

              {/* F7: Request Quality Pre-flight Feedback Card */}
              {intentQuality?.is_blocked && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-rose-900 flex items-center gap-1.5">
                      🚫 Prohibited Request Blocked (Quality Score: 0.0)
                    </span>
                    <span className="text-[10px] bg-rose-200 text-rose-900 font-bold px-1.5 py-0.5 rounded">
                      Hard Block
                    </span>
                  </div>
                  <p className="text-[11px]">
                    <strong>Reason:</strong> {intentQuality.block_reason || "Contains off-platform contact details, phone numbers, or prohibited spam keywords."}
                  </p>
                </div>
              )}

              {intentQuality && !intentQuality.is_blocked && intentQuality.quality_score < 0.7 && (
                <div className="p-4 bg-amber-50/80 border border-amber-200 text-amber-900 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-950 flex items-center gap-1.5">
                      ⚠️ Request Quality Step (F7): Vague Ask Detected
                    </span>
                    <span className="text-[11px] bg-amber-200 text-amber-900 font-bold px-2 py-0.5 rounded">
                      Quality Score: {Math.round(intentQuality.quality_score * 100)}%
                    </span>
                  </div>

                  {intentQuality.feedback && intentQuality.feedback.length > 0 && (
                    <ul className="list-disc list-inside text-[11px] text-amber-800 space-y-0.5">
                      {intentQuality.feedback.map((f: string, idx: number) => (
                        <li key={idx}>{f}</li>
                      ))}
                    </ul>
                  )}

                  {intentQuality.suggested_refinement && (
                    <div className="bg-white p-3 rounded-lg border border-amber-200 space-y-2 mt-2">
                      <p className="text-[11px] text-slate-500 font-semibold uppercase tracking-wider">
                        Suggested Refined Ask:
                      </p>
                      <p className="text-xs font-medium text-slate-800 italic">
                        &quot;{intentQuality.suggested_refinement}&quot;
                      </p>
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        <button
                          type="button"
                          onClick={() => handleAcceptRefinement(intentQuality.suggested_refinement)}
                          className="px-3 py-1.5 text-xs font-bold bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition"
                        >
                          ✓ Accept Suggestion & Save
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setIntentText(intentQuality.suggested_refinement);
                            setIntentQuality(null);
                          }}
                          className="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition"
                        >
                          ✏️ Edit Suggestion
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveIntent(intentText)}
                          className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700 underline"
                        >
                          Keep Mine Anyway
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons Row */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={checkingQuality || !intentText.trim()}
                    onClick={() => handleCheckQuality(intentText)}
                    className="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition disabled:opacity-50"
                  >
                    {checkingQuality ? "Analyzing Ask Quality..." : "🔍 Check Request Quality (F7)"}
                  </button>

                  <button
                    type="button"
                    disabled={isSavingIntent || intentQuality?.is_blocked || !intentText.trim()}
                    onClick={() => handleSaveIntent(intentText)}
                    className="px-4 py-1.5 text-xs font-bold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-2xs transition disabled:opacity-50"
                  >
                    {isSavingIntent ? "Structuring & Matching..." : "🚀 Save Intent & Re-Rank Mentors"}
                  </button>
                </div>

                {structuredIntent && (
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="bg-teal-50 text-teal-800 border border-teal-200 px-2 py-0.5 rounded font-medium">
                      🎯 Goal: {structuredIntent.goal_type}
                    </span>
                    <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">
                      💼 Role: {structuredIntent.target_role || "Backend"}
                    </span>
                    {structuredIntent.required_skills && structuredIntent.required_skills.length > 0 && (
                      <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">
                        ⚡ Skills: {structuredIntent.required_skills.slice(0, 3).join(", ")}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Main Grid: Mentors on Left (2 cols), Active Requests & Matched Jobs on Right (1 col) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column: Recommended Givers with "Why this match" & Factor Scores */}
            <div className="lg:col-span-2 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-bold text-slate-900">Recommended Mentors & Givers (F8)</h2>
                  <p className="text-xs text-slate-500">
                    Transparent ranking: pgvector embeddings, taxonomy, batch affinity, ratings & response speed.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {/* Scope Selector */}
                  <div className="flex bg-slate-100 p-0.5 rounded-xl text-xs font-semibold">
                    <button
                      type="button"
                      onClick={() => handleScopeChange("own_college")}
                      className={`px-3 py-1 rounded-lg transition ${
                        selectedScope === "own_college"
                          ? "bg-white text-teal-700 shadow-2xs"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      🏛️ IIIT Delhi (Free)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleScopeChange("cross_college")}
                      className={`px-3 py-1 rounded-lg transition ${
                        selectedScope === "cross_college"
                          ? "bg-white text-teal-700 shadow-2xs"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      🌐 Cross-College (1 Credit)
                    </button>
                  </div>

                  {/* Jury Explain Ranking Button */}
                  <button
                    type="button"
                    onClick={handleOpenExplainRanking}
                    className="px-3 py-1.5 text-xs font-bold bg-slate-900 hover:bg-slate-800 text-amber-300 rounded-xl shadow-2xs transition flex items-center gap-1.5"
                    title="Inspect ranking weights and factors for jury review"
                  >
                    <span>🔬 Explain Ranking</span>
                  </button>
                </div>
              </div>

              {/* F10: Hard Gates Active Summary Banner */}
              {excludedSummary && (
                <div className="p-3 bg-slate-50 border border-slate-200/90 rounded-xl flex items-center justify-between text-xs text-slate-600">
                  <div className="flex items-center space-x-2">
                    <span className="text-emerald-600 font-bold">🛡️ Hard Gates Active:</span>
                    <span>
                      {excludedSummary.total_excluded ?? 0} givers hard-excluded (
                      {excludedSummary.reasons?.unverified ?? 0} unverified,{" "}
                      {excludedSummary.reasons?.suspended ?? 0} suspended,{" "}
                      {excludedSummary.reasons?.inactive_too_long ?? 0} inactive &gt;14d,{" "}
                      {excludedSummary.reasons?.over_capacity ?? 0} over capacity)
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 italic">Zero unverified or full-capacity mentors shown</span>
                </div>
              )}

              {/* Giver Recommendation Cards */}
              <div className="space-y-4">
                {recsLoading ? (
                  <div className="p-12 text-center bg-white border border-slate-200 rounded-xl text-slate-500">
                    <div className="inline-block w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                    <p className="text-xs">Re-calculating semantic vector scores and ranking givers...</p>
                  </div>
                ) : recommendations.length > 0 ? (
                  recommendations.map((item: any) => {
                    const giver = item.giver;
                    const scores = item.score_components;
                    const isExpanded = expandedScoreGiverId === String(giver.id);
                    const giverType = giver.giver_type || "alumni";
                    const giverBadgeColor =
                      giverType === "faculty"
                        ? "bg-purple-50 text-purple-700 border-purple-200"
                        : giverType === "recruiter"
                        ? "bg-blue-50 text-blue-700 border-blue-200"
                        : giverType === "founder"
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-teal-50 text-teal-700 border-teal-200";

                    return (
                      <div
                        key={giver.id}
                        className="bg-white border border-slate-200 rounded-xl p-5 hover:border-teal-500/50 hover:shadow-sm transition-all space-y-3"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="font-bold text-sm text-slate-900">{giver.full_name}</h3>
                              {/* Giver Role Type Label */}
                              <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold ${giverBadgeColor}`}>
                                {giver.giver_type_label || "Alumnus Mentor"}
                              </span>
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                                {giver.band || giver.giver_band || "Top Rated"}
                              </span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                                ★ {giver.rating_summary?.smoothed_avg ? giver.rating_summary.smoothed_avg.toFixed(1) : (giver.rating_avg ? giver.rating_avg.toFixed(1) : "4.9")} ({giver.rating_summary?.total_sessions || giver.total_sessions || 12} sessions)
                              </span>
                            </div>
                            <p className="text-xs text-slate-600 mt-1 font-medium">
                              {giver.role_title || giver.designation || "Senior Software Engineer"} @ <span className="text-slate-900 font-semibold">{giver.company || "Google"}</span>
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            {/* Match Score Badge */}
                            {scores && (
                              <div className="text-right">
                                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Match Score</span>
                                <span className="text-xs font-extrabold text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-md">
                                  {Math.round((scores.total_score || 0.85) * 100)}%
                                </span>
                              </div>
                            )}

                            <button className="px-3 py-1.5 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-2xs transition-colors">
                              Request Session
                            </button>
                          </div>
                        </div>

                        {/* F9: Real Overlap "Why this match" explanation */}
                        <div className="bg-teal-50/60 border border-teal-100 rounded-lg p-2.5 flex items-start space-x-2">
                          <svg className="w-4 h-4 text-teal-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <div className="text-[11px] text-teal-950 leading-relaxed">
                            <strong className="font-semibold text-teal-900">Why this match: </strong>
                            {item.why_lines && item.why_lines.length > 0 ? (
                              <span>{item.why_lines.join("; ")}.</span>
                            ) : (
                              <span>{giver.why_match || "Same college alumnus; shares confirmed skills; strong reply rate."}</span>
                            )}
                          </div>
                        </div>

                        {/* Skills and Availability Row */}
                        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                          <div className="flex flex-wrap gap-1.5">
                            {(giver.skills || ["Distributed Systems", "FastAPI", "Kubernetes"]).map((s: any, idx: number) => {
                              const skillName = typeof s === "string" ? s : s.name;
                              return (
                                <span key={idx} className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                                  {skillName}
                                </span>
                              );
                            })}
                          </div>

                          <div className="flex items-center gap-3 text-[10px] text-slate-500">
                            <span className="flex items-center gap-1">
                              <span className={`w-2 h-2 rounded-full ${giver.availability_summary?.online ? "bg-emerald-500" : "bg-amber-400"}`}></span>
                              <span>{giver.availability_summary?.status === "active_now" ? "Active Now" : "Available Today"}</span>
                            </span>
                            <span>⚡ Replies in ~{giver.availability_summary?.avg_reply_minutes || 30}m</span>

                            {/* Factor Breakdown Expander */}
                            {scores && (
                              <button
                                type="button"
                                onClick={() => setExpandedScoreGiverId(isExpanded ? null : String(giver.id))}
                                className="text-teal-700 hover:text-teal-900 font-semibold underline ml-1"
                              >
                                {isExpanded ? "Hide Breakdown ▲" : "Score Breakdown ▼"}
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Expandable Factor Breakdown Table (Requirement 3 & 7) */}
                        {isExpanded && scores && (
                          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl mt-2 text-xs space-y-2">
                            <div className="flex items-center justify-between border-b border-slate-200/60 pb-1.5">
                              <span className="font-bold text-slate-800 text-[11px] uppercase tracking-wider">
                                Ranking Factor Breakdown (config/matching.json)
                              </span>
                              <span className="text-[11px] font-bold text-teal-800">
                                Total: {Math.round(scores.total_score * 100)}%
                              </span>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
                              <div className="p-2 bg-white rounded border border-slate-100">
                                <span className="text-slate-400 block text-[10px]">Skill &amp; Intent (35%)</span>
                                <span className="font-bold text-slate-800">{Math.round(scores.skill_intent_similarity * 100)}%</span>
                              </div>
                              <div className="p-2 bg-white rounded border border-slate-100">
                                <span className="text-slate-400 block text-[10px]">Similar Journey (15%)</span>
                                <span className="font-bold text-slate-800">{Math.round(scores.similar_journey * 100)}%</span>
                              </div>
                              <div className="p-2 bg-white rounded border border-slate-100">
                                <span className="text-slate-400 block text-[10px]">Affinity (15%)</span>
                                <span className="font-bold text-slate-800">{Math.round(scores.affinity * 100)}%</span>
                              </div>
                              <div className="p-2 bg-white rounded border border-slate-100">
                                <span className="text-slate-400 block text-[10px]">Rating (15%)</span>
                                <span className="font-bold text-slate-800">{Math.round(scores.rating * 100)}%</span>
                              </div>
                              <div className="p-2 bg-white rounded border border-slate-100">
                                <span className="text-slate-400 block text-[10px]">Availability (12%)</span>
                                <span className="font-bold text-slate-800">{Math.round(scores.availability * 100)}%</span>
                              </div>
                              <div className="p-2 bg-white rounded border border-slate-100">
                                <span className="text-slate-400 block text-[10px]">Response Speed (8%)</span>
                                <span className="font-bold text-slate-800">{Math.round(scores.response_speed * 100)}%</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="p-8 text-center bg-white border border-slate-200 rounded-xl text-slate-400 text-xs">
                    No givers matched yet. Upload or confirm your skill profile or save an intent ask above.
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

          {/* Jury / Dev Explain Ranking Modal */}
          {showExplainModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
              <div className="bg-white rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                  <div>
                    <span className="text-[10px] bg-amber-100 text-amber-900 font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                      Jury &amp; Dev Inspector
                    </span>
                    <h3 className="text-base font-bold text-slate-900 mt-1">
                      WarmPath Transparent Ranking Engine (config/matching.json)
                    </h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowExplainModal(false)}
                    className="text-slate-400 hover:text-slate-700 text-xl font-bold p-1"
                  >
                    &times;
                  </button>
                </div>

                {explainLoading ? (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    <div className="inline-block w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                    <p>Loading transparent weights and factor matrix...</p>
                  </div>
                ) : explainData ? (
                  <div className="space-y-5 text-xs">
                    {/* Weights Cards */}
                    <div>
                      <h4 className="font-bold text-slate-800 mb-2">1. Configurable Matching Weights</h4>
                      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                        {Object.entries(explainData.weights || {}).map(([key, val]: [string, any]) => (
                          <div key={key} className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-center">
                            <span className="text-[10px] text-slate-400 uppercase tracking-wider block truncate">
                              {key.replace(/_/g, " ")}
                            </span>
                            <span className="text-sm font-extrabold text-teal-700">
                              {Math.round(val * 100)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Hard Gates Summary */}
                    <div>
                      <h4 className="font-bold text-slate-800 mb-2">2. Hard Gates Pre-Filter (No names revealed)</h4>
                      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-emerald-950">
                            Excluded: {explainData.hard_gates_applied?.total_excluded ?? 0} givers
                          </p>
                          <p className="text-[11px] text-emerald-800 mt-0.5">
                            Unverified: {explainData.hard_gates_applied?.reasons?.unverified ?? 0} &bull;
                            Suspended: {explainData.hard_gates_applied?.reasons?.suspended ?? 0} &bull;
                            Inactive &gt;14d: {explainData.hard_gates_applied?.reasons?.inactive_too_long ?? 0} &bull;
                            Over Capacity: {explainData.hard_gates_applied?.reasons?.over_capacity ?? 0}
                          </p>
                        </div>
                        <span className="text-[10px] bg-emerald-100 text-emerald-900 font-bold px-2 py-1 rounded">
                          Pass-Through Rate: High
                        </span>
                      </div>
                    </div>

                    {/* Candidate Breakdown Matrix */}
                    <div>
                      <h4 className="font-bold text-slate-800 mb-2">3. Top Ranked Candidates Factor Breakdown</h4>
                      <div className="border border-slate-200 rounded-xl overflow-hidden">
                        <table className="min-w-full divide-y divide-slate-200 text-[11px]">
                          <thead className="bg-slate-50 text-slate-600 font-bold uppercase">
                            <tr>
                              <th className="px-3 py-2 text-left">Giver</th>
                              <th className="px-2 py-2 text-left">Role</th>
                              <th className="px-2 py-2 text-center">Skill/Intent (35%)</th>
                              <th className="px-2 py-2 text-center">Journey (15%)</th>
                              <th className="px-2 py-2 text-center">Affinity (15%)</th>
                              <th className="px-2 py-2 text-center">Rating (15%)</th>
                              <th className="px-2 py-2 text-center">Avail (12%)</th>
                              <th className="px-2 py-2 text-center">Speed (8%)</th>
                              <th className="px-3 py-2 text-right">Score</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            {(explainData.top_candidates || []).map((c: any, idx: number) => (
                              <tr key={idx} className="hover:bg-slate-50/70">
                                <td className="px-3 py-2 font-semibold text-slate-900">{c.full_name}</td>
                                <td className="px-2 py-2 text-slate-500 capitalize">{c.giver_type}</td>
                                <td className="px-2 py-2 text-center text-slate-700">
                                  {Math.round((c.raw_factors?.skill_intent_similarity ?? 0) * 100)}%
                                </td>
                                <td className="px-2 py-2 text-center text-slate-700">
                                  {Math.round((c.raw_factors?.similar_journey ?? 0) * 100)}%
                                </td>
                                <td className="px-2 py-2 text-center text-slate-700">
                                  {Math.round((c.raw_factors?.affinity ?? 0) * 100)}%
                                </td>
                                <td className="px-2 py-2 text-center text-slate-700">
                                  {Math.round((c.raw_factors?.rating ?? 0) * 100)}%
                                </td>
                                <td className="px-2 py-2 text-center text-slate-700">
                                  {Math.round((c.raw_factors?.availability ?? 0) * 100)}%
                                </td>
                                <td className="px-2 py-2 text-center text-slate-700">
                                  {Math.round((c.raw_factors?.response_speed ?? 0) * 100)}%
                                </td>
                                <td className="px-3 py-2 text-right font-extrabold text-teal-700">
                                  {Math.round(c.total_score * 100)}%
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No explanation data returned.</p>
                )}

                <div className="flex justify-end pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowExplainModal(false)}
                    className="px-4 py-2 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition"
                  >
                    Close Inspector
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: RESUME & SKILLS PROFILE (F4) */}
      {activeTab === "profile" && (
        <div className="space-y-6">
          {profileMessage && (
            <div className="p-4 bg-teal-50 border border-teal-200 text-teal-900 rounded-xl text-xs font-medium">
              {profileMessage}
            </div>
          )}

          {/* Upload Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">PDF Resume Upload (AI Extraction)</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Upload your CV to automatically extract education, skills, and projects. You retain full editorial control.
                </p>
              </div>
              <span className="text-[11px] bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-1 rounded font-semibold">
                Strict: extracted skills, student-confirmed
              </span>
            </div>

            <form onSubmit={handleResumeUpload} className="flex flex-col sm:flex-row items-center gap-4 pt-2">
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                className="text-xs text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-teal-700 hover:file:bg-teal-100"
              />
              <button
                type="submit"
                disabled={!resumeFile || uploadingResume}
                className="w-full sm:w-auto px-5 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-2xs transition disabled:opacity-50"
              >
                {uploadingResume ? "Parsing with LLM Adapter..." : "Upload & Parse Resume"}
              </button>
            </form>
          </div>

          {/* Editable Skills & Profile Form */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-6 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Student Confirmed Skills</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Label: <strong className="text-teal-700 font-semibold">{profile?.skills_label || "extracted skills, student-confirmed"}</strong>. Never labeled &quot;verified&quot;.
                </p>
              </div>
              <button
                onClick={handleSaveAndConfirmProfile}
                disabled={profileLoading}
                className="px-4 py-2 text-xs font-bold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-2xs transition disabled:opacity-50"
              >
                {profile?.is_confirmed ? "Save & Re-confirm Profile" : "Explicitly Confirm Profile"}
              </button>
            </div>

            {/* Current Skills List */}
            <div className="space-y-3">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Skills ({editableSkills.length})</label>
              <div className="flex flex-wrap gap-2">
                {editableSkills.map((skill, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 bg-slate-100 border border-slate-200 text-slate-800 text-xs px-3 py-1.5 rounded-lg"
                  >
                    <span>{skill.name}</span>
                    {skill.category && <span className="text-[10px] text-slate-400">({skill.category})</span>}
                    <button
                      type="button"
                      onClick={() => handleRemoveSkill(idx)}
                      className="text-slate-400 hover:text-rose-600 font-bold ml-1"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
            </div>

            {/* Add Skill Bar */}
            <div className="flex items-center gap-3 pt-2">
              <input
                type="text"
                placeholder="Add skill (e.g., PyTorch, Rust, Kubernetes)"
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                className="text-xs border border-slate-300 rounded-xl px-3 py-2 w-64 focus:outline-teal-500"
              />
              <select
                value={newSkillCategory}
                onChange={(e) => setNewSkillCategory(e.target.value)}
                className="text-xs border border-slate-300 rounded-xl px-3 py-2 focus:outline-teal-500"
              >
                <option value="Programming Languages">Programming Languages</option>
                <option value="Backend / Systems">Backend / Systems</option>
                <option value="AI / ML">AI / ML</option>
                <option value="Frontend">Frontend</option>
                <option value="DevOps / Cloud">DevOps / Cloud</option>
                <option value="Core CS">Core CS</option>
              </select>
              <button
                type="button"
                onClick={handleAddSkill}
                className="px-3 py-2 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition"
              >
                + Add Skill
              </button>
            </div>

            {/* Extracted Education & Projects Display */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-100">
              <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-xl space-y-2">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Extracted Education</h4>
                {profile?.merged?.education && profile.merged.education.length > 0 ? (
                  profile.merged.education.map((edu: any, i: number) => (
                    <div key={i} className="text-xs text-slate-700">
                      <strong>{edu.degree || "Degree"}</strong> - {edu.institution || "Institution"} ({edu.year || "Year"})
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">No education parsed yet. Upload resume above.</p>
                )}
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-xl space-y-2">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Extracted Projects</h4>
                {profile?.merged?.projects && profile.merged.projects.length > 0 ? (
                  profile.merged.projects.map((proj: any, i: number) => (
                    <div key={i} className="text-xs text-slate-700">
                      <strong>{proj.title || "Project"}</strong>: {proj.description || "N/A"}
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">No projects parsed yet. Upload resume above.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: PROOF OF WORK (F5) */}
      {activeTab === "proof" && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-6 shadow-xs">
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">GitHub Proof of Work</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Link your GitHub profile or repository as authentic proof of work. In demo mode, live metrics and languages are fetched deterministically.
              </p>
            </div>

            <form onSubmit={handleGitHubProofSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">GitHub Profile / Repo URL</label>
                <div className="flex gap-3">
                  <input
                    type="url"
                    placeholder="https://github.com/your-username"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    className="flex-1 text-xs border border-slate-300 rounded-xl px-3 py-2.5 focus:outline-teal-500"
                    required
                  />
                  <button
                    type="submit"
                    disabled={githubLoading}
                    className="px-5 py-2.5 text-xs font-bold bg-teal-600 hover:bg-teal-700 text-white rounded-xl shadow-2xs transition disabled:opacity-50"
                  >
                    {githubLoading ? "Verifying..." : "Verify & Link Proof"}
                  </button>
                </div>
              </div>
              {githubError && <p className="text-xs text-rose-600">{githubError}</p>}
            </form>

            {githubProof && (
              <div className="p-5 bg-slate-900 text-white rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-full bg-teal-500/20 border border-teal-400/40 flex items-center justify-center font-bold text-teal-300 text-sm">
                      {githubProof.username?.slice(0, 2).toUpperCase() || "GH"}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        {githubProof.username}
                        <span className="text-[10px] bg-amber-400/20 text-amber-300 border border-amber-400/30 px-2 py-0.5 rounded-full font-medium">
                          {githubProof.badge || "Proof of work"}
                        </span>
                      </h4>
                      <p className="text-[11px] text-slate-400">{githubProof.repo_url}</p>
                    </div>
                  </div>
                  <span className="text-xs text-emerald-400 font-semibold bg-emerald-950/60 border border-emerald-800 px-2.5 py-1 rounded">
                    Verified Signal in Matching Engine
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-4 pt-2 border-t border-slate-800 text-center">
                  <div className="p-2.5 bg-slate-800/50 rounded-lg">
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider">Public Repos</p>
                    <p className="text-base font-bold text-white">{githubProof.repo_count ?? 5}</p>
                  </div>
                  <div className="p-2.5 bg-slate-800/50 rounded-lg">
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider">Top Languages</p>
                    <p className="text-xs font-semibold text-teal-300 truncate">
                      {githubProof.top_languages?.join(", ") || "Python, TypeScript"}
                    </p>
                  </div>
                  <div className="p-2.5 bg-slate-800/50 rounded-lg">
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider">Total Commits</p>
                    <p className="text-base font-bold text-white">{githubProof.total_commits ?? 124}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: DPDP PRIVACY & CONSENT MANAGEMENT (F33) */}
      {activeTab === "privacy" && (
        <div className="space-y-6">
          {privacyMessage && (
            <div className="p-4 bg-teal-50 border border-teal-200 text-teal-900 rounded-xl text-xs font-medium">
              {privacyMessage}
            </div>
          )}

          {/* Explicit Consent Controls */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-6 shadow-xs">
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">DPDP Act (Privacy by Design) Consents</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Under the Digital Personal Data Protection Act, you have granular control over what data WarmPath processes.
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <div>
                  <h4 className="text-xs font-bold text-slate-900">Resume Processing & Skill Extraction</h4>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Allows Gemini LLM to parse your uploaded resume and recommend relevant mentors.
                  </p>
                </div>
                <button
                  type="button"
                  disabled={privacyLoading}
                  onClick={() => handleToggleConsent("resume_processing", !isConsentGranted("resume_processing"))}
                  className={`px-4 py-1.5 text-xs font-bold rounded-lg transition ${
                    isConsentGranted("resume_processing")
                      ? "bg-emerald-600 text-white hover:bg-emerald-700"
                      : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                  }`}
                >
                  {isConsentGranted("resume_processing") ? "Granted (Active)" : "Withdraw / Denied"}
                </button>
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <div>
                  <h4 className="text-xs font-bold text-slate-900">Profile Matching & Recommendations</h4>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Permits indexing your confirmed skills in pgvector to receive alumni mentor matches.
                  </p>
                </div>
                <button
                  type="button"
                  disabled={privacyLoading}
                  onClick={() => handleToggleConsent("profile_matching", !isConsentGranted("profile_matching"))}
                  className={`px-4 py-1.5 text-xs font-bold rounded-lg transition ${
                    isConsentGranted("profile_matching")
                      ? "bg-emerald-600 text-white hover:bg-emerald-700"
                      : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                  }`}
                >
                  {isConsentGranted("profile_matching") ? "Granted (Active)" : "Withdraw / Denied"}
                </button>
              </div>
            </div>
          </div>

          {/* 1-Click Data Export */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 shadow-xs">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">1-Click Personal Data Export</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Download a machine-readable JSON archive of your account, consents, resume extractions, and proofs.
                </p>
              </div>
              <button
                type="button"
                onClick={handleExportData}
                className="px-4 py-2 text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl border border-slate-200 transition"
              >
                Download JSON Archive &darr;
              </button>
            </div>
          </div>

          {/* Right to be Forgotten (Account Deletion) */}
          <div className="bg-rose-50/50 border border-rose-200 rounded-2xl p-6 space-y-4">
            <div>
              <h3 className="text-base font-bold text-rose-900">Right to be Forgotten (Permanent Deletion)</h3>
              <p className="text-xs text-rose-700 mt-0.5">
                Permanently purge your account, resume files, parsed schemas, pgvector embeddings, and proofs from the system.
              </p>
            </div>

            {!confirmDelete ? (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="px-4 py-2 text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-xl transition"
              >
                Delete My Account & All Data
              </button>
            ) : (
              <div className="p-4 bg-white border border-rose-300 rounded-xl space-y-3">
                <p className="text-xs font-bold text-rose-900">
                  Are you absolutely certain? This operation cannot be undone.
                </p>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={handleDeleteAccount}
                    className="px-4 py-2 text-xs font-bold bg-rose-700 hover:bg-rose-800 text-white rounded-xl transition"
                  >
                    Confirm Permanent Deletion
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDelete(false)}
                    className="px-4 py-2 text-xs font-semibold bg-slate-100 text-slate-700 rounded-xl hover:bg-slate-200 transition"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
