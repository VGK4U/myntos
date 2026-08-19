"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MemberAuthProvider, useMemberAuth } from "@/contexts/MemberAuthContext";

function MemberSidebar() {
  const pathname = usePathname();
  const { user, logout } = useMemberAuth();
  
  const navItems = [
    { name: "Dashboard", href: "/member/dashboard", icon: "fas fa-home" },
    { name: "Income & Earnings", href: "/member/income", icon: "fas fa-rupee-sign" },
    { name: "My Wallet", href: "/member/wallet", icon: "fas fa-wallet" },
    { name: "Direct Referrals", href: "/member/network/direct", icon: "fas fa-user-friends" },
    { name: "Matching Network", href: "/member/network/matching", icon: "fas fa-sitemap" },
    { name: "Guru Earnings", href: "/member/network/guru", icon: "fas fa-chalkboard-teacher" },
    { name: "My Coupons", href: "/member/benefits/coupons", icon: "fas fa-ticket-alt" },
    { name: "EV Discounts", href: "/member/benefits/ev", icon: "fas fa-car-battery" },
    { name: "Awards & Perks", href: "/member/benefits/awards", icon: "fas fa-award" },
    { name: "Settings", href: "/member/settings", icon: "fas fa-cog" },
  ];

  const isActive = (href: string) => pathname?.startsWith(href);

  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-screen fixed left-0 top-0 overflow-y-auto custom-scrollbar">
      {/* Brand Logo */}
      <div className="p-6 flex items-center border-b border-gray-800">
        <div className="w-10 h-10 bg-gradient-to-tr from-yellow-400 to-amber-600 rounded-lg flex items-center justify-center font-bold text-xl mr-3 shadow-lg text-white">
          V
        </div>
        <div>
          <h2 className="font-bold text-lg leading-tight tracking-tight text-white">VGK Network</h2>
          <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Member Portal</p>
        </div>
      </div>

      {/* User Info */}
      <div className="p-6 border-b border-gray-800 text-center relative overflow-hidden group">
        <div className="absolute inset-0 bg-gradient-to-b from-gray-800 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
        <div className="w-16 h-16 rounded-full bg-gray-800 border-2 border-amber-500 mx-auto mb-3 flex items-center justify-center text-xl font-bold relative z-10 text-white">
          {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
        </div>
        <h3 className="font-bold text-white relative z-10">{user?.first_name} {user?.last_name}</h3>
        <p className="text-xs text-gray-400 mb-2 relative z-10">{user?.vgk_id}</p>
        
        <span className={`inline-block text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider relative z-10 ${
          user?.tier === 'PLATINUM' ? 'bg-gray-100 text-gray-900' :
          user?.tier === 'GOLD' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
          user?.tier === 'SILVER' ? 'bg-gray-400/20 text-gray-300 border border-gray-400/30' :
          'bg-orange-500/20 text-orange-400 border border-orange-500/30' // Bronze
        }`}>
          {user?.tier || 'BRONZE'} TIER
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 mt-2 px-2">Menu</p>
        {navItems.slice(0, 3).map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive(item.href)
                ? "bg-amber-500/10 text-amber-500"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <i className={`${item.icon} w-6 text-center mr-2 text-lg`}></i>
            {item.name}
          </Link>
        ))}

        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 mt-6 px-2">My Network</p>
        {navItems.slice(3, 6).map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive(item.href)
                ? "bg-amber-500/10 text-amber-500"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <i className={`${item.icon} w-6 text-center mr-2 text-lg`}></i>
            {item.name}
          </Link>
        ))}

        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 mt-6 px-2">Benefits & Perks</p>
        {navItems.slice(6, 9).map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive(item.href)
                ? "bg-amber-500/10 text-amber-500"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <i className={`${item.icon} w-6 text-center mr-2 text-lg`}></i>
            {item.name}
          </Link>
        ))}
      </nav>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-gray-800 mt-auto">
        <Link
          href="/member/settings"
          className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors mb-2 ${
            isActive("/member/settings") ? "bg-amber-500/10 text-amber-500" : "text-gray-400 hover:bg-gray-800 hover:text-white"
          }`}
        >
          <i className="fas fa-cog w-6 text-center mr-2 text-lg"></i>
          Settings
        </Link>
        <button
          onClick={logout}
          className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <i className="fas fa-sign-out-alt w-6 text-center mr-2 text-lg"></i>
          Logout
        </button>
      </div>
    </div>
  );
}

function MemberLayoutContent({ children }: { children: React.ReactNode }) {
  const { isLoading, token, user } = useMemberAuth();
  const pathname = usePathname();

  // If on a public/auth route inside member, don't show sidebar
  if (pathname === "/member/login" || pathname === "/member/signup") {
    return <>{children}</>;
  }

  // Handle protected routes
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <i className="fas fa-spinner fa-spin text-4xl text-amber-500"></i>
      </div>
    );
  }

  // Fallback to login if no token (handled in page components or middleware ideally, but catching here)
  if (!token) {
    // We shouldn't strictly redirect here if we rely on the pages to do it, but we can render empty
    return null; 
  }

  return (
    <div className="flex min-h-screen bg-gray-50 font-sans">
      <MemberSidebar />
      <div className="flex-1 ml-64 flex flex-col min-h-screen relative">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-end px-6 sticky top-0 z-20 shrink-0">
          <div className="flex items-center space-x-4">
            <button className="text-gray-500 hover:text-gray-700 relative">
              <i className="fas fa-bell text-xl"></i>
              <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <div className="h-8 w-px bg-gray-200 mx-2"></div>
            <button className="text-gray-700 font-medium text-sm flex items-center hover:text-amber-600 transition-colors">
              <i className="fas fa-headset mr-2 text-gray-400"></i>
              Support
            </button>
            <div className="h-8 w-px bg-gray-200 mx-2"></div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-sm font-bold text-gray-900">{user?.first_name} {user?.last_name}</p>
                <p className="text-xs text-gray-500">{user?.vgk_id}</p>
              </div>
              <div className="w-9 h-9 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center font-bold text-sm border border-amber-200">
                {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
              </div>
            </div>
          </div>
        </header>

        {/* Main Page Content */}
        <main className="flex-1 overflow-x-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}

export default function MemberLayout({ children }: { children: React.ReactNode }) {
  return (
    <MemberAuthProvider>
      <MemberLayoutContent>
        {children}
      </MemberLayoutContent>
    </MemberAuthProvider>
  );
}
