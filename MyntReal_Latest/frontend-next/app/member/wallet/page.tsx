"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";

export default function MemberWalletPage() {
  const { user } = useMemberAuth();

  const [activeTab, setActiveTab] = useState("all");

  const [stats, setStats] = useState({
    walletBalance: 0,
    totalWithdrawn: 0,
    pendingClearance: 0,
  });
  
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.id) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        // 1. Fetch Auth Me for core balance
        const res = await api.get(`/vgk/auth/me`);
        let currentBalance = 0;
        if (res.data && res.data.success) {
          currentBalance = res.data.dashboard?.wallet_balance || user.wallet_balance || 0;
        }

        // 2. Fetch Withdrawal Summary
        let totalW = 0;
        let pendingW = 0;
        try {
          const sumRes = await api.get('/withdrawals/withdrawal-summary');
          if (sumRes.data) {
            totalW = sumRes.data.total_approved || 0;
            pendingW = sumRes.data.total_pending || 0;
          }
        } catch (e) {
          console.log("Failed to fetch withdrawal summary", e);
        }

        setStats({
          walletBalance: currentBalance,
          totalWithdrawn: totalW,
          pendingClearance: pendingW
        });

        // 3. Fetch Withdrawal Requests (History)
        try {
          const reqRes = await api.get('/withdrawals/withdrawal-requests');
          if (reqRes.data) {
            setRequests(reqRes.data);
          }
        } catch (e) {
          console.log("Failed to fetch withdrawal requests", e);
        }

      } catch (err) {
        console.error("Data fetch failed", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <i className="fas fa-circle-notch fa-spin text-4xl text-emerald-500"></i>
          <p className="text-slate-500 font-medium">Loading Wallet Ledger...</p>
        </div>
      </div>
    );
  }

  // Filter requests based on tab
  const filteredRequests = requests.filter(req => {
    if (activeTab === "all") return true;
    if (activeTab === "pending") return req.status === "Pending";
    if (activeTab === "approved") return req.status === "Approved";
    if (activeTab === "rejected") return req.status === "Rejected";
    return true;
  });

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-bold uppercase tracking-wider mb-2">
            Wallet Ledger
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Financial Overview</h1>
          <p className="text-slate-500 mt-1">Manage your VGK Network earnings and withdrawals</p>
        </div>
        <Link 
          href="/member/wallet/withdraw" 
          className="px-6 py-3 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center gap-2 w-full md:w-auto justify-center"
        >
          <i className="fas fa-money-bill-wave"></i> Request Withdrawal
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-3xl p-8 text-white shadow-lg relative overflow-hidden">
          <i className="fas fa-wallet absolute -right-6 -bottom-6 text-9xl opacity-10"></i>
          <h3 className="text-emerald-100 font-semibold mb-2 relative z-10">Available Balance</h3>
          <p className="text-4xl font-black relative z-10">₹{stats.walletBalance.toLocaleString()}</p>
        </div>
        
        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center text-xl mb-4">
            <i className="fas fa-hourglass-half"></i>
          </div>
          <h3 className="text-slate-500 font-semibold mb-1">Pending Clearance</h3>
          <p className="text-3xl font-black text-slate-900">₹{stats.pendingClearance.toLocaleString()}</p>
        </div>

        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center text-xl mb-4">
            <i className="fas fa-money-check-alt"></i>
          </div>
          <h3 className="text-slate-500 font-semibold mb-1">Total Withdrawn Lifetime</h3>
          <p className="text-3xl font-black text-slate-900">₹{stats.totalWithdrawn.toLocaleString()}</p>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h2 className="text-lg font-bold text-slate-900">Withdrawal History</h2>
          <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
            {['all', 'pending', 'approved', 'rejected'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 text-sm font-bold rounded-md capitalize transition-all ${
                  activeTab === tab 
                    ? 'bg-white text-slate-900 shadow-sm' 
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Request ID</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Amount</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">TDS / Admin / Net</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRequests.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center text-2xl text-slate-400 mx-auto mb-3">
                      <i className="fas fa-receipt"></i>
                    </div>
                    <p className="font-medium">No withdrawal requests found.</p>
                  </td>
                </tr>
              ) : (
                filteredRequests.map((req, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-semibold text-slate-900">{new Date(req.created_at).toLocaleDateString()}</p>
                      <p className="text-xs text-slate-500">{new Date(req.created_at).toLocaleTimeString()}</p>
                    </td>
                    <td className="px-6 py-4 font-mono text-sm text-slate-600">
                      WD-{req.id.toString().padStart(5, '0')}
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-bold text-slate-900">₹{req.amount.toLocaleString()}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1 text-xs text-slate-600">
                        <span>TDS (5%): ₹{req.tds_amount}</span>
                        <span>Admin (5%): ₹{req.admin_charge}</span>
                        <span className="font-bold text-emerald-600">Net: ₹{req.net_amount}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                        req.status === 'Approved' ? 'bg-emerald-100 text-emerald-700' :
                        req.status === 'Rejected' ? 'bg-rose-100 text-rose-700' :
                        'bg-amber-100 text-amber-700'
                      }`}>
                        <i className={`fas ${
                          req.status === 'Approved' ? 'fa-check-circle' :
                          req.status === 'Rejected' ? 'fa-times-circle' :
                          'fa-clock'
                        }`}></i>
                        {req.status}
                      </span>
                      {req.admin_remarks && (
                        <p className="text-xs text-slate-500 mt-1 max-w-[200px] truncate" title={req.admin_remarks}>
                          {req.admin_remarks}
                        </p>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
