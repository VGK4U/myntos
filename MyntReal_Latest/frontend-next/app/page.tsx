import React from "react";
import Link from "next/link";

export default function GlobalLandingPage() {
  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden font-sans bg-[#0f172a]" 
         style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)' }}>
      
      {/* Dynamic Background Effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-500 opacity-20 blur-[120px] pointer-events-none mix-blend-screen"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-500 opacity-20 blur-[120px] pointer-events-none mix-blend-screen"></div>
      
      {/* Legacy Sandbox Banner Replica */}
      <div className="bg-gradient-to-r from-indigo-600 to-pink-600 text-white text-center py-2 px-4 font-semibold shadow-md z-50 fixed top-0 w-full text-sm tracking-wide">
        <i className="fas fa-rocket mr-2"></i>
        VGK4U NEXT.JS PRODUCTION ENVIRONMENT
        <span className="ml-3 opacity-75 hidden sm:inline">(Enhanced Next.js Architecture)</span>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center text-center z-10 max-w-7xl mx-auto px-6 w-full mt-16 py-12">
        <div className="mb-12 animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl mb-6 shadow-2xl">
             <i className="fas fa-layer-group text-4xl text-white"></i>
          </div>
          <h1 className="text-4xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-blue-200 tracking-tight mb-4 drop-shadow-sm">
            VGK4U Central Portal
          </h1>
          <p className="text-lg md:text-xl text-blue-100/70 max-w-2xl mx-auto font-light">
            Select your destination portal below to access the MyntReal ecosystem. Secure, fast, and fully integrated.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8 w-full animate-in fade-in slide-in-from-bottom-12 duration-1000 delay-150">
          
          {/* Member Portal */}
          <Link href="/member/login" className="group block h-full">
            <div className="bg-white/5 hover:bg-white/10 backdrop-blur-lg border border-white/10 hover:border-white/30 rounded-3xl p-8 shadow-xl hover:shadow-2xl hover:shadow-emerald-500/20 transition-all duration-300 h-full flex flex-col items-center text-center transform hover:-translate-y-2 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <div className="w-20 h-20 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center text-3xl mb-6 group-hover:scale-110 group-hover:bg-emerald-500 group-hover:text-white transition-all duration-300 shadow-lg border border-emerald-500/30">
                <i className="fas fa-users"></i>
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">MNR Member</h2>
              <p className="text-blue-100/60 leading-relaxed text-sm">Access your MLM network, direct referrals, wallets, and EV scheme progress.</p>
            </div>
          </Link>

          {/* Vendor Portal */}
          <Link href="/vendor/login" className="group block h-full">
            <div className="bg-white/5 hover:bg-white/10 backdrop-blur-lg border border-white/10 hover:border-white/30 rounded-3xl p-8 shadow-xl hover:shadow-2xl hover:shadow-amber-500/20 transition-all duration-300 h-full flex flex-col items-center text-center transform hover:-translate-y-2 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <div className="w-20 h-20 bg-amber-500/20 text-amber-400 rounded-full flex items-center justify-center text-3xl mb-6 group-hover:scale-110 group-hover:bg-amber-500 group-hover:text-white transition-all duration-300 shadow-lg border border-amber-500/30">
                <i className="fas fa-handshake"></i>
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Partner / Vendor</h2>
              <p className="text-blue-100/60 leading-relaxed text-sm">Scan member coupons, track daily sales, and view VGK settlement ledgers.</p>
            </div>
          </Link>

          {/* Staff Portal */}
          <Link href="/staff/login" className="group block h-full">
            <div className="bg-white/5 hover:bg-white/10 backdrop-blur-lg border border-white/10 hover:border-white/30 rounded-3xl p-8 shadow-xl hover:shadow-2xl hover:shadow-blue-500/20 transition-all duration-300 h-full flex flex-col items-center text-center transform hover:-translate-y-2 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <div className="w-20 h-20 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center text-3xl mb-6 group-hover:scale-110 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300 shadow-lg border border-blue-500/30">
                <i className="fas fa-user-tie"></i>
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Staff & Ops</h2>
              <p className="text-blue-100/60 leading-relaxed text-sm">Manage tasks, leads, HR, support tickets, and VGK Network administration.</p>
            </div>
          </Link>

          {/* Super Admin */}
          <Link href="/superadmin/login" className="group block h-full">
            <div className="bg-white/5 hover:bg-white/10 backdrop-blur-lg border border-white/10 hover:border-white/30 rounded-3xl p-8 shadow-xl hover:shadow-2xl hover:shadow-rose-500/20 transition-all duration-300 h-full flex flex-col items-center text-center transform hover:-translate-y-2 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <div className="w-20 h-20 bg-rose-500/20 text-rose-400 rounded-full flex items-center justify-center text-3xl mb-6 group-hover:scale-110 group-hover:bg-rose-500 group-hover:text-white transition-all duration-300 shadow-lg border border-rose-500/30">
                <i className="fas fa-shield-alt"></i>
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Super Admin</h2>
              <p className="text-blue-100/60 leading-relaxed text-sm">Supreme Finance, global configuration, and root-level system management.</p>
            </div>
          </Link>

        </div>
        
        <div className="mt-16 text-center text-sm text-blue-200/40 font-medium">
          <p>&copy; {new Date().getFullYear()} VGK Network (MyntReal). All Rights Reserved.</p>
          <p className="mt-1 flex items-center justify-center gap-2">
            <i className="fas fa-check-circle text-emerald-400/50"></i> System Architecture v2.0
          </p>
        </div>
      </div>
    </div>
  );
}
