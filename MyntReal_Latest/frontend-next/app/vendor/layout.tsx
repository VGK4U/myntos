"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { VendorAuthProvider, useVendorAuth } from "@/contexts/VendorAuthContext";

function VendorSidebar() {
  const pathname = usePathname();
  const { user, logout } = useVendorAuth();
  
  const navItems = [
    { name: "Dashboard", href: "/vendor/dashboard", icon: "fas fa-store" },
    { name: "Scan Coupon", href: "/vendor/scan", icon: "fas fa-qrcode" },
    { name: "Transactions", href: "/vendor/transactions", icon: "fas fa-receipt" },
    { name: "Support", href: "/vendor/support", icon: "fas fa-headset" },
  ];

  const isActive = (href: string) => pathname?.startsWith(href);

  return (
    <div className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0 overflow-y-auto custom-scrollbar shadow-2xl">
      {/* Brand Logo */}
      <div className="p-6 flex items-center border-b border-slate-800">
        <div className="w-10 h-10 bg-gradient-to-tr from-sky-400 to-blue-600 rounded-lg flex items-center justify-center font-bold text-xl mr-3 shadow-lg text-white">
          V
        </div>
        <div>
          <h2 className="font-bold text-lg leading-tight tracking-tight text-white">VGK Vendor</h2>
          <p className="text-[10px] text-sky-400 uppercase tracking-widest font-bold">Partner Portal</p>
        </div>
      </div>

      {/* User Info */}
      <div className="p-6 border-b border-slate-800 text-center relative overflow-hidden group">
        <div className="absolute inset-0 bg-gradient-to-b from-slate-800 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
        <div className="w-16 h-16 rounded-full bg-slate-800 border-2 border-sky-500 mx-auto mb-3 flex items-center justify-center text-xl font-bold relative z-10 text-white shadow-lg">
          <i className="fas fa-store text-sky-400"></i>
        </div>
        <h3 className="font-bold text-white relative z-10 truncate">{user?.business_name || 'Business Name'}</h3>
        <p className="text-xs text-slate-400 mb-2 relative z-10">{user?.vendor_id || 'V-0000'}</p>
        
        <span className="inline-block bg-green-500/20 text-green-400 border border-green-500/30 text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider relative z-10">
          <i className="fas fa-check-circle mr-1"></i> Active Partner
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className={`flex items-center px-4 py-3 rounded-xl text-sm font-medium transition-all ${
              isActive(item.href)
                ? "bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-inner"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <i className={`${item.icon} w-6 text-center mr-3 text-lg`}></i>
            {item.name}
          </Link>
        ))}
      </nav>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-slate-800 mt-auto">
        <button
          onClick={logout}
          className="w-full flex items-center px-4 py-3 rounded-xl text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors"
        >
          <i className="fas fa-sign-out-alt w-6 text-center mr-3 text-lg"></i>
          Secure Logout
        </button>
      </div>
    </div>
  );
}

function VendorLayoutContent({ children }: { children: React.ReactNode }) {
  const { isLoading, token } = useVendorAuth();
  const pathname = usePathname();

  // If on a public/auth route inside vendor, don't show sidebar
  if (pathname === "/vendor/login") {
    return <>{children}</>;
  }

  // Handle protected routes
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <i className="fas fa-circle-notch fa-spin text-4xl text-sky-500"></i>
      </div>
    );
  }

  if (!token) {
    return null; 
  }

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans">
      <VendorSidebar />
      <div className="flex-1 ml-64 flex flex-col min-h-screen relative">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-end px-6 sticky top-0 z-20 shrink-0 shadow-sm">
          <div className="flex items-center space-x-4">
            <span className="text-sm font-bold text-slate-700 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
              <i className="fas fa-clock text-sky-500 mr-2"></i> {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </span>
            <button className="text-slate-400 hover:text-slate-600 relative">
              <i className="fas fa-bell text-xl"></i>
            </button>
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

export default function VendorLayout({ children }: { children: React.ReactNode }) {
  return (
    <VendorAuthProvider>
      <VendorLayoutContent>
        {children}
      </VendorLayoutContent>
    </VendorAuthProvider>
  );
}
