"use client";

import React from "react";
import Link from "next/link";
import { useVendorAuth } from "@/contexts/VendorAuthContext";

export default function VendorDashboardPage() {
  const { user } = useVendorAuth();

  const stats = {
    todayScans: 12,
    totalRevenue: 45000,
    activePromos: 2,
    pendingSettlements: 12500
  };

  const recentTransactions = [
    { id: 'TXN-001', memberId: 'VGK00214', date: '2026-08-14T10:30:00', amount: 1500, discount: 150, status: 'SETTLED' },
    { id: 'TXN-002', memberId: 'VGK00441', date: '2026-08-14T09:15:00', amount: 3200, discount: 320, status: 'PENDING' },
    { id: 'TXN-003', memberId: 'VGK00105', date: '2026-08-13T16:45:00', amount: 850, discount: 85, status: 'SETTLED' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Vendor Dashboard</h1>
          <p className="text-sm text-slate-500 mt-2">Welcome back, {user?.owner_name}. Here's what's happening at {user?.business_name}.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/vendor/scan" className="px-5 py-2.5 bg-gradient-to-r from-sky-500 to-blue-600 text-white font-bold rounded-lg shadow-md hover:from-sky-400 hover:to-blue-500 transition-colors">
            <i className="fas fa-camera mr-2"></i> Scan Member QR
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 shrink-0">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between group hover:border-sky-300 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 bg-sky-50 text-sky-600 rounded-full flex items-center justify-center text-xl shadow-inner">
              <i className="fas fa-qrcode"></i>
            </div>
          </div>
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Today's Scans</p>
            <h3 className="text-3xl font-bold text-slate-900">{stats.todayScans}</h3>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between group hover:border-green-300 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 bg-green-50 text-green-600 rounded-full flex items-center justify-center text-xl shadow-inner">
              <i className="fas fa-chart-line"></i>
            </div>
          </div>
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Total Revenue</p>
            <h3 className="text-3xl font-bold text-slate-900">₹ {(stats.totalRevenue).toLocaleString('en-IN')}</h3>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between group hover:border-amber-300 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center text-xl shadow-inner">
              <i className="fas fa-clock"></i>
            </div>
          </div>
          <div>
            <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Pending Settlements</p>
            <h3 className="text-3xl font-bold text-slate-900">₹ {(stats.pendingSettlements).toLocaleString('en-IN')}</h3>
            <p className="text-[10px] text-slate-400 mt-1">To be credited by VGK</p>
          </div>
        </div>

        <div className="bg-gradient-to-br from-slate-900 to-slate-800 p-6 rounded-xl shadow-lg flex flex-col justify-between text-white relative overflow-hidden">
          <i className="fas fa-tags absolute right-[-10px] bottom-[-10px] text-7xl opacity-10 transform -rotate-12"></i>
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-white/10 rounded-full flex items-center justify-center text-xl border border-white/20">
              <i className="fas fa-percentage text-sky-400"></i>
            </div>
          </div>
          <div className="relative z-10">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Active Promos</p>
            <h3 className="text-3xl font-bold text-white">{stats.activePromos}</h3>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 overflow-hidden">
        
        {/* Quick Actions / Announcements */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center">
              <i className="fas fa-bullhorn text-amber-500 mr-2"></i> VGK Announcements
            </h3>
            <div className="space-y-4">
              <div className="p-3 bg-amber-50 border border-amber-100 rounded-lg">
                <span className="text-[10px] font-bold text-amber-600 uppercase">Aug 10, 2026</span>
                <p className="text-sm text-slate-800 mt-1 font-medium">Settlement cycles have been upgraded. Payments are now processed every Tuesday and Friday.</p>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg">
                <span className="text-[10px] font-bold text-slate-500 uppercase">Aug 01, 2026</span>
                <p className="text-sm text-slate-700 mt-1">New QR Code scanning app update is live. Please ensure you are using the latest version.</p>
              </div>
            </div>
          </div>

          <div className="bg-sky-50 rounded-xl border border-sky-100 p-6 flex-1 flex flex-col justify-center items-center text-center">
            <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center text-sky-500 text-2xl shadow-sm mb-4">
              <i className="fas fa-headset"></i>
            </div>
            <h3 className="font-bold text-slate-900 mb-2">Need Help?</h3>
            <p className="text-sm text-slate-600 mb-4">Contact VGK Vendor Support for assistance with settlements or scanning issues.</p>
            <button className="px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50 transition-colors">
              Contact Support
            </button>
          </div>
        </div>

        {/* Recent Transactions List */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
          <div className="p-5 border-b border-slate-200 flex justify-between items-center bg-slate-50">
            <h3 className="font-bold text-slate-900">Recent Member Transactions</h3>
            <button className="text-sm font-bold text-sky-600 hover:text-sky-700">View All</button>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left">
              <thead className="bg-white sticky top-0 shadow-sm">
                <tr className="border-b border-slate-200">
                  <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Transaction</th>
                  <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Member ID</th>
                  <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Bill Amount</th>
                  <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Discount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentTransactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50 transition-colors">
                    <td className="p-4">
                      <p className="font-bold text-slate-900 text-sm">{tx.id}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{new Date(tx.date).toLocaleString([], { hour: '2-digit', minute:'2-digit', month:'short', day:'numeric' })}</p>
                    </td>
                    <td className="p-4">
                      <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs font-mono font-bold border border-slate-200">
                        {tx.memberId}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-bold text-slate-900">₹{tx.amount.toLocaleString('en-IN')}</span>
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-bold text-green-600">-₹{tx.discount.toLocaleString('en-IN')}</span>
                      <div className="mt-1">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${tx.status === 'SETTLED' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                          {tx.status}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
