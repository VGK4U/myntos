"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";

export default function MemberDashboardPage() {
  const { user } = useMemberAuth();
  const [stats, setStats] = useState({
    walletBalance: 0,
    totalEarnings: 0,
    directReferrals: 0,
    matchingPairs: 0,
    pendingWithdrawals: 0,
  });
  const [recentTransactions, setRecentTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.mnr_id) return;

    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        // Fetch comprehensive stats
        const res = await api.get(`/user/${user.mnr_id}/comprehensive`);
        if (res.data && res.data.success) {
          const dash = res.data.dashboard;
          setStats({
            walletBalance: dash.wallet_balance || user.wallet_balance || 0,
            totalEarnings: dash.total_income || dash.total_earnings || 0,
            directReferrals: dash.direct_referrals_count || 0,
            matchingPairs: dash.matching_pairs_count || 0,
            pendingWithdrawals: dash.pending_withdrawals || 0,
          });
        }

        // Fetch recent transactions
        const finRes = await api.get(`/user/${user.mnr_id}/financial-summary`);
        if (finRes.data && finRes.data.success) {
          const txs = finRes.data.recent_transactions || [];
          setRecentTransactions(
            txs.slice(0, 5).map((tx: any) => ({
              id: tx.id || Math.random(),
              type: tx.amount > 0 ? 'CREDIT' : 'DEBIT',
              amount: Math.abs(tx.amount || 0),
              desc: tx.description || tx.transaction_type || 'Transaction',
              date: tx.date || tx.created_at || new Date().toISOString()
            }))
          );
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <i className="fas fa-circle-notch fa-spin text-3xl text-amber-500"></i>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-2xl p-8 text-white shadow-xl mb-8 relative overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[150%] bg-gradient-to-l from-amber-500/20 to-transparent transform rotate-12 pointer-events-none"></div>
        <i className="fas fa-crown absolute right-10 bottom-[-20px] text-9xl opacity-10"></i>
        
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-2">
              Welcome back, {user?.first_name || 'Member'}! 👋
            </h1>
            <p className="text-gray-300 max-w-xl">
              Your {user?.tier || 'GOLD'} tier membership is active. You are currently earning 
              <span className="text-amber-400 font-bold ml-1">15% higher matching bonuses</span> this month.
            </p>
          </div>
          
          <div className="flex gap-3">
            <Link href="/member/wallet/withdraw" className="px-5 py-2.5 bg-amber-500 text-gray-900 font-bold rounded-lg shadow-lg hover:bg-amber-400 transition-all transform hover:-translate-y-0.5 active:translate-y-0 text-sm">
              <i className="fas fa-hand-holding-usd mr-2"></i> Withdraw Funds
            </Link>
          </div>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Wallet Balance */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between group hover:border-amber-300 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center text-xl shadow-inner">
              <i className="fas fa-wallet"></i>
            </div>
            <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-1 rounded-full uppercase">Available</span>
          </div>
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">E-Wallet Balance</p>
            <h3 className="text-3xl font-bold text-gray-900">₹ {(stats.walletBalance).toLocaleString('en-IN')}</h3>
          </div>
        </div>

        {/* Total Earnings */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between group hover:border-green-300 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 bg-green-50 text-green-600 rounded-full flex items-center justify-center text-xl shadow-inner">
              <i className="fas fa-chart-line"></i>
            </div>
          </div>
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Lifetime Earnings</p>
            <h3 className="text-3xl font-bold text-gray-900">₹ {(stats.totalEarnings).toLocaleString('en-IN')}</h3>
          </div>
        </div>

        {/* Direct Referrals */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between group hover:border-blue-300 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center text-xl shadow-inner">
              <i className="fas fa-user-friends"></i>
            </div>
            <Link href="/member/network/direct" className="text-xs text-blue-600 font-bold hover:underline">View All</Link>
          </div>
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Direct Referrals</p>
            <div className="flex items-end gap-2">
              <h3 className="text-3xl font-bold text-gray-900">{stats.directReferrals}</h3>
              <span className="text-sm text-gray-500 mb-1">Active</span>
            </div>
          </div>
        </div>

        {/* Matching Pairs */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex flex-col justify-between group hover:border-purple-300 transition-colors">
          <div className="flex justify-between items-start mb-4">
            <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-full flex items-center justify-center text-xl shadow-inner">
              <i className="fas fa-sitemap"></i>
            </div>
            <Link href="/member/network/matching" className="text-xs text-purple-600 font-bold hover:underline">View Tree</Link>
          </div>
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Matching Pairs</p>
            <div className="flex items-end gap-2">
              <h3 className="text-3xl font-bold text-gray-900">{stats.matchingPairs}</h3>
              <span className="text-sm text-gray-500 mb-1">Completed</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Quick Links & Referral Box */}
        <div className="space-y-6 lg:col-span-1">
          {/* Referral Link Box */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center text-lg">
                <i className="fas fa-link"></i>
              </div>
              <h3 className="font-bold text-gray-900 text-lg">Share Referral Link</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Earn 5% direct commission on any real estate or solar purchases made through your link.
            </p>
            <div className="flex bg-gray-50 border border-gray-200 rounded-lg overflow-hidden">
              <input 
                type="text" 
                readOnly 
                value={`https://vgknetwork.com/join?ref=${user?.vgk_id || 'VGK000'}`}
                className="w-full bg-transparent px-3 py-2 text-sm text-gray-600 outline-none"
              />
              <button className="bg-gray-200 hover:bg-gray-300 px-4 py-2 text-gray-700 font-bold text-sm transition-colors border-l border-gray-300">
                <i className="far fa-copy"></i>
              </button>
            </div>
            
            <div className="mt-4 grid grid-cols-3 gap-2">
              <button className="flex flex-col items-center justify-center p-2 rounded bg-green-50 text-green-600 hover:bg-green-100 transition-colors">
                <i className="fab fa-whatsapp text-xl mb-1"></i>
                <span className="text-[10px] font-bold">WhatsApp</span>
              </button>
              <button className="flex flex-col items-center justify-center p-2 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors">
                <i className="fab fa-facebook-f text-xl mb-1"></i>
                <span className="text-[10px] font-bold">Facebook</span>
              </button>
              <button className="flex flex-col items-center justify-center p-2 rounded bg-sky-50 text-sky-600 hover:bg-sky-100 transition-colors">
                <i className="fab fa-twitter text-xl mb-1"></i>
                <span className="text-[10px] font-bold">Twitter</span>
              </button>
            </div>
          </div>

          {/* Pending Actions */}
          <div className="bg-amber-50 rounded-xl border border-amber-200 p-5">
            <h3 className="font-bold text-amber-900 mb-3 flex items-center">
              <i className="fas fa-exclamation-triangle text-amber-500 mr-2"></i> Action Required
            </h3>
            <ul className="space-y-3">
              {user?.kyc_status !== 'VERIFIED' && (
                <li className="flex justify-between items-center text-sm">
                  <span className="text-amber-800 font-medium">Complete KYC Verification</span>
                  <Link href="/member/settings" className="px-3 py-1 bg-amber-600 text-white rounded text-xs font-bold hover:bg-amber-700">Verify</Link>
                </li>
              )}
              <li className="flex justify-between items-center text-sm">
                <span className="text-amber-800 font-medium">Add Bank Account Details</span>
                <Link href="/member/settings" className="px-3 py-1 bg-amber-600 text-white rounded text-xs font-bold hover:bg-amber-700">Update</Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Recent Transactions & Activity */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden h-full flex flex-col">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center">
              <h3 className="font-bold text-gray-900 text-lg">Recent Transactions</h3>
              <Link href="/member/wallet" className="text-sm font-bold text-indigo-600 hover:text-indigo-800">
                View Statement <i className="fas fa-arrow-right ml-1"></i>
              </Link>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              <ul className="divide-y divide-gray-100">
                {recentTransactions.map((tx) => (
                  <li key={tx.id} className="p-4 hover:bg-gray-50 transition-colors flex justify-between items-center">
                    <div className="flex items-center">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center mr-4 shrink-0 ${
                        tx.type === 'CREDIT' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                      }`}>
                        <i className={`fas ${tx.type === 'CREDIT' ? 'fa-arrow-down' : 'fa-arrow-up'}`}></i>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-gray-900">{tx.desc}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{new Date(tx.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
                      </div>
                    </div>
                    <div className="text-right shrink-0 ml-4">
                      <span className={`font-bold text-lg ${tx.type === 'CREDIT' ? 'text-green-600' : 'text-gray-900'}`}>
                        {tx.type === 'CREDIT' ? '+' : '-'}₹ {tx.amount.toLocaleString('en-IN')}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
