"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SuperAdminAuthProvider, useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";

function SuperAdminSidebar() {
  const pathname = usePathname();
  const { user, logout } = useSuperAdminAuth();
  
  const navGroups = [
    {
      title: "Core Systems",
      items: [
        { name: "System Dashboard", href: "/superadmin/dashboard", icon: "fas fa-server" },
        { name: "Global Configuration", href: "/superadmin/config", icon: "fas fa-cogs" },
      ]
    },
    {
      title: "Network Oversight",
      items: [
        { name: "Placement Approvals", href: "/superadmin/network/approvals", icon: "fas fa-sitemap" },
        { name: "Red ID Oversight", href: "/superadmin/network/red-ids", icon: "fas fa-id-card-alt" },
        { name: "Awards Management", href: "/superadmin/awards", icon: "fas fa-trophy" },
      ]
    },
    {
      title: "Supreme Finance",
      items: [
        { name: "Master Dashboard", href: "/superadmin/finance/supreme", icon: "fas fa-chart-pie" },
        { name: "Company Revenue", href: "/superadmin/finance/revenue", icon: "fas fa-wallet" },
        { name: "Expense Ledgers", href: "/superadmin/finance/expenses", icon: "fas fa-file-invoice-dollar" },
        { name: "Cash Flow", href: "/superadmin/finance/cash", icon: "fas fa-money-bill-wave" },
      ]
    }
  ];

  const isActive = (href: string) => pathname?.startsWith(href);

  return (
    <div className="w-64 bg-[#0B0F19] border-r border-[#1F2937] text-gray-300 flex flex-col h-screen fixed left-0 top-0 overflow-y-auto custom-scrollbar shadow-2xl z-50">
      
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-[#1F2937] bg-[#111827] sticky top-0 z-10 shrink-0">
        <div className="w-8 h-8 rounded bg-gradient-to-br from-red-600 to-rose-900 flex items-center justify-center font-black text-white mr-3 shadow-[0_0_15px_rgba(225,29,72,0.5)]">
          SA
        </div>
        <div>
          <h2 className="font-bold text-white tracking-wide text-sm leading-tight">SUPER ADMIN</h2>
          <p className="text-[9px] text-red-500 uppercase tracking-widest font-bold">Absolute Authority</p>
        </div>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-8">
        {navGroups.map((group, idx) => (
          <div key={idx}>
            <h3 className="px-3 text-[10px] font-black text-gray-500 uppercase tracking-widest mb-3">
              {group.title}
            </h3>
            <div className="space-y-1">
              {group.items.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    isActive(item.href)
                      ? "bg-red-900/20 text-red-400 border border-red-500/20 shadow-inner"
                      : "text-gray-400 hover:bg-gray-800 hover:text-white"
                  }`}
                >
                  <i className={`${item.icon} w-5 text-center mr-3 text-[15px]`}></i>
                  {item.name}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* User Actions */}
      <div className="p-4 border-t border-[#1F2937] bg-[#111827] mt-auto">
        <div className="flex items-center px-3 mb-4">
          <div className="w-8 h-8 rounded-full bg-gray-800 border border-gray-600 flex items-center justify-center text-xs font-bold text-gray-300 mr-3">
            <i className="fas fa-user-shield"></i>
          </div>
          <div className="flex-1 truncate">
            <p className="text-xs font-bold text-white truncate">{user?.username || 'SysAdmin'}</p>
            <p className="text-[10px] text-gray-500 truncate">{typeof user?.role === 'object' ? ((user?.role as any)?.role_name || (user?.role as any)?.role_code || 'Root Access') : (String(user?.role || 'Root Access'))}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center justify-center px-4 py-2 rounded-lg text-xs font-bold text-gray-400 border border-gray-700 hover:bg-red-900/30 hover:text-red-400 hover:border-red-900/50 transition-colors"
        >
          <i className="fas fa-power-off mr-2"></i> Terminate Session
        </button>
      </div>
    </div>
  );
}

function SuperAdminLayoutContent({ children }: { children: React.ReactNode }) {
  const { isLoading, token } = useSuperAdminAuth();
  const pathname = usePathname();

  // If on a public/auth route inside superadmin, don't show sidebar
  if (pathname === "/superadmin/login") {
    return <>{children}</>;
  }

  // Handle protected routes
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center">
          <i className="fas fa-shield-alt text-4xl text-red-600 mb-4 animate-pulse"></i>
          <p className="text-sm font-bold text-gray-600 uppercase tracking-widest">Verifying Privileges...</p>
        </div>
      </div>
    );
  }

  if (!token) {
    return null; 
  }

  return (
    <div className="flex min-h-screen bg-gray-50 font-sans">
      <SuperAdminSidebar />
      <div className="flex-1 ml-64 flex flex-col min-h-screen relative">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-20 shrink-0 shadow-sm">
          <div className="flex items-center">
             <div className="bg-red-50 text-red-600 border border-red-200 px-3 py-1 rounded text-xs font-bold flex items-center">
               <span className="w-2 h-2 rounded-full bg-red-600 mr-2 animate-pulse"></span>
               PRODUCTION SYSTEM - USE CAUTION
             </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm font-bold text-gray-700 bg-gray-100 px-3 py-1.5 rounded-full border border-gray-200">
              <i className="fas fa-clock text-red-500 mr-2"></i> {new Date().toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
            </span>
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

export default function SuperAdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <SuperAdminAuthProvider>
      <SuperAdminLayoutContent>
        {children}
      </SuperAdminLayoutContent>
    </SuperAdminAuthProvider>
  );
}
