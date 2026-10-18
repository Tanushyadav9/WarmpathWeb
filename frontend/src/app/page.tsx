import Link from "next/link";

export default function HomePage() {
  const roles = [
    {
      role: "student",
      title: "Student Portal",
      badge: "Seeker",
      desc: "Upload resume, state specific intent, get AI matches with 'Why this match' reasoning.",
      link: "/dashboard/student",
      bg: "bg-blue-50/70 border-blue-200 text-blue-900",
      cta: "Explore Mentors & Opportunities",
    },
    {
      role: "alumni",
      title: "Alumni Portal",
      badge: "Giver",
      desc: "Manage capacity caps, hold sessions, earn reputation badges and cross-college credits.",
      link: "/dashboard/alumni",
      bg: "bg-teal-50/70 border-teal-200 text-teal-900",
      cta: "Review Mentee Requests",
    },
    {
      role: "faculty",
      title: "Faculty Portal",
      badge: "Domain Mentor",
      desc: "Provide academic and research consultations with compensated hours and verified expertise.",
      link: "/dashboard/faculty",
      bg: "bg-indigo-50/70 border-indigo-200 text-indigo-900",
      cta: "View Academic Requests",
    },
    {
      role: "recruiter",
      title: "Recruiter Portal",
      badge: "Talent Partner",
      desc: "Post referrals and hiring chats with pre-screened, verified high-intent students.",
      link: "/dashboard/recruiter",
      bg: "bg-purple-50/70 border-purple-200 text-purple-900",
      cta: "View Matched Candidates",
    },
    {
      role: "founder",
      title: "Founder Portal",
      badge: "Venture Creator",
      desc: "Host founder office hours, discover entrepreneurial students, build core team pipelines.",
      link: "/dashboard/founder",
      bg: "bg-amber-50/70 border-amber-200 text-amber-900",
      cta: "Manage Startup Pipeline",
    },
    {
      role: "admin",
      title: "Institution Admin",
      badge: "Governor",
      desc: "Verify alumni, monitor fulfillment rates, audit skill gaps, and enforce safety standards.",
      link: "/dashboard/admin",
      bg: "bg-rose-50/70 border-rose-200 text-rose-900",
      cta: "Open Admin Console",
    },
  ];

  const trustLayers = [
    { num: 1, title: "Identity", desc: "College CSV list match + official email OTP + peer vouching fallback" },
    { num: 2, title: "Badges", desc: "Transparent verification levels: Pending, Verified Alumnus, Verified Professional, Trusted" },
    { num: 3, title: "Limits", desc: "Weekly giver capacity cap, monthly free-session cap, graduated trust score caps" },
    { num: 4, title: "In-App Comms", desc: "Built-in communication that shields personal phone numbers and emails" },
    { num: 5, title: "Scam Detection", desc: "Real-time detection flagging payment solicitations and off-platform links" },
    { num: 6, title: "Human Review", desc: "Institution moderation queue for dispute escalation, suspension, and appeals" },
    { num: 7, title: "Incident Learning", desc: "Resolved reports dynamically update scam rules and user trust scores" },
  ];

  return (
    <div className="space-y-16 py-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <section className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center space-x-2 bg-teal-50 border border-teal-200 text-teal-800 px-3.5 py-1.5 rounded-full text-xs font-semibold shadow-xs">
          <span>Official Pilot Target: IIIT Delhi & Peer Colleges</span>
          <span className="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
          <span className="text-teal-600">50 Verified Givers Active</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
          Building a Network,{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-teal-500">
            Not a Directory.
          </span>
        </h1>
        <p className="text-lg text-slate-600 leading-relaxed">
          A directory lists people; WarmPath recommends, connects, schedules, and measures.
          Anchored in institution-verified trust, intent-first asks, and protected communication.
        </p>
        <div className="pt-2 flex flex-wrap justify-center gap-4 text-xs font-medium text-slate-500">
          <span className="flex items-center gap-1.5 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs">
            <svg className="w-4 h-4 text-teal-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            Same-college connections ALWAYS free
          </span>
          <span className="flex items-center gap-1.5 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs">
            <svg className="w-4 h-4 text-teal-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            Escrow-protected credit economy
          </span>
          <span className="flex items-center gap-1.5 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs">
            <svg className="w-4 h-4 text-teal-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            No cold-spam (capacity capped)
          </span>
        </div>
      </section>

      {/* Role Dashboards Grid */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Role-Based Experiences</h2>
            <p className="text-xs text-slate-500">Each role views tailored data and adheres to strict verification permissions</p>
          </div>
          <span className="text-xs font-semibold text-teal-700 bg-teal-50 px-2.5 py-1 rounded-md border border-teal-200">
            6 Specialized Roles
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {roles.map((item) => (
            <div
              key={item.role}
              className={`rounded-2xl border p-6 flex flex-col justify-between transition-all duration-200 hover:shadow-md bg-white`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-base text-slate-900">{item.title}</h3>
                  <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${item.bg}`}>
                    {item.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">{item.desc}</p>
              </div>

              <div className="pt-6">
                <Link
                  href={item.link}
                  className="w-full inline-flex items-center justify-center text-xs font-semibold px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-teal-600 text-white transition-colors duration-150 shadow-xs"
                >
                  {item.cta} &rarr;
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Seven Trust Layers */}
      <section className="bg-slate-900 text-white rounded-3xl p-8 sm:p-10 shadow-xl space-y-8">
        <div className="max-w-2xl">
          <span className="text-xs font-bold uppercase tracking-wider text-teal-400">Security Architecture</span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight mt-1">
            The 7 Layers of Trust (F31)
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 mt-2">
            WarmPath replaces unverified social directory spam with a verifiable pipeline of institution proof, capacity gates, and incident containment.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {trustLayers.map((layer) => (
            <div
              key={layer.num}
              className="bg-slate-800/80 border border-slate-700/80 rounded-xl p-4 space-y-2 hover:border-teal-500/50 transition-colors"
            >
              <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-400 font-bold text-xs flex items-center justify-center border border-teal-500/30">
                0{layer.num}
              </div>
              <h4 className="font-semibold text-sm text-slate-100">{layer.title}</h4>
              <p className="text-xs text-slate-400 leading-normal">{layer.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
