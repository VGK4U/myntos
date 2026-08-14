import React from "react";
import Link from "next/link";
import Image from "next/image";

export default function GlobalLandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center relative overflow-hidden font-sans">
      
      {/* Background Decor */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-500 opacity-5 blur-[100px]"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-amber-500 opacity-5 blur-[100px]"></div>

      <div className="text-center z-10 max-w-4xl mx-auto px-6 w-full">
        <div className="mb-8 animate-fade-in-up">
          <div className="w-24 h-24 mx-auto bg-gradient-to-tr from-gray-900 to-gray-700 rounded-2xl flex items-center justify-center shadow-xl mb-6 border border-gray-600">
            <span className="text-4xl font-black text-white tracking-widest">VGK</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-black text-gray-900 tracking-tight mb-4">
            Welcome to the VGK Network
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            Select your destination portal below to access the MyntReal ecosystem.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          
          {/* Member Portal */}
          <Link href="/member/login" className="group">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:border-amber-400 hover:shadow-lg transition-all h-full flex flex-col items-center text-center relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-amber-100 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity -z-0"></div>
              <div className="w-16 h-16 bg-amber-50 text-amber-500 rounded-full flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform relative z-10">
                <i className="fas fa-users"></i>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2 relative z-10">Member Portal</h2>
              <p className="text-sm text-gray-500 relative z-10">Access your MLM network, direct referrals, wallets, and EV scheme progress.</p>
            </div>
          </Link>

          {/* Vendor Portal */}
          <Link href="/vendor/login" className="group">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:border-sky-400 hover:shadow-lg transition-all h-full flex flex-col items-center text-center relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-sky-100 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity -z-0"></div>
              <div className="w-16 h-16 bg-sky-50 text-sky-500 rounded-full flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform relative z-10">
                <i className="fas fa-store"></i>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2 relative z-10">Vendor Partner</h2>
              <p className="text-sm text-gray-500 relative z-10">Scan member coupons, track daily sales, and view VGK settlement ledgers.</p>
            </div>
          </Link>

          {/* Staff Portal */}
          <Link href="/staff/login" className="group">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:border-indigo-400 hover:shadow-lg transition-all h-full flex flex-col items-center text-center relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-100 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity -z-0"></div>
              <div className="w-16 h-16 bg-indigo-50 text-indigo-500 rounded-full flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform relative z-10">
                <i className="fas fa-user-tie"></i>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2 relative z-10">Staff & Ops</h2>
              <p className="text-sm text-gray-500 relative z-10">Manage tasks, leads, HR, support tickets, and VGK Network administration.</p>
            </div>
          </Link>

          {/* Super Admin */}
          <Link href="/superadmin/login" className="group">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 hover:border-red-400 hover:shadow-lg transition-all h-full flex flex-col items-center text-center relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-red-100 rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity -z-0"></div>
              <div className="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform relative z-10">
                <i className="fas fa-shield-alt"></i>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2 relative z-10">Super Admin</h2>
              <p className="text-sm text-gray-500 relative z-10">Supreme Finance, global configuration, and root-level system management.</p>
            </div>
          </Link>

        </div>
        
        <div className="mt-16 text-center text-sm text-gray-400 font-medium">
          <p>&copy; {new Date().getFullYear()} VGK Network (MyntReal). All Rights Reserved.</p>
          <p className="mt-1">System Architecture v2.0 - Next.js Front-End</p>
        </div>
      </div>
    </div>
  );
}
