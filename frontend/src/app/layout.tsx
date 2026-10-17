import type { Metadata } from "next";
import "./globals.css";
import NotificationCenter from "@/components/NotificationCenter";
import DemoSwitcher from "@/components/DemoSwitcher";
import Link from "next/link";

export const metadata: Metadata = {
  title: "WarmPath | Trust first, networking second",
  description:
    "A closed, institution-verified alumni network. Building a Network, Not a Directory.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 min-h-screen flex flex-col font-sans antialiased">
        {/* Top Navigation */}
        <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            {/* Logo & Tagline */}
            <div className="flex items-center space-x-3">
              <Link href="/" className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-teal-600 to-teal-500 flex items-center justify-center text-white font-bold shadow-md">
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2.2"
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </div>
                <div>
                  <span className="font-extrabold text-lg text-slate-900 tracking-tight flex items-center gap-1.5">
                    WarmPath
                    <span className="text-[10px] font-semibold bg-teal-50 text-teal-700 border border-teal-200 px-1.5 py-0.5 rounded-full">
                      IIIT-D Verified
                    </span>
                  </span>
                  <p className="text-[10px] text-slate-500 hidden sm:block">
                    Trust first, networking second.
                  </p>
                </div>
              </Link>
            </div>

            {/* Quick Links & Actions */}
            <div className="flex items-center space-x-4">
              <nav className="hidden md:flex items-center space-x-6 text-sm font-medium text-slate-600">
                <Link href="/" className="hover:text-teal-600 transition-colors">
                  Overview
                </Link>
                <Link
                  href="/dashboard/student"
                  className="hover:text-teal-600 transition-colors"
                >
                  My Portal
                </Link>
              </nav>

              <div className="flex items-center space-x-3 border-l border-slate-200 pl-4">
                <NotificationCenter />
                <Link
                  href="/login"
                  className="text-xs font-semibold text-slate-700 hover:text-teal-600 px-3 py-1.5 rounded-lg border border-slate-300 hover:border-teal-500 transition-all"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content View with padding for bottom demo switcher */}
        <main className="flex-1 pb-24">{children}</main>

        {/* Persistent Hackathon Demo Switcher */}
        <DemoSwitcher />
      </body>
    </html>
  );
}
