/**
 * frontend/src/lib/api.ts - WarmPath API Client & Local Auth Store
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UserSession {
  id: string;
  email: string;
  full_name: string;
  role: string;
  roles: string[];
  institution_id?: number;
  verification_level: string;
  trust_score: number;
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("warmpath_token");
}

export function getStoredUser(): UserSession | null {
  if (typeof window === "undefined") return null;
  const userStr = localStorage.getItem("warmpath_user");
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

export function setSession(token: string, user: UserSession): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("warmpath_token", token);
  localStorage.setItem("warmpath_user", JSON.stringify(user));
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("warmpath_token");
  localStorage.removeItem("warmpath_user");
}

export async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = "API request failed";
    try {
      const data = await res.json();
      errorDetail = data.detail || data.message || JSON.stringify(data);
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return res.json();
}

// Auth API
export async function login(email: string, password: string) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setSession(data.access_token, data.user);
  return data;
}

export async function loginAsRole(role: string) {
  const data = await apiFetch("/api/v1/demo/login-as", {
    method: "POST",
    body: JSON.stringify({ role }),
  });
  setSession(data.access_token, data.user);
  return data;
}

export async function resetDatabase() {
  return apiFetch("/api/v1/demo/reset", {
    method: "POST",
  });
}

export async function fetchDashboard(role: string) {
  return apiFetch(`/api/v1/dashboard/${role}`);
}

export async function fetchNotifications() {
  return apiFetch("/api/v1/notifications");
}

export async function markNotificationRead(id: string) {
  return apiFetch(`/api/v1/notifications/${id}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead() {
  return apiFetch("/api/v1/notifications/mark-all-read", {
    method: "POST",
  });
}

// Verification APIs (F2 & F3)
export async function sendOtp(email: string, purpose: string = "alumni_registration") {
  return apiFetch("/api/v1/verification/send-otp", {
    method: "POST",
    body: JSON.stringify({ email, purpose }),
  });
}

export async function registerAlumni(payload: any) {
  const data = await apiFetch("/api/v1/verification/register-alumni", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (data.access_token && data.user) {
    setSession(data.access_token, data.user);
  }
  return data;
}

export async function registerEmployer(payload: any) {
  const data = await apiFetch("/api/v1/verification/register-employer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (data.access_token && data.user) {
    setSession(data.access_token, data.user);
  }
  return data;
}

export async function uploadDocument(document_ref: string, document_type: string = "degree_certificate", notes?: string) {
  return apiFetch("/api/v1/verification/upload-document", {
    method: "POST",
    body: JSON.stringify({ document_ref, document_type, notes }),
  });
}

export async function requestPeerVouches(voucher_emails: string[], message?: string) {
  return apiFetch("/api/v1/verification/request-peer-vouches", {
    method: "POST",
    body: JSON.stringify({ voucher_emails, message }),
  });
}

export async function respondPeerVouch(vouch_id: string, action: "approve" | "reject", comment?: string) {
  return apiFetch("/api/v1/verification/respond-peer-vouch", {
    method: "POST",
    body: JSON.stringify({ vouch_id, action, comment }),
  });
}

export async function fetchVerificationStatus() {
  return apiFetch("/api/v1/verification/status");
}

export async function fetchVerificationQueue() {
  return apiFetch("/api/v1/admin/verification-queue");
}

export async function adminVerifyAction(request_id: string, action: "approve" | "reject", reason: string) {
  return apiFetch("/api/v1/admin/verify-action", {
    method: "POST",
    body: JSON.stringify({ request_id, action, reason }),
  });
}

export async function previewRosterCsv(csv_content: string) {
  return apiFetch("/api/v1/admin/roster/preview", {
    method: "POST",
    body: JSON.stringify({ csv_content }),
  });
}

export async function uploadRosterCsv(institution_id: number, csv_content: string, replace_existing: boolean = false) {
  return apiFetch("/api/v1/admin/roster/upload", {
    method: "POST",
    body: JSON.stringify({ institution_id, csv_content, replace_existing }),
  });
}

export async function createOpportunity(payload: any) {
  return apiFetch("/api/v1/opportunities", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

