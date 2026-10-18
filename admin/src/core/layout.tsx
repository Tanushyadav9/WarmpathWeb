import React, { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  ShieldCheck,
  UserCheck,
  LayoutDashboard,
  Ticket,
  Sun,
  Moon,
  Menu,
  X,
  HelpCircle,
  Scale,
} from 'lucide-react';
import { JuryDemoPanel } from './jury_demo';

export const AdminLayout: React.FC = () => {
  const location = useLocation();
  const [isDark, setIsDark] = useState<boolean>(() => localStorage.getItem('warmpath_theme') === 'dark');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [isJuryOpen, setIsJuryOpen] = useState<boolean>(true);
  const [isHelpOpen, setIsHelpOpen] = useState<boolean>(false);
  const [currentRole, setCurrentRole] = useState<string>('admin');

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('warmpath_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('warmpath_theme', 'light');
    }
  }, [isDark]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) return;
      if (e.key === '?') {
        setIsHelpOpen((prev) => !prev);
      } else if (e.key.toLowerCase() === 'd') {
        setIsDark((prev) => !prev);
      } else if (e.key.toLowerCase() === 'j') {
        setIsJuryOpen((prev) => !prev);
      } else if (e.key === 'Escape') {
        setIsHelpOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const navItems = [
    { label: 'Dashboard & Analytics', path: '/', icon: LayoutDashboard },
    { label: 'Moderation & Safety', path: '/moderation', icon: ShieldCheck },
    { label: 'Verification Queue', path: '/verification', icon: UserCheck },
    { label: 'Seats & Grants', path: '/seats', icon: Ticket },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-brand-surface dark:bg-brand-bgDark font-sans text-brand-dark dark:text-slate-100 transition-colors duration-200">
      {/* Skip to Main Content Link for A11y */}
      <a
        href="#main-admin-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-brand-coral focus:text-white focus:rounded-xl focus:shadow-lg focus:outline-none"
      >
        Skip to main content
      </a>

      {/* Top Banner with Jury Mode Trigger */}
      <aside aria-label="Demo notice" className="bg-gradient-to-r from-brand-indigo via-indigo-900 to-brand-dark text-white text-xs px-4 py-2 border-b border-indigo-950 flex flex-wrap items-center justify-between gap-2 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-brand-coral text-white tracking-wide uppercase">
            Jury Demo Mode
          </span>
          <span className="font-medium text-slate-200">
            8-Step Story Walkthrough &bull; Anti-Gaming &bull; Proof-of-Work Verification
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsJuryOpen((prev) => !prev)}
            className="px-2.5 py-1 bg-brand-coral hover:bg-orange-600 rounded-lg font-bold text-white transition flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-white"
          >
            <Scale className="w-3.5 h-3.5" />
            <span>{isJuryOpen ? 'Close Checklist Dock' : 'Open Checklist Dock'}</span>
          </button>
        </div>
      </aside>

      {/* App Shell Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Desktop Sidebar */}
        <aside className="w-64 bg-brand-dark dark:bg-brand-cardDark text-white flex-col shrink-0 hidden md:flex border-r border-slate-200 dark:border-brand-borderDark transition-colors">
          <div className="p-6 border-b border-white/10 dark:border-slate-800">
            <h1 className="text-xl font-bold tracking-tight text-brand-coral">WarmPath</h1>
            <p className="text-xs text-brand-slate">Institutional Portal &bull; IIIT Delhi</p>
          </div>

          {/* Role Persona Switcher in Sidebar */}
          <div className="p-4 border-b border-white/10 dark:border-slate-800">
            <label htmlFor="role-select" className="text-[10px] font-bold uppercase tracking-wider text-brand-slate block mb-1">
              Active Persona
            </label>
            <select
              id="role-select"
              value={currentRole}
              onChange={(e) => setCurrentRole(e.target.value)}
              className="w-full text-xs bg-slate-800/80 text-white rounded-xl px-3 py-2 border border-slate-700 focus:outline-none focus:border-brand-coral"
            >
              <option value="admin">🛡️ Institution Admin</option>
              <option value="student">🎓 Student (Aditi Sharma)</option>
              <option value="alumnus">💼 Alumni / Giver (Rohan)</option>
              <option value="faculty">🏛️ Faculty (Dr. Vivek)</option>
              <option value="recruiter">👔 Recruiter (Zomato)</option>
            </select>
          </div>

          <nav aria-label="Admin Navigation" className="flex-1 p-4 space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-brand-coral ${
                    active
                      ? 'bg-brand-indigo text-white shadow-sm'
                      : 'text-brand-slate hover:text-white hover:bg-brand-indigo/40'
                  }`}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Bottom Bar Controls */}
          <div className="p-4 border-t border-white/10 dark:border-slate-800 flex items-center justify-between">
            <button
              onClick={() => setIsDark((prev) => !prev)}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition focus:outline-none focus:ring-2 focus:ring-brand-coral"
              title="Toggle theme (Hotkey: D)"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-300" />}
            </button>
            <button
              onClick={() => setIsHelpOpen(true)}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition focus:outline-none focus:ring-2 focus:ring-brand-coral"
              title="Keyboard shortcuts (Hotkey: ?)"
              aria-label="Keyboard shortcuts"
            >
              <HelpCircle className="w-4 h-4 text-slate-300" />
            </button>
          </div>
        </aside>

        {/* Mobile Header */}
        <div className="md:hidden flex flex-col w-full">
          <header className="p-4 bg-white dark:bg-brand-cardDark border-b border-slate-200 dark:border-brand-borderDark flex items-center justify-between">
            <h1 className="text-lg font-bold text-brand-coral">WarmPath</h1>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsDark((prev) => !prev)}
                className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-brand-dark dark:text-white"
              >
                {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setIsMobileMenuOpen((prev) => !prev)}
                className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-brand-dark dark:text-white"
              >
                {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </button>
            </div>
          </header>

          {isMobileMenuOpen && (
            <nav className="p-4 bg-white dark:bg-brand-cardDark border-b border-slate-200 dark:border-brand-borderDark space-y-2">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </Link>
              ))}
            </nav>
          )}
        </div>

        {/* Main Content View */}
        <main id="main-admin-content" className="flex-1 p-6 md:p-8 overflow-y-auto space-y-6">
          <Outlet />
        </main>

        {/* Jury Demo Dock Panel */}
        <JuryDemoPanel isOpen={isJuryOpen} onClose={() => setIsJuryOpen(false)} />
      </div>

      {/* Keyboard Shortcuts Dialog */}
      {isHelpOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
        >
          <div className="bg-white dark:bg-brand-cardDark border border-slate-200 dark:border-brand-borderDark rounded-3xl p-6 max-w-sm w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-brand-dark dark:text-white flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-brand-coral" />
                Keyboard Shortcuts
              </h3>
              <button onClick={() => setIsHelpOpen(false)} className="text-xs text-brand-slate font-bold">
                ✕ Esc
              </button>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-brand-slate">D</span>
                <span className="font-bold text-brand-coral">Toggle Dark / Light Mode</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-brand-slate">J</span>
                <span className="font-bold text-brand-coral">Toggle Jury Checklist Dock</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                <span className="text-brand-slate">1 through 8</span>
                <span className="font-bold text-brand-coral">Run Jury Demo Step</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-brand-slate">?</span>
                <span className="font-bold text-brand-coral">Open Shortcuts Help</span>
              </div>
            </div>
            <button
              onClick={() => setIsHelpOpen(false)}
              className="w-full py-2 bg-brand-coral hover:bg-orange-600 text-white rounded-xl text-xs font-bold transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
