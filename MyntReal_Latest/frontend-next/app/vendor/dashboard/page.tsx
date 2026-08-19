"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useVendorAuth } from "@/contexts/VendorAuthContext";
import api from "@/lib/api";

export default function VendorDashboardPage() {
  const { user } = useVendorAuth();
  
  const [stats, setStats] = useState({
    todayScans: 0,
    totalRevenue: 0,
    activePromos: 0,
    pendingSettlements: 0
  });
  
  const [recentTransactions, setRecentTransactions] = useState<any[]>([]);
  const [announcements, setAnnouncements] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    
    setLoading(true);
    Promise.all([
      api.get('/vendor/me').catch(() => ({ data: {} })),
      api.get('/vendor/me/transactions?per_page=10').catch(() => ({ data: { data: [] } })),
      api.get('/vendor/me/marketplace-products').catch(() => ({ data: [] })),
      api.get('/feedback/public/announcements').catch(() => ({ data: [] }))
    ]).then(([meRes, txRes, prodRes, annRes]) => {
      const vendorData = meRes.data || {};
      const txns = txRes.data?.data || [];
      const prods = prodRes.data || [];
      const anns = annRes.data || [];
      
      setRecentTransactions(txns);
      setAnnouncements(anns);
      
      // Calculate stats
      const today = new Date().toDateString();
      const todayTxns = txns.filter((t: any) => new Date(t.created_at).toDateString() === today);
      const pendingSettlements = txns
        .filter((t: any) => t.status === 'APPROVED' && !t.cashback_credited)
        .reduce((sum: number, t: any) => sum + (t.discount_amount || 0), 0);
        
      setStats({
        todayScans: todayTxns.length,
        totalRevenue: vendorData.total_business_value || 0,
        activePromos: prods.filter((p: any) => p.is_active).length,
        pendingSettlements: pendingSettlements
      });
    }).finally(() => {
      setLoading(false);
    });
  }, [user]);

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Vendor Dashboard</h1>
          <p className="text-sm text-slate-500 mt-2">Welcome back, {user?.vendor_name || 'Vendor'}. Here's what's happening at your store.</p>
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
            <h3 className="text-3xl font-bold text-slate-900">{loading ? '...' : stats.todayScans}</h3>
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
            <h3 className="text-3xl font-bold text-slate-900">₹ {loading ? '...' : (stats.totalRevenue).toLocaleString('en-IN')}</h3>
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
            <h3 className="text-3xl font-bold text-slate-900">₹ {loading ? '...' : (stats.pendingSettlements).toLocaleString('en-IN')}</h3>
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
            <h3 className="text-3xl font-bold text-white">{loading ? '...' : stats.activePromos}</h3>
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
              {announcements.length === 0 ? (
                <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg text-slate-500 text-sm">
                  No new announcements.
                </div>
              ) : (
                announcements.map((ann, idx) => (
                  <div key={idx} className={`p-3 border rounded-lg ${ann.type === 'text' ? 'bg-slate-50 border-slate-100' : 'bg-amber-50 border-amber-100'}`}>
                    <span className={`text-[10px] font-bold uppercase ${ann.type === 'text' ? 'text-slate-500' : 'text-amber-600'}`}>
                      {new Date(ann.created_at).toLocaleDateString()}
                    </span>
                    <p className="text-sm text-slate-800 mt-1 font-medium">{ann.title || ann.description}</p>
                  </div>
                ))
              )}
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
            {loading ? (
              <div className="flex justify-center items-center h-48">
                <i className="fas fa-circle-notch fa-spin text-3xl text-sky-600"></i>
              </div>
            ) : recentTransactions.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-slate-500">
                <i className="fas fa-receipt text-3xl mb-2 text-slate-300"></i>
                <p>No recent transactions</p>
              </div>
            ) : (
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
                        <p className="font-bold text-slate-900 text-sm">{tx.txn_number}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{new Date(tx.created_at).toLocaleString([], { hour: '2-digit', minute:'2-digit', month:'short', day:'numeric' })}</p>
                      </td>
                      <td className="p-4">
                        <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs font-mono font-bold border border-slate-200">
                          {tx.member_partner_id || 'MEMBER'}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <span className="font-bold text-slate-900">₹{tx.amount_total?.toLocaleString('en-IN')}</span>
                      </td>
                      <td className="p-4 text-right">
                        <span className="font-bold text-green-600">-₹{tx.discount_amount?.toLocaleString('en-IN')}</span>
                        <div className="mt-1">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${tx.status === 'APPROVED' ? 'bg-green-100 text-green-700' : tx.status === 'PENDING' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                            {tx.status}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
