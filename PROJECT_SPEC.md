# WarmPath — Project Specification

> **Tagline**: *"Trust first, networking second."*  
> **Hackathon Theme**: Alumni Network and Professional Connections — *"Building a Network, Not a Directory"*.  
> **Core Principle**: A directory merely lists people; WarmPath **recommends, connects, schedules, and measures**.

---

## 1. Executive Summary & Philosophy

Traditional alumni networks and professional directories suffer from low trust, cold outreach fatigue, spam, and unfulfilled connection requests. **WarmPath** re-engineers institutional networking into a closed, high-trust, verified ecosystem.

Connections are not transactional rolodex lookups. Instead:
- **Trust First**: Every participant is verified through college records, institutional emails, peer vouching, or corporate credentials before interaction can occur.
- **Affinity Layer**: Same-college connections are fundamentally and permanently free. Cross-college mentorship and recruitment operate on an escrow-backed credit economy.
- **Explainable Matching**: Transparent, configurable multi-factor matching (embeddings in pgvector + semantic keywords + rule-based hard gates) paired with clear *"Why this match"* reasoning.
- **Closed-Loop Measurement**: Outcomes are tracked from session completion and escrow release to interview progress, referral tracking, and institutional skill-gap analytics.

---

## 2. Technical Stack & Architecture

### 2.1 Core Stack
- **Frontend**: Next.js (App Router, React 19, TypeScript, Tailwind CSS, Lucide Icons, Shadcn UI patterns).
- **Backend**: FastAPI (Python 3.11+, Pydantic v2, SQLAlchemy 2.0 Async, Alembic migrations).
- **Database**: PostgreSQL 16 with `pgvector` extension for vector similarity search.
- **Cache & Message Broker**: Redis 7+ for session caching, rate limiting, and pub/sub.
- **Infrastructure**: `docker-compose.yml` for unified local execution (Postgres + pgvector, Redis, FastAPI, Next.js, and Mailpit).
- **Automation**: One-command seed script (`scripts/seed.py` or `scripts/seed.sh`) generating realistic dummy colleges, students, alumni, faculty, recruiters, and sessions.

### 2.2 Adapter Pattern & Demo Mode
To ensure the entire application runs 100% offline and reliably for jury evaluations without third-party API dependencies or costs, all external integrations implement a clean interface adapter pattern:

```
                      ┌────────────────────────┐
                      │    Service Adapter     │
                      │       Interface        │
                      └───────────┬────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
      ┌──────────────────────┐          ┌──────────────────────┐
      │  Live Production     │          │  Mock DEMO_MODE      │
      │  Implementation      │          │  Implementation      │
      ├──────────────────────┤          ├──────────────────────┤
      │ OpenAI / Gemini API  │          │ Deterministic Embeds │
      │ Mailgun / SendGrid   │          │ Mailpit / In-Memory  │
      │ Google Calendar API  │          │ Synthetic Meet Links │
      │ Razorpay / Stripe    │          │ Simulated Webhooks   │
      │ GitHub GraphQL API   │          │ Static Repo Analysis │
      └──────────────────────┘          └──────────────────────┘
```

1. **LLM / Embedding Adapter**:
   - Production: OpenAI `text-embedding-3-small` / Gemini API for embeddings and extraction.
   - Demo Mode: Deterministic 768-dim hash-based vector generator + local rules-based parser.
2. **Email OTP Adapter**:
   - Production: SMTP / SendGrid / AWS SES.
   - Demo Mode: Mailpit local SMTP catcher (`localhost:8025`) and pre-fixed test OTPs (`123456`).
3. **Calendar & Meeting Adapter**:
   - Production: Google Calendar API with Google Meet / Zoom links.
   - Demo Mode: Jitsi / static Meet link generator without OAuth requirements.
4. **Payment Adapter**:
   - Production: Razorpay / Stripe checkout with signed webhook verification.
   - Demo Mode: Simulated instant escrow funding and sandbox webhook trigger.
5. **GitHub Proof-of-Work Adapter**:
   - Production: GitHub REST/GraphQL API fetching repo stats, commit activity, and top languages.
   - Demo Mode: Seeded profile summaries with verified badge emulation.

---

## 3. User Roles & Access Matrix

WarmPath defines **6 distinct user roles** plus an **Institution Admin**:

| Role | Primary Purpose | Key Privileges | Economic Model |
| :--- | :--- | :--- | :--- |
| **Student** *(Seeker)* | Career navigation & mentorship | Uploads resume, states intent, receives explainable recommendations, books sessions | Free for same-college; pays platform credits for cross-college (or sponsored) |
| **Alumni** *(Giver)* | Guidance, portfolio & career prep | Sets weekly capacity, holds 1:1 sessions, vouches for high-performing seekers | Free same-college; earns 80% escrow credits on cross-college; reputation tiers |
| **Faculty** *(Giver)* | Domain & research mentorship | Verified expert badge, academic advising, research project collaboration | Compensated time via institutional or credit escrow; verified faculty badge |
| **Recruiter** *(Giver of Ops)*| Talent discovery & hiring | Posts verified job/internship referrals, conducts hiring chats with matched candidates | Consumes employer plan credits; requires verified company email & CIN/GST |
| **Founder** *(Giver of Ops)*  | Hiring & industry talks | Hosts office hours, fireside chats, posts startup referrals, meets pre-screened talent | Verified employer badge; peer-vouched startup credibility |
| **Institution Admin**        | Network stewardship & oversight| Validates alumni/faculty queues, reviews skill gaps, tracks fulfillment rates & health | Institutional seat; full audit and reporting dashboard |

---

## 4. Core System & Economic Rules

1. **Free Affinity Layer**:
   - Mentorship and requests between students and givers of the **same institution** are **ALWAYS 100% free**. No credits or payments may ever be demanded for intra-college connections.
2. **Cross-College Credit Economy & Escrow**:
   - Cross-college bookings require platform credits.
   - Credits are placed into an **Escrow Hold** upon request creation.
   - Credits are **released to the Giver (80%)** and **Platform fee (20%)** only after the session has been confirmed as completed AND rated by the student.
   - If a request is declined, cancelled before cutoff, or the giver is a no-show, **100% of the credits are refunded** to the seeker's wallet.
   - All pricing, escrow ratios, and fees reside in an externalized configuration file (`config/economy.json` or backend `config.py`), never hardcoded.
3. **Reputation-Driven Giver Bands**:
   - No demeaning tier labels are visible to seekers. Givers progress through reputation bands based on volume and verified ratings:
     - **Rising**: Less than 5 completed sessions (receives fair-start visibility boost in recommendations).
     - **Trusted**: 5 to 9 completed sessions with an average rating $\ge 4.2$.
     - **Top Rated**: 10+ completed sessions with an average rating $\ge 4.7$.
4. **Strict Verification Gate for External Actions**:
   - Unverified users **cannot** post jobs, referrals, or initiate unsolicited messages to students.
5. **Student Sovereignty over AI Extraction**:
   - Students can review, edit, override, or delete any data extracted from resumes by the AI parser before it is committed. Nothing is finalized without explicit student confirmation.
6. **Honest & Grounded Metrics**:
   - The platform strictly displays *"pilot target"* phrasing for estimates and system capacities. Zero-risk or absolute claims are prohibited across all UI copy.

---

## 5. The Seven Trust Layers

WarmPath visibly implements **7 interlocking trust layers** across the user journey:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      THE 7 WARM-PATH TRUST LAYERS                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. IDENTITY        │ College CSV match, institutional email OTP,        │
│                    │ peer vouching (2 batchmates), CIN/GST employer     │
├────────────────────┼────────────────────────────────────────────────────┤
│ 2. BADGES          │ Pending, Verified Alumnus, Verified Professional,  │
│                    │ Trusted, Verified Employer                         │
├────────────────────┼────────────────────────────────────────────────────┤
│ 3. LIMITS          │ Weekly capacity caps, graduated trust limits       │
│                    │ (preventing spam blasts by new students)           │
├────────────────────┼────────────────────────────────────────────────────┤
│ 4. IN-APP COMMS    │ Ephemeral chat concealing direct phone/email       │
│                    │ until trust established                            │
├────────────────────┼────────────────────────────────────────────────────┤
│ 5. SCAM DETECTION  │ Real-time scanning for off-platform contact leaks, │
│                    │ unapproved payment links, and coercion             │
├────────────────────┼────────────────────────────────────────────────────┤
│ 6. HUMAN REVIEW    │ 1-click report queue, triage dashboard,            │
│                    │ suspension, outlier rating moderation              │
├────────────────────┼────────────────────────────────────────────────────┤
│ 7. INCIDENT        │ Resolved moderation reports feed back to update    │
│    LEARNING        │ regex scam patterns and dynamic trust scores       │
└────────────────────┴────────────────────────────────────────────────────┘
```

---

## 6. Functional Architecture & Feature Mapping (F1 to F36)

### 6.1 Authentication & Trust Foundation
- **F1 Role-Based Auth and Role-Based Views**: JWT-based session auth with strictly segregated dashboards and navigational shells for Student, Alumni, Faculty, Recruiter, Founder, and Admin.
- **F2 Multi-Channel Registration & Verification**:
  - College CSV roster matching (Roll number / Enrollment ID).
  - Institutional domain `.edu` / `.ac.in` email OTP verification.
  - Document fallback (Degree certificate, student ID card upload).
  - Peer vouching: Verification unlocked when endorsed by two verified alumni from the same graduation batch.
  - Employer verification: Work email OTP + Company Registration (CIN / GST) lookup.
- **F3 Verification Levels & Badges**:
  - `Pending`: Registered but awaiting email/doc validation.
  - `Verified Alumnus`: Confirmed institutional graduate.
  - `Verified Professional`: Confirmed industry role via corporate domain.
  - `Trusted`: Sustained high rating ($\ge 4.5$), zero scam flags, verified ID.
  - `Verified Employer`: Recruiter/Founder with validated business credentials.

### 6.2 Seeker Onboarding & Needs Formulation
- **F4 Resume Upload & AI Parser**: PDF upload, extracted to structured JSON (Education, Skills, Experience, Projects). Candidate can inspect, edit, or reject any parsed field prior to saving.
- **F5 Proof-of-Work Links**: Optional GitHub, portfolio, or publication links with automated repo metadata extraction.
- **F6 Intent Structuring ("What do you want next?")**: Guided questionnaire transforming vague ambitions (*"I want a tech job"*) into structured targets (*Role: Backend Engineer, Domain: Fintech, Ask: Mock Technical Interview & Resume Critique*).
- **F7 Request Quality Step**: Pre-flight linting of connection requests before dispatch to givers, checking for clarity, context, and absence of generic copy-paste text.

### 6.3 Recommendation & Matching Engine
- **F8 Multi-Factor Hybrid Matching Engine**:
  - Semantic vector similarity via `pgvector` HNSW indexes over student intent embeddings and giver profile embeddings.
  - Keyword & taxonomy overlap (skills, industry, domain, programming languages).
  - Configurable weights in `matching_config.json`:
    $$\text{Score} = w_v \cdot S_{\text{vector}} + w_k \cdot S_{\text{keyword}} + w_a \cdot S_{\text{affinity}} + w_r \cdot S_{\text{rating}}$$
- **F9 Explainable Matches ("Why this match")**: Transparent 2-3 sentence explanation generated alongside every match card (e.g., *"Graduated from your college in 2021; works in Cloud Infra at target employer; highly rated for mock system design interviews"*).
- **F10 Safety & Capacity Gates**: Automated hard exclusions in SQL/vector queries: unverified givers, givers exceeding weekly session quotas, and givers with active reports are excluded from candidate pools.

### 6.4 Availability, Scheduling & Connection Lifecycle
- **F11 Giver Availability States**: Real-time status toggle: `Active now`, `Available today` (with specific time slots), or `Inactive`. Givers are automatically transitioned to `Inactive` after 14 days of no reply. Public profile displays response rate (%) and average reply time (hours).
- **F12 Capacity Caps**: Giver-configured weekly capacity (e.g., max 2 sessions/week) and monthly free-session quotas to prevent alumni burnout.
- **F13 Graduated Trust Limits**: New students start with a maximum of 2 concurrent pending requests. Quota increases as sessions are completed responsibly and positively rated.
- **F14 Connection Flow & Notifications**: Full lifecycle state machine (`PENDING` $\to$ `ACCEPTED` $\to$ `SCHEDULED` $\to$ `COMPLETED` / `DECLINED` / `CANCELLED`) with instant notification dispatch.
- **F17 Calendar & Video Integration**: Auto-generated Google Calendar event and meeting link (Jitsi or Google Meet) created upon request acceptance, handling timezone conversions.

### 6.5 Safe In-App Communications
- **F15 Contact-Masked Chat**: In-app messaging interface where email addresses and phone numbers are obscured by default to protect user privacy.
- **F16 Real-Time Scam & Off-Platform Detection**: Automated filter evaluating outbound chat messages against regular expressions and suspicious patterns:
  - Phone numbers, email leaks, external payment handles (UPI, PayPal, CashApp).
  - High-risk keywords (*"send money"*, *"crypto"*, *"telegram"*, *"whatsapp me"*).
  - Triggers soft warnings to user, blocks high-severity payloads, and logs incident to the moderation queue.

### 6.6 Economics, Sponsorship & Value Exchange
- **F18 Credit Economy & Escrow Engine**:
  - User wallet displaying available balance and escrow holds.
  - Subscription or credit bundle purchase options (mocked in demo).
  - Escrow hold placed on booking; 80% disbursed to giver upon completed session + rating; 20% platform maintenance fee.
  - Instant 100% refund on decline, expiration, or verified giver no-show.
- **F19 Sponsored Access Seats**: Institutional pool allowing underrepresented or financially constrained students to access cross-college credits funded by alumni donations or university funds.

### 6.7 Ratings, Endorsements & Quality Control
- **F20 Post-Session Tag-Based Ratings**: Givers can only be rated after a verified completed session. Structured multi-dimensional tags (*"Clear feedback"*, *"On time"*, *"Helpful technical advice"*, *"Actionable next steps"*) plus 1-5 star score.
- **F21 Reputation Bands & Leaderboards**: Giver progression from Rising to Top Rated. "Rising" givers receive algorithmic discovery boosts to prevent cold-start monopoly by senior alumni. Curated "Top Givers" institutional showcase.
- **F22 Post-Session Alumni Endorsements**: Option for alumni after an exceptional session to write a verified vouch or referral note displayed directly on the student's profile.
- **F23 Outlier Rating & Anti-Gaming Engine**: Statistical anomaly detection checking for reciprocal rating collusion, rapid succession rating spikes, or malicious 1-star retaliation.

### 6.8 Governance, Moderation & Specialized Workflows
- **F24 Human Review Queue & Moderation**: Admin dashboard reviewing flagged messages, dispute escalations, and reported profiles with 1-click actions: Dismiss, Warn, Suspend, or Ban.
- **F25 Faculty Mentorship Workflows**: Academic domain mentor profiles with verified department credentials, dedicated office-hour slots, and institutional honorarium allocations.
- **F26 Recruiter & Founder Hiring Channels**:
  - Posting verified job referrals, hiring sprints, and AMA sessions.
  - Verified Employer badges requiring validated business credentials.
- **F27 Curated Opportunities Engine**: Hackathons, internships, and workshops automatically matched to student skills, college affiliations, and target cities.
- **F28 Institution Analytics Dashboard**: University administration portal displaying request volume, fulfillment ratios, median response latencies, skills in high demand vs. supply, and pending alumni verification backlog.
- **F29 Longitudinal Outcome Tracking**: Post-connection check-in surveys at 30 and 90 days (*"Did this lead to an interview, referral, or project milestone?"*) to measure real institutional ROI.
- **F30 Interactive Network Graph**: Visual graph of university connection clusters, mentor-student paths, and cross-college affinity bridges rendered via interactive canvas/SVG.
- **F31 Integrated Seven Trust Layers**: Holistic system overview ensuring all 7 trust checkpoints are visibly surfaced across profiles, chats, and checkout flows.
- **F32 Closed-Loop Incident Learning**: Resolving moderation tickets automatically creates negative test vectors, updates scam regex patterns, and recalibrates user trust weights.
- **F33 DPDP Act Privacy by Design**: Full compliance with India's Digital Personal Data Protection Act:
  - Granular, affirmative consent checkpoints.
  - Role-based profile visibility toggles (hide CGPA, hide contact details).
  - 1-click machine-readable data export (JSON) and permanent "Right to be Forgotten" account deletion.
- **F34 Pilot Launch Metrics & Gates**: Dedicated readiness page tracking pilot thresholds (Target: 50 verified givers, 60% 72-hour reply rate) before institutional gating unlocks new colleges.
- **F35 Notification Center**: Real-time in-app dropdown and notification center tracking request updates, messages, verifications, and reminders.
- **F36 Jury Demo Sandbox Switcher**: Persistent bottom-bar demo toolbar enabling immediate switching between Student, Alumni, Faculty, Recruiter, Founder, and Admin personas, with a one-click **"Reset Database"** button to restore seed data.

---

## 7. User Interface & Design System

### 7.1 Aesthetic & Emotional Tone
- **Calm, High-Trust, Academic-Executive**: Avoids chaotic social media feeds or distracting gamification. Feels authoritative, trustworthy, and welcoming.
- **Color Palette**:
  - **Teal / Jade (`#0D9488` / `#14B8A6`)**: Primary brand color representing growth, trust, and clarity.
  - **Deep Navy (`#0F172A` / `#1E293B`)**: Background and structure representing institutional integrity.
  - **Coral (`#F43F5E` / `#FB7185`)**: High-contrast accent color reserved strictly for primary actions, badges, and notifications.
  - **Clean Neutrals (`#F8FAFC` / `#334155`)**: Slate tones for borders, surfaces, and secondary text.
- **Typography**: Clean humanist sans-serif (`Inter` or `Geist Sans`) with clear typographic hierarchy, large readable lead sentences, and high contrast ratios meeting WCAG 2.1 AA standards.
- **Accessibility & Responsiveness**: Full keyboard navigation, visible focus rings, responsive mobile layouts down to 320px width, and seamless light/dark mode toggling.

---

## 8. Definition of Done (DoD)

To mark any feature as **Done** in `FEATURES.md`:
1. **Full-Stack Implementation**: Fully operational across Next.js frontend and FastAPI backend.
2. **Real Database Persistence**: Operations persist to PostgreSQL (and Redis where applicable); no transient memory hacks.
3. **Validation & Error Handling**: Pydantic/Zod schemas validate inputs; user-friendly localized error alerts on failures.
4. **Automated Testing**: At least one automated test (backend pytest or frontend Vitest/Playwright test) asserting happy and edge-case paths.
5. **Verified Verification Steps**: Exact manual verification steps documented in `FEATURES.md`.
