"use client";

import Link from "next/link";

export default function HubLandingPage() {
  return (
    <div className="min-h-screen bg-gray-50 font-sans selection:bg-brand-warning/30 selection:text-brand-warning">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 h-20 bg-white/90 backdrop-blur-md border-b border-gray-200 z-50 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-warning rounded text-white flex items-center justify-center font-bold shadow-sm">
              M
            </div>
            <span className="text-xl font-bold text-gray-900 tracking-tight">MyntReal</span>
          </div>
          
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm font-medium text-gray-600 hover:text-brand-warning transition-colors">Features</a>
            <a href="#solutions" className="text-sm font-medium text-gray-600 hover:text-brand-warning transition-colors">Solutions</a>
            <a href="#resources" className="text-sm font-medium text-gray-600 hover:text-brand-warning transition-colors">Resources</a>
          </div>

          <div className="flex items-center gap-4">
            <Link 
              href="/portals"
              className="text-sm font-bold text-gray-900 hover:text-brand-warning transition-colors hidden sm:block"
            >
              Sign In
            </Link>
            <Link 
              href="/signup"
              className="text-sm font-bold bg-gray-900 text-white px-5 py-2.5 rounded-lg hover:bg-brand-warning transition-colors shadow-sm hover:shadow"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight leading-tight mb-6">
            The Enterprise Platform for <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-warning to-amber-500">Real Estate Operations</span>
          </h1>
          <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto leading-relaxed">
            Unify your field operations, manage multi-tier member networks, and process complex financial payouts with our enterprise-grade CRM and ERP solution.
          </p>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
            <Link 
              href="/portals"
              className="w-full sm:w-auto px-8 py-4 bg-brand-warning text-white text-lg font-bold rounded-lg hover:bg-amber-600 transition-all shadow-md hover:shadow-xl hover:-translate-y-0.5"
            >
              Access Portal <i className="fas fa-arrow-right ml-2"></i>
            </Link>
            <a 
              href="#features"
              className="w-full sm:w-auto px-8 py-4 bg-white text-gray-900 border border-gray-200 text-lg font-bold rounded-lg hover:bg-gray-50 transition-all shadow-sm"
            >
              Explore Features
            </a>
          </div>
        </div>
      </section>

      {/* Dashboard Preview / Mockup */}
      <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pb-24">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-2xl shadow-gray-200/50 overflow-hidden relative">
          {/* Mac window header */}
          <div className="h-12 bg-gray-50 border-b border-gray-200 flex items-center px-4 gap-2">
            <div className="w-3 h-3 rounded-full bg-rose-400"></div>
            <div className="w-3 h-3 rounded-full bg-amber-400"></div>
            <div className="w-3 h-3 rounded-full bg-emerald-400"></div>
          </div>
          {/* Fake Dashboard Body */}
          <div className="h-[400px] md:h-[600px] bg-gray-50/50 p-8 flex items-center justify-center relative overflow-hidden">
             <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
             <div className="text-center z-10">
                <i className="fas fa-chart-network text-6xl text-gray-300 mb-4"></i>
                <p className="text-gray-500 font-medium text-lg">MyntReal Enterprise Hub</p>
             </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-sm font-bold text-brand-warning uppercase tracking-widest mb-2">Platform Capabilities</h2>
            <h3 className="text-3xl font-extrabold text-gray-900">Everything you need to scale operations</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard 
              icon="fas fa-sitemap"
              title="Multi-Tier Hierarchy"
              description="Manage complex MLM structures, direct facilitations, and matching networks with infinite depth."
            />
            <FeatureCard 
              icon="fas fa-money-check-alt"
              title="Automated Financials"
              description="Calculate real-time earnings, process wallets, and generate comprehensive statements instantly."
            />
            <FeatureCard 
              icon="fas fa-car"
              title="Field Allowances"
              description="Track eligibility for Standard and Car allowances based on rolling multi-month performance."
            />
            <FeatureCard 
              icon="fas fa-trophy"
              title="Awards & Bonanza"
              description="Run time-bound bonanza campaigns and automatically evaluate team performance for physical awards."
            />
            <FeatureCard 
              icon="fas fa-chart-pie"
              title="Real-Time Analytics"
              description="Executive dashboards providing macro-level insights into company revenue vs. payouts."
            />
            <FeatureCard 
              icon="fas fa-shield-alt"
              title="Enterprise Security"
              description="Role-based access control ensuring HR, Accounts, and Support staff only see what they need."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 py-12 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-brand-warning rounded text-white flex items-center justify-center font-bold text-xs">
              M
            </div>
            <span className="text-lg font-bold text-white tracking-tight">MyntReal</span>
          </div>
          <p className="text-gray-400 text-sm">
            &copy; {new Date().getFullYear()} MyntReal CRM. All rights reserved.
          </p>
          <div className="flex gap-4 text-gray-400">
            <a href="#" className="hover:text-white transition-colors"><i className="fab fa-twitter"></i></a>
            <a href="#" className="hover:text-white transition-colors"><i className="fab fa-linkedin"></i></a>
            <a href="#" className="hover:text-white transition-colors"><i className="fab fa-github"></i></a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: string, title: string, description: string }) {
  return (
    <div className="p-8 rounded-2xl border border-gray-100 bg-gray-50 hover:bg-white hover:border-gray-200 hover:shadow-lg transition-all group">
      <div className="w-12 h-12 rounded-xl bg-white border border-gray-200 flex items-center justify-center text-gray-600 mb-6 group-hover:text-brand-warning group-hover:scale-110 transition-transform shadow-sm">
        <i className={`${icon} text-xl`}></i>
      </div>
      <h4 className="text-lg font-bold text-gray-900 mb-3">{title}</h4>
      <p className="text-gray-600 leading-relaxed text-sm">
        {description}
      </p>
    </div>
  );
}
