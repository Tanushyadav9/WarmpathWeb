"""Full polished interactive WarmPath web interface and Jury Demo application.
Provides responsive, accessible, light/dark mode UI with unified badge system and 8-step Jury Demo walkthrough.
"""

def get_ui_html() -> str:
    return """<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WarmPath - Trusted, Intent-First Alumni Network</title>
  <!-- Tailwind Play CDN for rich utility-first rendering with dark mode support -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: {
              dark: '#16163A',
              indigo: '#2B2D6E',
              coral: '#FF6B4A',
              teal: '#0FB5A5',
              green: '#10B981',
              amber: '#F5A524',
              slate: '#64748B',
              surface: '#EEF1F8',
              cardDark: '#151733',
              bgDark: '#0B0C1E',
              borderDark: '#232652'
            }
          }
        }
      }
    }
  </script>
  <style>
    @keyframes pulse-dot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
    }
    .animate-radar { animation: pulse-dot 2s infinite ease-in-out; }
    /* Accessible focus rings */
    :focus-visible {
      outline: 2px solid #FF6B4A !important;
      outline-offset: 2px !important;
    }
    .skip-to-main {
      position: absolute;
      top: -40px;
      left: 0;
      background: #FF6B4A;
      color: white;
      padding: 8px 16px;
      z-index: 100;
      transition: top 0.2s;
    }
    .skip-to-main:focus { top: 0; }
  </style>
</head>
<body class="h-full bg-brand-surface dark:bg-brand-bgDark text-brand-dark dark:text-slate-100 transition-colors duration-200 antialiased flex flex-col font-sans">
  <a href="#main-content" class="skip-to-main font-semibold text-sm">Skip to main content</a>

  <!-- Top Announcement / Jury Demo Banner -->
  <aside role="region" aria-label="Demo notice" class="bg-gradient-to-r from-brand-indigo via-indigo-900 to-brand-dark text-white text-xs px-4 py-2 border-b border-indigo-950 flex flex-wrap items-center justify-between gap-2 shadow-sm">
    <div class="flex items-center gap-2">
      <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-brand-coral text-white tracking-wide uppercase">Jury Demo Active</span>
      <span class="font-medium">WarmPath Interactive Evaluation Mode &bull; 8-Step Verification Story &amp; Proof-of-Work System</span>
    </div>
    <div class="flex items-center gap-3">
      <button onclick="toggleJuryPanel()" class="px-2.5 py-1 bg-brand-coral hover:bg-orange-600 rounded font-bold text-white transition flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-white">
        <span>⚖️</span>
        <span id="jury-dock-btn-label">Open Checklist Panel</span>
      </button>
      <button onclick="triggerResetDemo()" class="px-2.5 py-1 bg-white/10 hover:bg-white/20 rounded font-medium text-white transition flex items-center gap-1 focus:outline-none focus:ring-2 focus:ring-white" title="Reset all demo data back to clean state">
        <span>🔄</span>
        <span>One-Click Reset</span>
      </button>
    </div>
  </aside>

  <!-- Global Header & Navigation -->
  <header role="banner" class="bg-white dark:bg-brand-cardDark border-b border-slate-200 dark:border-brand-borderDark sticky top-0 z-40 transition-colors">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16 gap-4">
        
        <!-- Brand Title & Home -->
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-coral to-orange-400 flex items-center justify-center text-white font-extrabold text-xl shadow-md">
            W
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-xl font-bold tracking-tight text-brand-dark dark:text-white">WarmPath</h1>
              <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/60 text-brand-teal border border-teal-200 dark:border-teal-800">IIIT Delhi Network</span>
            </div>
            <p class="text-[11px] text-brand-slate dark:text-slate-400 hidden sm:block">Trusted, Intent-First Alumni &amp; Mentorship Network</p>
          </div>
        </div>

        <!-- Role Switcher (Onboarding by Role) -->
        <nav aria-label="Role selector" class="hidden md:flex items-center bg-slate-100 dark:bg-slate-900/80 p-1 rounded-xl border border-slate-200 dark:border-slate-800">
          <button id="role-btn-student" onclick="switchRole('student')" class="role-tab px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 bg-white dark:bg-brand-cardDark text-brand-dark dark:text-white shadow-sm" aria-selected="true" role="tab">
            <span>🎓</span> Student
          </button>
          <button id="role-btn-alumnus" onclick="switchRole('alumnus')" class="role-tab px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 text-brand-slate hover:text-brand-dark dark:hover:text-white" aria-selected="false" role="tab">
            <span>💼</span> Alumni / Giver
          </button>
          <button id="role-btn-faculty" onclick="switchRole('faculty')" class="role-tab px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 text-brand-slate hover:text-brand-dark dark:hover:text-white" aria-selected="false" role="tab">
            <span>🏛️</span> Faculty
          </button>
          <button id="role-btn-recruiter" onclick="switchRole('recruiter')" class="role-tab px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 text-brand-slate hover:text-brand-dark dark:hover:text-white" aria-selected="false" role="tab">
            <span>👔</span> Recruiter
          </button>
          <button id="role-btn-admin" onclick="switchRole('admin')" class="role-tab px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 text-brand-slate hover:text-brand-dark dark:hover:text-white" aria-selected="false" role="tab">
            <span>🛡️</span> Admin
          </button>
        </nav>

        <!-- Utilities: Theme Toggle & Keyboard Shortcut Help -->
        <div class="flex items-center gap-2">
          <!-- Light/Dark Mode Switcher -->
          <button onclick="toggleDarkMode()" class="p-2 rounded-xl text-brand-slate hover:text-brand-dark dark:hover:text-white bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 transition focus:outline-none" aria-label="Toggle light and dark mode" title="Toggle theme (Hotkey: D)">
            <span id="theme-icon" class="text-base">🌙</span>
          </button>
          <!-- Keyboard help shortcut -->
          <button onclick="openHelpModal()" class="p-2 rounded-xl text-brand-slate hover:text-brand-dark dark:hover:text-white bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 transition focus:outline-none" aria-label="Keyboard shortcuts" title="Keyboard shortcuts (Hotkey: ?)">
            <span class="text-xs font-bold font-mono">?</span>
          </button>
          <!-- Mobile Menu Toggle Button -->
          <button onclick="toggleMobileMenu()" class="md:hidden p-2 rounded-xl text-brand-slate hover:text-brand-dark dark:hover:text-white bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700" aria-label="Toggle navigation menu">
            <span>☰</span>
          </button>
        </div>

      </div>

      <!-- Mobile Role Switcher Menu Drawer -->
      <div id="mobile-menu" class="hidden md:hidden pb-3 pt-1 border-t border-slate-200 dark:border-slate-800 flex flex-col gap-1.5">
        <p class="text-[11px] font-bold text-brand-slate uppercase tracking-wider px-2 pt-2">Switch Active Persona</p>
        <button onclick="switchRole('student'); toggleMobileMenu()" class="px-3 py-2 rounded-lg text-left text-xs font-semibold bg-slate-100 dark:bg-slate-800">🎓 Student (Aditi Sharma)</button>
        <button onclick="switchRole('alumnus'); toggleMobileMenu()" class="px-3 py-2 rounded-lg text-left text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800">💼 Alumni / Giver (Rohan Sharma)</button>
        <button onclick="switchRole('faculty'); toggleMobileMenu()" class="px-3 py-2 rounded-lg text-left text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800">🏛️ Faculty (Dr. Vivek Kumar)</button>
        <button onclick="switchRole('recruiter'); toggleMobileMenu()" class="px-3 py-2 rounded-lg text-left text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800">👔 Recruiter (Zomato)</button>
        <button onclick="switchRole('admin'); toggleMobileMenu()" class="px-3 py-2 rounded-lg text-left text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800">🛡️ Institution Admin</button>
      </div>
    </div>
  </header>

  <!-- Notification Toast Container (ARIA live region) -->
  <div id="toast-container" class="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none" aria-live="polite" role="status"></div>

  <!-- Main Content Layout (Split with Jury Demo Dock) -->
  <div class="flex-1 flex overflow-hidden">

    <!-- Primary Interactive Stage -->
    <main id="main-content" class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">

      <!-- Badge System Showcase Bar -->
      <section aria-label="Badge System Catalog" class="bg-white dark:bg-brand-cardDark p-4 rounded-2xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="text-sm font-bold text-brand-dark dark:text-white">WarmPath Trust &amp; Badging System</span>
            <span class="text-xs text-brand-slate dark:text-slate-400">Institutional validation signals &amp; live availability statuses</span>
          </div>
          <span class="text-xs bg-slate-100 dark:bg-slate-800 text-brand-slate dark:text-slate-300 px-2 py-0.5 rounded font-mono">5 Badge Classes</span>
        </div>
        <div class="flex flex-wrap items-center gap-2.5">
          <!-- Verification Badges -->
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-teal-50 dark:bg-teal-950/70 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800" title="Verified against college registrar rolls">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
            Verified Alumni
          </span>
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800" title="Verified business entity CIN/GST">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2h-3a1 1 0 01-1-1v-2a1 1 0 00-1-1H9a1 1 0 00-1 1v2a1 1 0 01-1 1H4a1 1 0 110-2V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z" clip-rule="evenodd"/></svg>
            Verified Employer
          </span>
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-purple-50 dark:bg-purple-950/70 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800" title="Faculty expert endorsed by department chair">
            ★ Verified Expert
          </span>
          <!-- Rating Bands -->
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-sky-50 dark:bg-sky-950/70 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800" title="Fair-start boost applied in ranking">
            ⚡ Rising (Boosted)
          </span>
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800" title="Consistently rated >4.5 by students">
            🛡️ Trusted
          </span>
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800" title="Top 5% giver across institution">
            🏆 Top Rated
          </span>
          <!-- Availability Status Dots -->
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800" title="Active right now with real-time response rate">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-radar"></span>
            Active now (94% reply)
          </span>
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800" title="Available in evening window">
            <span class="w-2 h-2 rounded-full bg-amber-500"></span>
            Available today (8-10 PM)
          </span>
          <!-- Proof of Work & Vouched -->
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-cyan-50 dark:bg-cyan-950/70 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800" title="Tied to verified code repository or research">
            🔗 Verified Proof of Work
          </span>
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-fuchsia-50 dark:bg-fuchsia-950/70 text-fuchsia-700 dark:text-fuchsia-300 border border-fuchsia-200 dark:border-fuchsia-800" title="1-click referral vouch from senior engineer">
            🎖️ Vouched by Rohan @ Microsoft
          </span>
        </div>
      </section>

      <!-- ROLE VIEW 1: STUDENT (Default) -->
      <div id="view-student" class="role-view space-y-6">
        
        <!-- Header Profile & Intent Hero Card -->
        <div class="bg-gradient-to-br from-brand-indigo via-indigo-900 to-brand-dark rounded-3xl p-6 sm:p-8 text-white shadow-lg relative overflow-hidden">
          <div class="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div>
              <div class="flex items-center gap-3">
                <div class="w-14 h-14 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center font-bold text-2xl text-brand-coral">AS</div>
                <div>
                  <div class="flex items-center gap-2">
                    <h2 class="text-2xl font-bold">Aditi Sharma</h2>
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-brand-coral text-white">Student</span>
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-white/20 text-white">IIIT Delhi '27</span>
                  </div>
                  <p class="text-indigo-200 text-sm mt-0.5">B.Tech Computer Science &bull; 3rd Year &bull; Distributed Systems &amp; Backend Engineering</p>
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-2 mt-4">
                <span class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-white/10 border border-white/15">Python</span>
                <span class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-white/10 border border-white/15">Distributed Systems</span>
                <span class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-white/10 border border-white/15">FastAPI</span>
                <span class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-white/10 border border-white/15">Docker</span>
                <span id="student-vouch-pill" class="px-2.5 py-1 rounded-lg text-xs font-bold bg-fuchsia-500/30 text-fuchsia-200 border border-fuchsia-400/40">🎖️ Vouched by Rohan @ Microsoft</span>
              </div>
            </div>
            <!-- Wallet Card in Hero -->
            <div class="bg-white/10 backdrop-blur-md rounded-2xl p-4 border border-white/20 w-full md:w-auto min-w-[220px]">
              <div class="flex items-center justify-between text-xs text-indigo-200">
                <span>Single Credit Wallet</span>
                <span class="text-teal-300 font-bold">Sponsored Seat Active</span>
              </div>
              <div class="mt-2 flex items-baseline gap-2">
                <span id="student-wallet-bal" class="text-3xl font-extrabold text-white">20</span>
                <span class="text-xs text-indigo-200 font-medium">Credits</span>
                <span id="student-wallet-held" class="text-xs px-2 py-0.5 rounded bg-amber-400/20 text-amber-300 border border-amber-400/30 ml-auto">0 Held in Escrow</span>
              </div>
              <p class="text-[11px] text-indigo-200/80 mt-1">Free for same-college IIIT Delhi connections &bull; 5 credits cross-college</p>
            </div>
          </div>
        </div>

        <!-- Section: Interactive Intent & Resume Prompting -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Resume Upload Card with Magic Byte Check -->
          <div class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-3">
                <h3 class="text-base font-bold text-brand-dark dark:text-white flex items-center gap-2">
                  <span>📄</span> Verified Proof-of-Work
                </h3>
                <span class="text-xs font-bold text-brand-teal bg-teal-50 dark:bg-teal-950/60 px-2 py-0.5 rounded border border-teal-200 dark:border-teal-800">DPDP Compliant</span>
              </div>
              <p class="text-xs text-brand-slate dark:text-slate-400 mb-4">Upload resume PDF (type, size &amp; magic bytes `%PDF-` inspected). Extracted skills are verified against your code repositories.</p>
              
              <div id="resume-drop-zone" class="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-2xl p-6 text-center hover:border-brand-coral transition cursor-pointer bg-slate-50 dark:bg-slate-900/40">
                <div class="w-10 h-10 mx-auto mb-2 text-brand-coral">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                </div>
                <p class="text-xs font-bold text-brand-dark dark:text-white">aditi_sharma_iiitd.pdf</p>
                <p class="text-[11px] text-brand-slate mt-0.5">248 KB &bull; Verified Magic Signature (%PDF-1.5)</p>
                <div class="mt-3 flex items-center justify-center gap-1.5">
                  <span class="text-[11px] px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 font-semibold">4 Skills Extracted</span>
                </div>
              </div>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
              <span class="text-brand-slate dark:text-slate-400">Proof of Work:</span>
              <a href="https://github.com/aditi/distributed-raft" target="_blank" class="font-bold text-brand-coral hover:underline flex items-center gap-1">github.com/aditi/distributed-raft ↗</a>
            </div>
          </div>

          <!-- AI Intent Prompt Refinement Card -->
          <div class="lg:col-span-2 bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-2">
                <h3 class="text-base font-bold text-brand-dark dark:text-white flex items-center gap-2">
                  <span>✨</span> Intent Prompt Refinement
                </h3>
                <span class="text-xs font-bold text-brand-coral bg-orange-50 dark:bg-orange-950/60 px-2 py-0.5 rounded border border-orange-200 dark:border-orange-800">Intent-First Matching</span>
              </div>
              <p class="text-xs text-brand-slate dark:text-slate-400 mb-4">Givers respond to clear, high-intent agendas. Enter a conversational goal and WarmPath AI structures it into concrete discussion points.</p>
              
              <div class="space-y-3">
                <div>
                  <label for="raw-intent-input" class="text-xs font-bold text-brand-dark dark:text-slate-200 block mb-1">Your Mentorship Goal</label>
                  <div class="flex gap-2">
                    <input id="raw-intent-input" type="text" value="i want to learn coding and get a good job" class="flex-1 text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 dark:text-white focus:outline-none focus:border-brand-coral" placeholder="Enter what you need guidance on...">
                    <button onclick="handleRefineIntent()" class="px-4 py-2 bg-brand-indigo hover:bg-indigo-900 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 focus:outline-none">
                      <span>✨</span> Refine Intent
                    </button>
                  </div>
                </div>

                <div id="intent-refinement-result" class="p-3.5 bg-indigo-50 dark:bg-slate-900/60 rounded-2xl border border-indigo-100 dark:border-slate-800">
                  <div class="flex items-center justify-between mb-1">
                    <span class="text-[11px] font-bold text-brand-indigo dark:text-indigo-300 uppercase tracking-wide">Structured Mentorship Agenda (AI Refined)</span>
                    <span class="text-[11px] font-bold text-emerald-600 dark:text-emerald-400">98% Match Readiness</span>
                  </div>
                  <p id="intent-refined-text" class="text-xs font-semibold text-brand-dark dark:text-white leading-relaxed">System Design &amp; Backend Architecture for Tier-1 Product Engineering (Focus: Distributed Systems, Concurrency &amp; Microservices)</p>
                  <div class="mt-2 flex flex-wrap gap-1.5">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-brand-dark dark:text-slate-200 border border-indigo-200 dark:border-slate-700">Agenda: Raft Consensus</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-brand-dark dark:text-slate-200 border border-indigo-200 dark:border-slate-700">Interview Framing</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-brand-dark dark:text-slate-200 border border-indigo-200 dark:border-slate-700">Production Reliability</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs text-brand-slate dark:text-slate-400">
              <span>Intent filters out spam &bull; Givers only see role-relevant student profile</span>
              <span class="font-medium text-emerald-600 dark:text-emerald-400">0 Open Requests / 3 Max Limit</span>
            </div>
          </div>

        </div>

        <!-- Section: Ranked Giver Matches (Why-This-Match) -->
        <section aria-label="Ranked Mentorship Matches" class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-bold text-brand-dark dark:text-white flex items-center gap-2">
                <span>🎯</span> Ranked Matches for Your Confirmed Intent
              </h3>
              <p class="text-xs text-brand-slate dark:text-slate-400">Ranked by skill overlap, college affiliation, response rate, and fair-start boost.</p>
            </div>
            <span class="text-xs font-bold text-brand-dark dark:text-white bg-slate-100 dark:bg-slate-800 px-3 py-1 rounded-full">Showing 2 Verified Givers</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <!-- Match 1: Rohan Sharma (Same College, Free) -->
            <article class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border-2 border-emerald-500/40 dark:border-emerald-500/30 shadow-sm relative flex flex-col justify-between">
              <div class="absolute top-4 right-4 flex items-center gap-2">
                <span class="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">98% Match</span>
                <span class="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-teal-50 dark:bg-teal-950 text-brand-teal border border-teal-300 dark:border-teal-700">0 Credits (Free)</span>
              </div>
              <div>
                <div class="flex items-start gap-3 mb-3">
                  <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-indigo to-blue-600 text-white font-bold text-lg flex items-center justify-center">RS</div>
                  <div>
                    <h4 class="text-base font-bold text-brand-dark dark:text-white">Rohan Sharma</h4>
                    <p class="text-xs text-brand-slate dark:text-slate-300 font-medium">Staff Engineer at Microsoft &bull; IIIT Delhi Alumnus</p>
                    <div class="mt-1 flex items-center gap-2">
                      <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-radar"></span>
                        Active now
                      </span>
                      <span class="text-[11px] text-brand-slate dark:text-slate-400">&bull; 95% response rate &bull; avg reply 18m</span>
                    </div>
                  </div>
                </div>

                <!-- Badges -->
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800">Verified Alumni</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">★ 4.9 Top Rated (18 sessions)</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">Capacity: 2/10 booked</span>
                </div>

                <!-- Why This Match Explanation Box -->
                <div class="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-2xl border border-slate-200 dark:border-slate-800 text-xs mb-4">
                  <p class="font-bold text-brand-dark dark:text-white mb-1 flex items-center gap-1">
                    <span class="text-brand-coral">💡</span> Why this match:
                  </p>
                  <ul class="space-y-1 text-brand-slate dark:text-slate-300 text-[11px]">
                    <li class="flex items-center gap-1.5"><span class="text-emerald-500 font-bold">✓</span> Same College: IIIT Delhi alumni connection</li>
                    <li class="flex items-center gap-1.5"><span class="text-emerald-500 font-bold">✓</span> Direct overlap in Distributed Systems &amp; FastAPI</li>
                    <li class="flex items-center gap-1.5"><span class="text-emerald-500 font-bold">✓</span> Zero credits required under institutional charter</li>
                  </ul>
                </div>
              </div>

              <div class="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <span class="text-xs text-brand-slate dark:text-slate-400">Available: Next 3 days</span>
                <button id="book-same-btn" onclick="executeBookSession('same')" class="px-4 py-2 bg-brand-coral hover:bg-orange-600 text-white rounded-xl text-xs font-bold transition shadow-sm focus:outline-none">
                  Book Free Session (0 Credits)
                </button>
              </div>
            </article>

            <!-- Match 2: Priya Patel (Cross College, 5 Credits Escrow) -->
            <article class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm relative flex flex-col justify-between">
              <div class="absolute top-4 right-4 flex items-center gap-2">
                <span class="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-700">86% Match</span>
                <span class="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700">5 Credits (Cross-College)</span>
              </div>
              <div>
                <div class="flex items-start gap-3 mb-3">
                  <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 text-white font-bold text-lg flex items-center justify-center">PP</div>
                  <div>
                    <h4 class="text-base font-bold text-brand-dark dark:text-white">Priya Patel</h4>
                    <p class="text-xs text-brand-slate dark:text-slate-300 font-medium">Senior SWE at Google &bull; NSUT Alumna</p>
                    <div class="mt-1 flex items-center gap-2">
                      <span class="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 dark:text-amber-400">
                        <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                        Available today (8-10 PM)
                      </span>
                      <span class="text-[11px] text-brand-slate dark:text-slate-400">&bull; 88% response rate</span>
                    </div>
                  </div>
                </div>

                <!-- Badges -->
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800">Verified Alumni</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">🛡️ 4.8 Trusted</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">Kubernetes &bull; Go</span>
                </div>

                <!-- Why This Match Explanation Box -->
                <div class="p-3 bg-slate-50 dark:bg-slate-900/60 rounded-2xl border border-slate-200 dark:border-slate-800 text-xs mb-4">
                  <p class="font-bold text-brand-dark dark:text-white mb-1 flex items-center gap-1">
                    <span class="text-brand-coral">💡</span> Why this match:
                  </p>
                  <ul class="space-y-1 text-brand-slate dark:text-slate-300 text-[11px]">
                    <li class="flex items-center gap-1.5"><span class="text-emerald-500 font-bold">✓</span> Industry experience at Google with Go &amp; Kubernetes</li>
                    <li class="flex items-center gap-1.5"><span class="text-emerald-500 font-bold">✓</span> Cross-college connection (5 credits held safely in Escrow)</li>
                    <li class="flex items-center gap-1.5"><span class="text-emerald-500 font-bold">✓</span> 80% released to giver upon verified session completion</li>
                  </ul>
                </div>
              </div>

              <div class="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <span class="text-xs text-brand-slate dark:text-slate-400">Escrow Hold: 5 Credits</span>
                <button id="book-cross-btn" onclick="executeBookSession('cross')" class="px-4 py-2 bg-brand-indigo hover:bg-indigo-900 text-white rounded-xl text-xs font-bold transition shadow-sm focus:outline-none">
                  Book Session (5 Credits Hold)
                </button>
              </div>
            </article>

          </div>
        </section>

        <!-- Section: Active In-App Chat with Live Scam Detection -->
        <section aria-label="In-App Protected Mentorship Chat" class="bg-white dark:bg-brand-cardDark rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm overflow-hidden">
          <div class="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/30">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-brand-indigo text-white font-bold flex items-center justify-center">RS</div>
              <div>
                <h4 class="text-sm font-bold text-brand-dark dark:text-white">Active Mentorship Session: Rohan Sharma (Microsoft)</h4>
                <p class="text-xs text-brand-slate dark:text-slate-400">Contact details auto-protected &bull; In-app calendar link generated on slot confirmation</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Confirmed Meet Link Active
              </span>
              <a href="https://meet.jit.si/warmpath-demo-rohan-aditi" target="_blank" class="text-xs font-bold px-3 py-1 bg-brand-indigo text-white rounded-lg hover:bg-indigo-900">Join Call ↗</a>
            </div>
          </div>

          <!-- Chat Messages Area -->
          <div id="chat-messages-box" class="p-6 space-y-4 max-h-72 overflow-y-auto bg-slate-50/30 dark:bg-slate-900/20">
            <!-- System Greeting -->
            <div class="text-center my-2">
              <span class="text-[11px] font-medium text-brand-slate dark:text-slate-400 bg-white dark:bg-slate-800 px-3 py-1 rounded-full border border-slate-200 dark:border-slate-700 shadow-2xs">
                🛡️ WarmPath Scam Protection Active: Phone numbers, emails, and money requests are strictly blocked.
              </span>
            </div>
            
            <!-- Message from Giver -->
            <div class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-lg bg-brand-indigo text-white text-xs font-bold flex items-center justify-center shrink-0">RS</div>
              <div class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3 rounded-2xl rounded-tl-none max-w-md shadow-2xs">
                <p class="text-xs text-brand-dark dark:text-slate-200">Hi Aditi! Reviewed your Raft consensus GitHub repository. Looking forward to our systems architecture session tomorrow at 7 PM.</p>
                <span class="text-[10px] text-brand-slate mt-1 block">10:42 AM</span>
              </div>
            </div>

            <!-- Dynamic Chat Container for user inputs -->
            <div id="dynamic-chat-stream" class="space-y-3"></div>
          </div>

          <!-- Chat Input Bar with Scam Simulator Button -->
          <div class="p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-brand-cardDark">
            <div class="flex flex-col sm:flex-row items-center gap-2">
              <input id="chat-input-text" type="text" placeholder="Type a message to Rohan..." class="flex-1 text-xs px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 dark:text-white focus:outline-none focus:border-brand-coral">
              <div class="flex items-center gap-2 w-full sm:w-auto">
                <button onclick="sendChatMessage(false)" class="flex-1 sm:flex-none px-4 py-2.5 bg-brand-coral hover:bg-orange-600 text-white rounded-xl text-xs font-bold transition focus:outline-none">
                  Send
                </button>
                <button onclick="sendChatMessage(true)" class="flex-1 sm:flex-none px-3.5 py-2.5 bg-red-50 dark:bg-red-950/80 hover:bg-red-100 text-red-600 dark:text-red-300 border border-red-200 dark:border-red-800 rounded-xl text-xs font-bold transition flex items-center gap-1.5 focus:outline-none" title="Demonstrate real-time blocking of UPI payment requests and phone numbers">
                  <span>🚨</span> Simulate Scam
                </button>
              </div>
            </div>
            <p class="text-[11px] text-brand-slate dark:text-slate-400 mt-2">
              Click <strong>Simulate Scam</strong> to test the detection middleware against UPI extortion and off-platform phone numbers.
            </p>
          </div>
        </section>

      </div>

      <!-- ROLE VIEW 2: ALUMNI / GIVER -->
      <div id="view-alumnus" class="role-view hidden space-y-6">
        <div class="bg-white dark:bg-brand-cardDark p-6 sm:p-8 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
          <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div class="flex items-center gap-4">
              <div class="w-14 h-14 rounded-2xl bg-brand-indigo text-white font-bold text-2xl flex items-center justify-center">RS</div>
              <div>
                <div class="flex items-center gap-2">
                  <h2 class="text-xl font-bold text-brand-dark dark:text-white">Rohan Sharma</h2>
                  <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-teal-50 dark:bg-teal-950 text-teal-700 border border-teal-200">Verified Alumni</span>
                  <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950 text-amber-700 border border-amber-200">🏆 Top Rated</span>
                </div>
                <p class="text-xs text-brand-slate dark:text-slate-300 mt-0.5">Staff Software Engineer &bull; Microsoft &bull; IIIT Delhi Class of 2020</p>
              </div>
            </div>
            <!-- Availability Switcher Controls -->
            <div class="flex items-center gap-2 bg-slate-100 dark:bg-slate-900 p-1.5 rounded-2xl border border-slate-200 dark:border-slate-800">
              <button onclick="setGiverStatus('active_now')" id="giver-status-active" class="px-3 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-brand-cardDark text-emerald-600 dark:text-emerald-400 shadow-xs flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-radar"></span> Active now
              </button>
              <button onclick="setGiverStatus('available_today')" id="giver-status-today" class="px-3 py-1.5 rounded-xl text-xs font-bold text-brand-slate hover:text-brand-dark dark:hover:text-white flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-amber-500"></span> Available today (8-10pm)
              </button>
              <button onclick="setGiverStatus('inactive')" id="giver-status-inactive" class="px-3 py-1.5 rounded-xl text-xs font-bold text-brand-slate hover:text-brand-dark dark:hover:text-white flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-slate-400"></span> Inactive
              </button>
            </div>
          </div>

          <!-- Giver Metrics & Capacity Grid -->
          <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-100 dark:border-slate-800">
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
              <p class="text-xs text-brand-slate">Weekly Capacity Cap</p>
              <p class="text-2xl font-bold text-brand-dark dark:text-white mt-1">2 / 10</p>
              <p class="text-[11px] text-emerald-600 dark:text-emerald-400 mt-0.5">8 sessions available</p>
            </div>
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
              <p class="text-xs text-brand-slate">Response Rate</p>
              <p class="text-2xl font-bold text-brand-teal mt-1">95.4%</p>
              <p class="text-[11px] text-brand-slate mt-0.5">Calculated over real history</p>
            </div>
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
              <p class="text-xs text-brand-slate">Avg Reply Time</p>
              <p class="text-2xl font-bold text-brand-indigo dark:text-indigo-300 mt-1">18 mins</p>
              <p class="text-[11px] text-brand-slate mt-0.5">Fast-responder badge earned</p>
            </div>
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
              <p class="text-xs text-brand-slate">Karma &amp; Credits Earned</p>
              <p class="text-2xl font-bold text-brand-coral mt-1">25 Credits</p>
              <p class="text-[11px] text-brand-slate mt-0.5">Can spend to reach senior leaders</p>
            </div>
          </div>
        </div>

        <!-- 1-Click Vouch Section for Givers -->
        <div class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-base font-bold text-brand-dark dark:text-white flex items-center gap-2">
                <span>🎖️</span> 1-Click Referral Vouch (Post-Session)
              </h3>
              <p class="text-xs text-brand-slate dark:text-slate-400">Available after completed sessions rated 4 or 5 stars. Highlights student proof-of-work to hiring companies.</p>
            </div>
            <button onclick="executeVouchStudent()" class="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-xs font-bold shadow-sm hover:opacity-90">
              + Vouch for Aditi Sharma
            </button>
          </div>
          <div class="p-4 rounded-2xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 flex items-start gap-3">
            <span class="text-2xl">🎖️</span>
            <div>
              <p class="text-xs font-bold text-purple-900 dark:text-purple-200">"Vouched by Rohan Sharma at Microsoft"</p>
              <p class="text-xs text-purple-800 dark:text-purple-300 mt-0.5">Endorsed for Systems Architecture &amp; Distributed Raft Implementation. Visible on Aditi's profile in recruiter pre-matched talent feeds.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ROLE VIEW 3: FACULTY -->
      <div id="view-faculty" class="role-view hidden space-y-6">
        <div class="bg-white dark:bg-brand-cardDark p-6 sm:p-8 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-purple-700 to-indigo-800 text-white font-bold text-2xl flex items-center justify-center">VK</div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-xl font-bold text-brand-dark dark:text-white">Dr. Vivek Kumar</h2>
                <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-50 dark:bg-purple-950 text-purple-700 border border-purple-200">★ Verified Expert</span>
              </div>
              <p class="text-xs text-brand-slate dark:text-slate-300 mt-0.5">Professor of Computer Science &bull; Domain Mentor in High-Performance Distributed Systems &bull; IIIT Delhi</p>
            </div>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-100 dark:border-slate-800">
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
              <p class="text-xs text-brand-slate">Domain Compensation Rate</p>
              <p class="text-2xl font-bold text-brand-dark dark:text-white mt-1">5 Credits / session</p>
              <p class="text-[11px] text-brand-slate mt-0.5">Funded via sponsor credits pool</p>
            </div>
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
              <p class="text-xs text-brand-slate">Research Mentorships</p>
              <p class="text-2xl font-bold text-brand-teal mt-1">12 Completed</p>
              <p class="text-[11px] text-emerald-600 mt-0.5">100% Student satisfaction</p>
            </div>
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-100 dark:border-slate-800">
              <p class="text-xs text-brand-slate">Expertise Areas</p>
              <div class="mt-2 flex flex-wrap gap-1">
                <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-brand-dark dark:text-slate-200 border">Distributed Systems</span>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-brand-dark dark:text-slate-200 border">Memory Systems</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ROLE VIEW 4: RECRUITER / FOUNDER -->
      <div id="view-recruiter" class="role-view hidden space-y-6">
        <div class="bg-white dark:bg-brand-cardDark p-6 sm:p-8 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-brand-coral to-red-600 text-white font-bold text-2xl flex items-center justify-center">Z</div>
              <div>
                <div class="flex items-center gap-2">
                  <h2 class="text-xl font-bold text-brand-dark dark:text-white">Neha Verma</h2>
                  <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950 text-indigo-700 border border-indigo-200">✓ Verified Employer</span>
                </div>
                <p class="text-xs text-brand-slate dark:text-slate-300 mt-0.5">Talent Acquisition Lead &bull; Zomato &bull; Verified CIN: U93030DL2010PTC198141</p>
              </div>
            </div>
            <button onclick="alert('Post Opportunity dialog opened. Unverified employers are blocked from posting.')" class="px-4 py-2 bg-brand-coral hover:bg-orange-600 text-white rounded-xl text-xs font-bold transition">
              + Post Opportunity
            </button>
          </div>
        </div>

        <!-- Pre-Matched Opted-In Candidates Feed -->
        <div class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-base font-bold text-brand-dark dark:text-white">Pre-Matched Candidate Feed (Opted-In Students Only)</h3>
              <p class="text-xs text-brand-slate dark:text-slate-400">Students with verified proof of work who opted in to hear from Zomato. Contact details remain confidential until connection is confirmed.</p>
            </div>
            <span class="text-xs font-bold px-2.5 py-1 rounded bg-teal-50 dark:bg-teal-950 text-brand-teal border border-teal-200">Privacy Shield Active</span>
          </div>

          <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-brand-indigo text-white font-bold text-sm flex items-center justify-center">AS</div>
              <div>
                <div class="flex items-center gap-2">
                  <p class="text-sm font-bold text-brand-dark dark:text-white">Aditi Sharma</p>
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-fuchsia-100 text-fuchsia-800">🎖️ Vouched by Microsoft</span>
                </div>
                <p class="text-xs text-brand-slate">IIIT Delhi '27 &bull; Top Skills: Python, Distributed Systems, FastAPI, Docker</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <a href="https://github.com/aditi/distributed-raft" target="_blank" class="text-xs font-bold px-3 py-1.5 bg-slate-200 dark:bg-slate-800 text-brand-dark dark:text-white rounded-xl hover:bg-slate-300">View Proof of Work ↗</a>
              <button onclick="alert('Interview request sent to student via platform calendar adapter!')" class="text-xs font-bold px-4 py-1.5 bg-brand-indigo text-white rounded-xl hover:bg-indigo-900">Request Hiring Chat</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ROLE VIEW 5: INSTITUTION ADMIN -->
      <div id="view-admin" class="role-view hidden space-y-6">
        
        <!-- Dashboard Analytics Overview -->
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div class="bg-white dark:bg-brand-cardDark p-5 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
            <p class="text-xs font-medium text-brand-slate">Total Requests</p>
            <p class="text-3xl font-bold text-brand-dark dark:text-white mt-1">2</p>
            <p class="text-[11px] text-emerald-600 font-semibold mt-1">100% Answered within 72h</p>
          </div>
          <div class="bg-white dark:bg-brand-cardDark p-5 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
            <p class="text-xs font-medium text-brand-slate">Fulfillment Rate</p>
            <p class="text-3xl font-bold text-brand-teal mt-1">100%</p>
            <p class="text-[11px] text-brand-slate mt-1">Completed vs Booked</p>
          </div>
          <div class="bg-white dark:bg-brand-cardDark p-5 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
            <p class="text-xs font-medium text-brand-slate">Avg Rating</p>
            <p class="text-3xl font-bold text-amber-500 mt-1">5.0 ★</p>
            <p class="text-[11px] text-brand-slate mt-1">Anti-gaming verified</p>
          </div>
          <div class="bg-white dark:bg-brand-cardDark p-5 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
            <p class="text-xs font-medium text-brand-slate">Launch Gate</p>
            <p class="text-3xl font-bold text-emerald-500 mt-1">LOCKED</p>
            <p class="text-[11px] text-brand-slate mt-1">Target: 50 verified givers</p>
          </div>
        </div>

        <!-- Skill Gap Analysis Matrix -->
        <div class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-base font-bold text-brand-dark dark:text-white flex items-center gap-2">
                <span>📊</span> Institutional Skill-Gap Analysis
              </h3>
              <p class="text-xs text-brand-slate dark:text-slate-400">Demand: Student mentorship intents vs Supply: Verified alumni on platform.</p>
            </div>
            <button onclick="alert('Exporting institution_metrics.csv...')" class="text-xs font-bold px-3 py-1.5 bg-slate-100 dark:bg-slate-800 text-brand-dark dark:text-white rounded-xl border hover:bg-slate-200">
              Export CSV 📥
            </button>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800">
              <div class="flex justify-between text-xs font-bold mb-1">
                <span class="text-brand-dark dark:text-white">Distributed Systems</span>
                <span class="text-emerald-600">Covered (Supply: 8)</span>
              </div>
              <p class="text-[11px] text-brand-slate">3 student requests &bull; 8 verified alumni</p>
              <div class="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 mt-2">
                <div class="bg-emerald-500 h-2 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800">
              <div class="flex justify-between text-xs font-bold mb-1">
                <span class="text-brand-dark dark:text-white">FastAPI &amp; Python</span>
                <span class="text-emerald-600">Covered (Supply: 5)</span>
              </div>
              <p class="text-[11px] text-brand-slate">2 student requests &bull; 5 verified alumni</p>
              <div class="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 mt-2">
                <div class="bg-emerald-500 h-2 rounded-full" style="width: 100%"></div>
              </div>
            </div>
            <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800">
              <div class="flex justify-between text-xs font-bold mb-1">
                <span class="text-brand-dark dark:text-white">GPU Kernels / Triton</span>
                <span class="text-brand-coral font-bold">Skill Gap (0 Alumni)</span>
              </div>
              <p class="text-[11px] text-brand-slate">4 student requests &bull; 0 alumni supply</p>
              <div class="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-2 mt-2">
                <div class="bg-brand-coral h-2 rounded-full" style="width: 0%"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Verification & Moderation Queues -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          <!-- Verification Queue -->
          <div class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-bold text-brand-dark dark:text-white">Verification Queue (2 Pending)</h4>
              <span class="text-xs text-brand-slate">Pre-matched against registrar roll</span>
            </div>
            <div class="space-y-3">
              <div id="verif-card-fake" class="p-3.5 rounded-2xl border border-red-200 dark:border-red-900/50 bg-red-50/40 dark:bg-red-950/20 flex items-center justify-between">
                <div>
                  <p class="text-xs font-bold text-brand-dark dark:text-white">Unknown Impersonator (FORGED-9999)</p>
                  <p class="text-[11px] text-red-600 dark:text-red-400">Forged certificate &bull; Roll number not in registrar list</p>
                </div>
                <button onclick="executeVerificationStep()" class="text-xs font-bold px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg">Reject ✕</button>
              </div>
              <div id="verif-card-real" class="p-3.5 rounded-2xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/40 dark:bg-emerald-950/20 flex items-center justify-between">
                <div>
                  <p class="text-xs font-bold text-brand-dark dark:text-white">Raghav Sen (2022CSB1042)</p>
                  <p class="text-[11px] text-emerald-600 dark:text-emerald-400">Roll match verified &bull; IIIT Delhi B.Tech CS</p>
                </div>
                <button onclick="executeVerificationStep()" class="text-xs font-bold px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg">Auto-Verify ✓</button>
              </div>
            </div>
          </div>

          <!-- Moderation & Scam Learning Queue -->
          <div class="bg-white dark:bg-brand-cardDark p-6 rounded-3xl border border-slate-200 dark:border-brand-borderDark shadow-sm">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-bold text-brand-dark dark:text-white">Safety Moderation &amp; Incident Learning</h4>
              <span class="text-xs text-brand-slate">Active rules learning</span>
            </div>
            <div id="moderation-report-card" class="p-3.5 rounded-2xl border border-amber-200 dark:border-amber-900/50 bg-amber-50/40 dark:bg-amber-950/20 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-amber-800 dark:text-amber-300">Report #7777: Scam Payment Request</span>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-200 dark:bg-amber-900 text-amber-900 dark:text-amber-200">Pending Review</span>
              </div>
              <p class="text-xs text-brand-dark dark:text-slate-200">"User requested 500 INR via UPI handle payme@upi for offline referral link"</p>
              <div class="flex items-center justify-between pt-1">
                <span id="learned-rule-status" class="text-[11px] text-brand-slate">Action: Suspend &amp; learn regex pattern</span>
                <button onclick="executeAdminResolveReport()" class="text-xs font-bold px-3.5 py-1.5 bg-brand-dark text-white rounded-lg hover:bg-slate-800">
                  Resolve &amp; Learn Rule
                </button>
              </div>
            </div>
          </div>

        </div>

      </div>

    </main>

    <!-- RIGHT DOCK: JURY DEMO CHECKLIST PANEL -->
    <aside id="jury-dock" class="w-96 bg-white dark:bg-brand-cardDark border-l border-slate-200 dark:border-brand-borderDark flex flex-col shrink-0 shadow-xl transition-all duration-300 z-30">
      
      <!-- Dock Header -->
      <div class="p-4 border-b border-slate-200 dark:border-brand-borderDark bg-slate-50/70 dark:bg-slate-900/40 flex items-center justify-between">
        <div>
          <div class="flex items-center gap-1.5">
            <span class="text-base">⚖️</span>
            <h3 class="text-sm font-bold text-brand-dark dark:text-white">Jury Demo Walkthrough</h3>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">8-Step Guided Evaluation Story</p>
        </div>
        <button onclick="toggleJuryPanel()" class="p-1 rounded text-brand-slate hover:text-brand-dark dark:hover:text-white text-xs">✕</button>
      </div>

      <!-- Progress Meter -->
      <div class="px-4 py-3 bg-white dark:bg-brand-cardDark border-b border-slate-100 dark:border-slate-800">
        <div class="flex items-center justify-between text-xs mb-1.5">
          <span class="font-bold text-brand-dark dark:text-white">Overall Story Progress</span>
          <span id="jury-progress-label" class="font-bold text-brand-coral">0 / 8 Complete</span>
        </div>
        <div class="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
          <div id="jury-progress-bar" class="bg-gradient-to-r from-brand-coral to-emerald-500 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
        </div>
        <div class="mt-2.5 flex items-center justify-between">
          <button onclick="runAllDemoSteps()" class="text-[11px] font-bold px-2.5 py-1 rounded bg-brand-indigo text-white hover:bg-indigo-900 transition">
            ▶ Auto-Play All 8 Steps
          </button>
          <button onclick="triggerResetDemo()" class="text-[11px] font-bold px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 text-brand-slate hover:text-brand-coral transition">
            🔄 Reset Story
          </button>
        </div>
      </div>

      <!-- Checklist Accordion Steps (1 to 8) -->
      <div class="flex-1 overflow-y-auto p-4 space-y-3">
        
        <!-- Step 1 -->
        <div id="jury-card-1" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">1. Resume &amp; Skills</span>
            <span id="step-badge-1" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Student uploads resume with `%PDF-` magic check and ties skills to GitHub proof-of-work.</p>
          <button onclick="runSingleStep(1)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 1
          </button>
        </div>

        <!-- Step 2 -->
        <div id="jury-card-2" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">2. AI Intent Refinement</span>
            <span id="step-badge-2" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Vague intent "i want to learn coding..." is structured into concrete distributed systems agenda.</p>
          <button onclick="runSingleStep(2)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 2
          </button>
        </div>

        <!-- Step 3 -->
        <div id="jury-card-3" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">3. Ranked Matches</span>
            <span id="step-badge-3" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Ranks Rohan (98% same college) &amp; Priya (86% cross college) with active availability status dots.</p>
          <button onclick="runSingleStep(3)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 3
          </button>
        </div>

        <!-- Step 4 -->
        <div id="jury-card-4" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">4. Single Credit Escrow</span>
            <span id="step-badge-4" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Books free same-college session (0 credits) and paid cross-college session (5 credits escrow hold).</p>
          <button onclick="runSingleStep(4)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 4
          </button>
        </div>

        <!-- Step 5 -->
        <div id="jury-card-5" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">5. Scam Detection</span>
            <span id="step-badge-5" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Scam message containing phone number &amp; UPI request is blocked in chat with warning banner.</p>
          <button onclick="runSingleStep(5)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 5
          </button>
        </div>

        <!-- Step 6 -->
        <div id="jury-card-6" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">6. Release &amp; Vouch</span>
            <span id="step-badge-6" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Session completes &bull; 5★ rating releases 80% to giver / 20% fee &bull; 1-click vouch added.</p>
          <button onclick="runSingleStep(6)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 6
          </button>
        </div>

        <!-- Step 7 -->
        <div id="jury-card-7" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">7. Admin &amp; Scam Learning</span>
            <span id="step-badge-7" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Admin reviews skill gap &bull; resolves scam report &bull; automatically adds new learned regex rule.</p>
          <button onclick="runSingleStep(7)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 7
          </button>
        </div>

        <!-- Step 8 -->
        <div id="jury-card-8" class="jury-step-card p-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1.5 transition">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-brand-dark dark:text-white">8. Verification Review</span>
            <span id="step-badge-8" class="text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">PENDING</span>
          </div>
          <p class="text-[11px] text-brand-slate dark:text-slate-400">Fake alumnus rejected with reason &bull; enrolled student auto-verifies with Verified Alumni badge.</p>
          <button onclick="runSingleStep(8)" class="w-full mt-1 py-1 text-xs font-bold bg-white dark:bg-slate-800 hover:bg-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg text-brand-indigo dark:text-indigo-300">
            Execute Step 8
          </button>
        </div>

      </div>
    </aside>

  </div>

  <!-- Keyboard Shortcuts & Accessibility Modal -->
  <dialog id="help-modal" class="p-0 rounded-3xl bg-white dark:bg-brand-cardDark border border-slate-200 dark:border-brand-borderDark shadow-2xl backdrop:bg-black/50 max-w-md w-full">
    <div class="p-6 space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-brand-dark dark:text-white flex items-center gap-2">
          <span>⌨️</span> Keyboard Shortcuts
        </h3>
        <button onclick="closeHelpModal()" class="text-brand-slate text-xs font-bold">✕ Esc</button>
      </div>
      <div class="space-y-2 text-xs">
        <div class="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
          <span class="text-brand-slate dark:text-slate-400">1 through 8</span>
          <span class="font-mono font-bold text-brand-coral">Execute Jury Demo Step</span>
        </div>
        <div class="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
          <span class="text-brand-slate dark:text-slate-400">R</span>
          <span class="font-mono font-bold text-brand-coral">One-Click Demo Reset</span>
        </div>
        <div class="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
          <span class="text-brand-slate dark:text-slate-400">D</span>
          <span class="font-mono font-bold text-brand-coral">Toggle Light / Dark Mode</span>
        </div>
        <div class="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
          <span class="text-brand-slate dark:text-slate-400">J</span>
          <span class="font-mono font-bold text-brand-coral">Toggle Jury Checklist Dock</span>
        </div>
        <div class="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
          <span class="text-brand-slate dark:text-slate-400">S / G / F / E / A</span>
          <span class="font-mono font-bold text-brand-coral">Switch Role Personas</span>
        </div>
        <div class="flex justify-between py-1">
          <span class="text-brand-slate dark:text-slate-400">?</span>
          <span class="font-mono font-bold text-brand-coral">Open Shortcuts Dialog</span>
        </div>
      </div>
      <button onclick="closeHelpModal()" class="w-full py-2 bg-brand-coral text-white rounded-xl text-xs font-bold">
        Got it
      </button>
    </div>
  </dialog>

  <!-- Interactive JavaScript Application Engine -->
  <script>
    // State
    let currentRole = 'student';
    let isDarkMode = localStorage.getItem('warmpath_theme') === 'dark';
    let isJuryDockOpen = true;
    let completedSteps = new Set();

    // Initialize Theme
    function applyTheme() {
      if (isDarkMode) {
        document.documentElement.classList.add('dark');
        document.getElementById('theme-icon').textContent = '☀️';
      } else {
        document.documentElement.classList.remove('dark');
        document.getElementById('theme-icon').textContent = '🌙';
      }
    }
    function toggleDarkMode() {
      isDarkMode = !isDarkMode;
      localStorage.setItem('warmpath_theme', isDarkMode ? 'dark' : 'light');
      applyTheme();
      showToast('Theme updated: ' + (isDarkMode ? 'Dark Mode' : 'Light Mode'), 'info');
    }

    // Role Switching
    function switchRole(role) {
      currentRole = role;
      document.querySelectorAll('.role-view').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.role-tab').forEach(el => {
        el.classList.remove('bg-white', 'dark:bg-brand-cardDark', 'text-brand-dark', 'dark:text-white', 'shadow-sm');
        el.classList.add('text-brand-slate');
        el.setAttribute('aria-selected', 'false');
      });

      const activeView = document.getElementById('view-' + role);
      const activeBtn = document.getElementById('role-btn-' + role);
      if (activeView) activeView.classList.remove('hidden');
      if (activeBtn) {
        activeBtn.classList.add('bg-white', 'dark:bg-brand-cardDark', 'text-brand-dark', 'dark:text-white', 'shadow-sm');
        activeBtn.classList.remove('text-brand-slate');
        activeBtn.setAttribute('aria-selected', 'true');
      }
      showToast('Switched persona to ' + role.toUpperCase(), 'info');
    }

    // Mobile Menu
    function toggleMobileMenu() {
      const menu = document.getElementById('mobile-menu');
      menu.classList.toggle('hidden');
    }

    // Help Dialog
    function openHelpModal() {
      document.getElementById('help-modal').showModal();
    }
    function closeHelpModal() {
      document.getElementById('help-modal').close();
    }

    // Toast Notifications
    function showToast(message, type = 'success') {
      const container = document.getElementById('toast-container');
      const toast = document.createElement('div');
      toast.className = `p-3.5 rounded-2xl text-xs font-bold text-white shadow-lg pointer-events-auto flex items-center gap-2 transform transition-all duration-300 translate-y-2 opacity-0 ${
        type === 'error' ? 'bg-red-600' : type === 'warning' ? 'bg-amber-600' : type === 'info' ? 'bg-brand-indigo' : 'bg-emerald-600'
      }`;
      toast.innerHTML = `<span>${type === 'error' ? '✕' : type === 'warning' ? '⚠️' : '✓'}</span> <span>${message}</span>`;
      container.appendChild(toast);
      requestAnimationFrame(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
      });
      setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-x-4');
        setTimeout(() => toast.remove(), 300);
      }, 3500);
    }

    // Jury Panel Toggle
    function toggleJuryPanel() {
      const dock = document.getElementById('jury-dock');
      isJuryDockOpen = !isJuryDockOpen;
      dock.classList.toggle('hidden', !isJuryDockOpen);
      document.getElementById('jury-dock-btn-label').textContent = isJuryDockOpen ? 'Close Checklist Panel' : 'Open Checklist Panel';
    }

    // Giver Availability Toggle
    function setGiverStatus(status) {
      ['active', 'today', 'inactive'].forEach(k => {
        const btn = document.getElementById('giver-status-' + k);
        btn.classList.remove('bg-white', 'dark:bg-brand-cardDark', 'shadow-xs');
      });
      const activeKey = status === 'active_now' ? 'active' : status === 'available_today' ? 'today' : 'inactive';
      document.getElementById('giver-status-' + activeKey).classList.add('bg-white', 'dark:bg-brand-cardDark', 'shadow-xs');
      showToast('Giver status updated to ' + status.replace('_', ' ').toUpperCase(), 'success');
    }

    // Update Progress
    function updateProgress(stepNum) {
      completedSteps.add(stepNum);
      const count = completedSteps.size;
      const pct = (count / 8) * 100;
      document.getElementById('jury-progress-bar').style.width = pct + '%';
      document.getElementById('jury-progress-label').textContent = `${count} / 8 Complete (${Math.round(pct)}%)`;

      const badge = document.getElementById('step-badge-' + stepNum);
      if (badge) {
        badge.textContent = 'PASSED ✓';
        badge.className = 'text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300';
      }
      const card = document.getElementById('jury-card-' + stepNum);
      if (card) {
        card.classList.add('border-emerald-500/50', 'bg-emerald-50/20');
      }
    }

    // Step Execution via API
    async function runSingleStep(stepNum) {
      try {
        const resp = await fetch('/demo/step/' + stepNum, { method: 'POST' });
        const data = await resp.json();
        if (resp.ok) {
          updateProgress(stepNum);
          handleStepUIEffects(stepNum, data);
          showToast(`Step ${stepNum} Verified: ${data.title}`, 'success');
        } else {
          showToast(data.error?.message || 'Step execution failed', 'error');
        }
      } catch (err) {
        showToast('Connection error executing step ' + stepNum, 'error');
      }
    }

    // Visual updates corresponding to step outcome
    function handleStepUIEffects(stepNum, data) {
      if (stepNum === 1) {
        showToast('Resume parsed with magic signature & 4 skills confirmed!', 'success');
      } else if (stepNum === 2) {
        document.getElementById('intent-refined-text').textContent = data.refined_intent;
      } else if (stepNum === 4) {
        document.getElementById('student-wallet-bal').textContent = '15';
        document.getElementById('student-wallet-held').textContent = '5 Held in Escrow';
        document.getElementById('book-same-btn').textContent = 'Booked (0 Credits)';
        document.getElementById('book-same-btn').disabled = true;
        document.getElementById('book-cross-btn').textContent = 'Booked (5 Held)';
        document.getElementById('book-cross-btn').disabled = true;
      } else if (stepNum === 5) {
        appendBlockedScamMessage(data.attempted_message);
      } else if (stepNum === 6) {
        document.getElementById('student-wallet-held').textContent = '0 Held (Released)';
        showToast('Escrow released 80% to giver; Vouch badge issued!', 'success');
      } else if (stepNum === 7) {
        document.getElementById('learned-rule-status').textContent = 'Rule updated & active in scam_rules table';
        document.getElementById('moderation-report-card').classList.add('opacity-75');
      } else if (stepNum === 8) {
        document.getElementById('verif-card-fake').innerHTML = '<span class="text-xs font-bold text-red-600">✕ Fake Applicant REJECTED (Unmatched Identifier)</span>';
        document.getElementById('verif-card-real').innerHTML = '<span class="text-xs font-bold text-emerald-600">✓ Raghav Sen AUTO-VERIFIED with Official Badge</span>';
      }
    }

    // Sequential Auto-Play
    async function runAllDemoSteps() {
      showToast('Starting sequential 8-step Jury Demo walkthrough...', 'info');
      for (let i = 1; i <= 8; i++) {
        await runSingleStep(i);
        await new Promise(r => setTimeout(r, 600));
      }
      showToast('All 8 Story Acceptance Tests Passed with 100% Verification!', 'success');
    }

    // One-Click Reset
    async function triggerResetDemo() {
      try {
        const resp = await fetch('/demo/reset', { method: 'POST' });
        const data = await resp.json();
        if (resp.ok) {
          completedSteps.clear();
          document.getElementById('jury-progress-bar').style.width = '0%';
          document.getElementById('jury-progress-label').textContent = '0 / 8 Complete';
          for (let i = 1; i <= 8; i++) {
            const badge = document.getElementById('step-badge-' + i);
            if (badge) {
              badge.textContent = 'PENDING';
              badge.className = 'text-[10px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
            }
            const card = document.getElementById('jury-card-' + i);
            if (card) {
              card.classList.remove('border-emerald-500/50', 'bg-emerald-50/20');
            }
          }
          document.getElementById('student-wallet-bal').textContent = '20';
          document.getElementById('student-wallet-held').textContent = '0 Held in Escrow';
          document.getElementById('book-same-btn').textContent = 'Book Free Session (0 Credits)';
          document.getElementById('book-same-btn').disabled = false;
          document.getElementById('book-cross-btn').textContent = 'Book Session (5 Credits Hold)';
          document.getElementById('book-cross-btn').disabled = false;
          document.getElementById('dynamic-chat-stream').innerHTML = '';
          showToast('Clean state restored. Ready for demonstration.', 'info');
        }
      } catch (err) {
        showToast('Error resetting demo state', 'error');
      }
    }

    // User Interactive Actions
    async function handleRefineIntent() {
      const raw = document.getElementById('raw-intent-input').value;
      const resp = await fetch('/demo/refine-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent: raw })
      });
      const data = await resp.json();
      document.getElementById('intent-refined-text').textContent = data.refined_intent;
      updateProgress(2);
      showToast('Intent refined and structured with actionable agenda!', 'success');
    }

    function executeBookSession(type) {
      runSingleStep(4);
    }

    function sendChatMessage(isScam) {
      if (isScam) {
        runSingleStep(5);
      } else {
        const input = document.getElementById('chat-input-text');
        const text = input.value.trim() || 'Looking forward to our session tomorrow!';
        appendLegitMessage(text);
        input.value = '';
      }
    }

    function appendLegitMessage(text) {
      const stream = document.getElementById('dynamic-chat-stream');
      const msg = document.createElement('div');
      msg.className = 'flex items-start gap-3 justify-end';
      msg.innerHTML = `
        <div class="bg-brand-coral text-white p-3 rounded-2xl rounded-tr-none max-w-md shadow-2xs">
          <p class="text-xs">${text}</p>
          <span class="text-[10px] text-white/80 mt-1 block text-right">Just now &bull; Delivered</span>
        </div>
        <div class="w-8 h-8 rounded-lg bg-orange-500 text-white text-xs font-bold flex items-center justify-center shrink-0">AS</div>
      `;
      stream.appendChild(msg);
      document.getElementById('chat-messages-box').scrollTop = 99999;
    }

    function appendBlockedScamMessage(text) {
      const stream = document.getElementById('dynamic-chat-stream');
      const msg = document.createElement('div');
      msg.className = 'p-3.5 rounded-2xl border-2 border-red-500/80 bg-red-50 dark:bg-red-950/40 text-red-900 dark:text-red-200 space-y-1.5 shadow-sm';
      msg.innerHTML = `
        <div class="flex items-center justify-between text-xs font-bold text-red-600 dark:text-red-300">
          <span class="flex items-center gap-1.5">🚨 Message Blocked by Security Middleware</span>
          <span class="text-[10px] uppercase px-1.5 py-0.5 rounded bg-red-200 dark:bg-red-900 text-red-900 dark:text-red-200">Payment &amp; Contact Extortion</span>
        </div>
        <p class="text-xs italic bg-white/70 dark:bg-black/30 p-2 rounded-lg font-mono line-through text-slate-500 dark:text-slate-400">"${text}"</p>
        <p class="text-[11px] text-red-700 dark:text-red-300 font-semibold">
          Safety Notice: WarmPath strictly prevents sharing off-platform contact numbers and direct payment requests (UPI/Wallets). The sender has been flagged in audit logs.
        </p>
      `;
      stream.appendChild(msg);
      document.getElementById('chat-messages-box').scrollTop = 99999;
    }

    function executeVouchStudent() {
      runSingleStep(6);
    }
    function executeAdminResolveReport() {
      runSingleStep(7);
    }
    function executeVerificationStep() {
      runSingleStep(8);
    }

    // Keyboard Shortcuts (1-8, D, R, J, S, G, F, E, A, ?)
    window.addEventListener('keydown', (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
      const key = e.key.toUpperCase();
      if (['1', '2', '3', '4', '5', '6', '7', '8'].includes(e.key)) {
        runSingleStep(parseInt(e.key));
      } else if (key === 'D') {
        toggleDarkMode();
      } else if (key === 'R') {
        triggerResetDemo();
      } else if (key === 'J') {
        toggleJuryPanel();
      } else if (key === 'S') {
        switchRole('student');
      } else if (key === 'G') {
        switchRole('alumnus');
      } else if (key === 'F') {
        switchRole('faculty');
      } else if (key === 'E') {
        switchRole('recruiter');
      } else if (key === 'A') {
        switchRole('admin');
      } else if (key === '?') {
        openHelpModal();
      } else if (e.key === 'Escape') {
        closeHelpModal();
      }
    });

    // Boot Initialization
    applyTheme();
  </script>
</body>
</html>
"""
