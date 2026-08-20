import React from "react";
import Link from "next/link";
import Image from "next/image";

export default function VGK4ULandingPage() {
  return (
    <div className="min-h-screen flex flex-col font-sans bg-slate-50 overflow-x-hidden selection:bg-indigo-500 selection:text-white">
      
      {/* 1. Global Navigation Bar */}
      <nav className="fixed w-full z-50 bg-white/80 backdrop-blur-lg border-b border-gray-200 transition-all duration-300">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            {/* Logo Area */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-tr from-indigo-600 to-blue-500 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <span className="text-white font-bold text-xl tracking-tighter">V</span>
              </div>
              <div className="flex flex-col">
                <span className="font-extrabold text-xl tracking-tight text-slate-900 leading-none">VGK Network</span>
                <span className="text-[10px] uppercase font-bold tracking-widest text-indigo-600 mt-0.5">MyntReal Architecture</span>
              </div>
            </div>
            
            {/* Desktop Navigation Links */}
            <div className="hidden md:flex items-center space-x-8">
              <a href="#ecosystem" className="text-sm font-semibold text-slate-600 hover:text-indigo-600 transition-colors">Ecosystem</a>
              <a href="#features" className="text-sm font-semibold text-slate-600 hover:text-indigo-600 transition-colors">Enterprise Features</a>
              <a href="#security" className="text-sm font-semibold text-slate-600 hover:text-indigo-600 transition-colors">Security</a>
            </div>

            {/* Auth Actions */}
            <div className="flex items-center gap-4">
              <Link href="/member/login" className="hidden sm:block text-sm font-semibold text-slate-700 hover:text-indigo-600 transition-colors">
                Member Login
              </Link>
              <Link href="/staff/login" className="px-5 py-2.5 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-md shadow-indigo-600/20 transition-all transform hover:-translate-y-0.5 flex items-center gap-2">
                <i className="fas fa-lock text-xs"></i> Staff Portal
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* 2. Hero Section */}
      <main className="flex-1 pt-20">
        <div className="relative overflow-hidden bg-white">
          {/* Background Decorators */}
          <div className="absolute top-0 right-0 -mr-20 -mt-20 w-[500px] h-[500px] bg-indigo-50 rounded-full blur-3xl opacity-50 pointer-events-none"></div>
          <div className="absolute bottom-0 left-0 -ml-20 -mb-20 w-[400px] h-[400px] bg-blue-50 rounded-full blur-3xl opacity-50 pointer-events-none"></div>
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-32 relative z-10">
            <div className="text-center max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-50 border border-indigo-100 mb-8">
                <span className="flex h-2 w-2 rounded-full bg-indigo-600 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                </span>
                <span className="text-xs font-bold text-indigo-700 uppercase tracking-wider">Next.js Enterprise Upgrade V2.0</span>
              </div>
              
              <h1 className="text-5xl md:text-7xl font-black text-slate-900 tracking-tight leading-[1.1] mb-8">
                The Unified <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-500">MyntReal</span> Ecosystem
              </h1>
              
              <p className="text-lg md:text-xl text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed">
                A highly secure, hyper-performant central portal seamlessly connecting Members, Staff Operations, Vendors, and Executive Leadership.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <a href="#ecosystem" className="w-full sm:w-auto px-8 py-4 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl shadow-xl shadow-slate-900/20 transition-all flex items-center justify-center gap-3 group">
                  Explore Portals
                  <i className="fas fa-arrow-down text-sm group-hover:translate-y-1 transition-transform"></i>
                </a>
                <Link href="/member/login" className="w-full sm:w-auto px-8 py-4 bg-white border border-slate-200 hover:border-indigo-200 hover:bg-indigo-50 text-slate-700 hover:text-indigo-700 font-bold rounded-xl transition-all flex items-center justify-center gap-3">
                  <i className="fas fa-users text-sm"></i> Access Member Network
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* 3. The Portals (Ecosystem) Grid */}
        <div id="ecosystem" className="bg-slate-50 py-24 border-t border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl font-black text-slate-900 tracking-tight mb-4">Centralized Operations Hub</h2>
              <p className="text-slate-600 max-w-2xl mx-auto">Select your secure portal below. Each environment is strictly isolated with role-based JWT authentication and encrypted data transit.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
              {/* Member Portal */}
              <Link href="/member/login" className="group">
                <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm hover:shadow-xl hover:border-emerald-200 transition-all h-full flex flex-col relative overflow-hidden transform hover:-translate-y-1">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-50 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center text-2xl mb-6 relative z-10 shadow-inner">
                    <i className="fas fa-users"></i>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-3 relative z-10">MNR Member</h3>
                  <p className="text-slate-600 text-sm leading-relaxed mb-6 flex-1 relative z-10">Manage direct referrals, EV schemes, matching network, and daily earnings.</p>
                  <div className="mt-auto flex items-center text-sm font-bold text-emerald-600 relative z-10">
                    Secure Login <i className="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
                  </div>
                </div>
              </Link>

              {/* Staff Portal */}
              <Link href="/staff/login" className="group">
                <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm hover:shadow-xl hover:border-blue-200 transition-all h-full flex flex-col relative overflow-hidden transform hover:-translate-y-1">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-blue-50 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center text-2xl mb-6 relative z-10 shadow-inner">
                    <i className="fas fa-user-tie"></i>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-3 relative z-10">Staff & CRM Ops</h3>
                  <p className="text-slate-600 text-sm leading-relaxed mb-6 flex-1 relative z-10">Lead management, AI dialers, Finance ledgers, HR tracking, and general operations.</p>
                  <div className="mt-auto flex items-center text-sm font-bold text-blue-600 relative z-10">
                    Secure Login <i className="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
                  </div>
                </div>
              </Link>

              {/* Vendor Portal */}
              <Link href="/vendor/login" className="group">
                <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm hover:shadow-xl hover:border-amber-200 transition-all h-full flex flex-col relative overflow-hidden transform hover:-translate-y-1">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-2xl flex items-center justify-center text-2xl mb-6 relative z-10 shadow-inner">
                    <i className="fas fa-store"></i>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-3 relative z-10">Partner / Vendor</h3>
                  <p className="text-slate-600 text-sm leading-relaxed mb-6 flex-1 relative z-10">Scan coupons, process payments, and track settlements with the VGK Network.</p>
                  <div className="mt-auto flex items-center text-sm font-bold text-amber-600 relative z-10">
                    Secure Login <i className="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
                  </div>
                </div>
              </Link>

              {/* Super Admin Portal */}
              <Link href="/superadmin/login" className="group">
                <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm hover:shadow-xl hover:border-rose-200 transition-all h-full flex flex-col relative overflow-hidden transform hover:-translate-y-1">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-rose-50 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-16 h-16 bg-rose-100 text-rose-600 rounded-2xl flex items-center justify-center text-2xl mb-6 relative z-10 shadow-inner">
                    <i className="fas fa-shield-alt"></i>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-3 relative z-10">Super Admin</h3>
                  <p className="text-slate-600 text-sm leading-relaxed mb-6 flex-1 relative z-10">Root access, executive configuration, mass approvals, and master ledger tracking.</p>
                  <div className="mt-auto flex items-center text-sm font-bold text-rose-600 relative z-10">
                    Secure Login <i className="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
                  </div>
                </div>
              </Link>
            </div>
          </div>
        </div>

      </main>

      {/* 4. Global Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
            <div className="md:col-span-2">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold tracking-tighter">V</span>
                </div>
                <span className="font-bold text-lg text-white">VGK Network</span>
              </div>
              <p className="text-sm leading-relaxed max-w-sm mb-6">
                Powering the MyntReal network. A cutting-edge, secure, and fully scalable enterprise resource planning and MLM management architecture.
              </p>
              <div className="flex gap-4">
                <a href="#" className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center hover:bg-indigo-600 hover:text-white transition-colors">
                  <i className="fab fa-twitter"></i>
                </a>
                <a href="#" className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center hover:bg-indigo-600 hover:text-white transition-colors">
                  <i className="fab fa-linkedin-in"></i>
                </a>
              </div>
            </div>
            
            <div>
              <h4 className="text-white font-bold mb-4 uppercase tracking-wider text-xs">Portals</h4>
              <ul className="space-y-3 text-sm">
                <li><Link href="/member/login" className="hover:text-indigo-400 transition-colors">Member Dashboard</Link></li>
                <li><Link href="/staff/login" className="hover:text-indigo-400 transition-colors">Staff CRM</Link></li>
                <li><Link href="/vendor/login" className="hover:text-indigo-400 transition-colors">Partner Network</Link></li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-white font-bold mb-4 uppercase tracking-wider text-xs">System</h4>
              <ul className="space-y-3 text-sm">
                <li><a href="#" className="hover:text-indigo-400 transition-colors">Architecture Documentation</a></li>
                <li><a href="#" className="hover:text-indigo-400 transition-colors">API Status</a></li>
                <li><a href="#" className="hover:text-indigo-400 transition-colors">Security Policy</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-slate-800 pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-medium">
            <p>&copy; {new Date().getFullYear()} VGK Network (MyntReal). All Rights Reserved.</p>
            <div className="flex items-center gap-2 text-indigo-400 bg-indigo-400/10 px-3 py-1.5 rounded-full">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
              All Systems Operational — V2.0 Enterprise
            </div>
          </div>
        </div>
      </footer>

    </div>
  );
}
