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

  useEffect(() => {
    setUser(getStoredUser());
    loadDashboardData();
    loadProfileAndProof();
  }, []);

  async function loadDashboardData() {
    try {
      setLoading(true);
      const res = await fetchDashboard("student");
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load student dashboard");
    } finally {
      setLoading(false);
    }
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

      {/* TAB 1: MENTORS & OPPORTUNITIES */}
      {activeTab === "mentors" && (
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
                  No givers matched yet. Upload or confirm your skill profile to enable recommendations.
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
