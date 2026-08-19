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
  const [bonanzas, setBonanzas] = useState<any[]>([]);
  const [memberCard, setMemberCard] = useState<any>(null);
  const [leadsSummary, setLeadsSummary] = useState<any>({ total: 0, converted: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.id) return;

    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // 1. Fetch Auth Me / Dashboard core stats
        const res = await api.get(`/vgk/auth/me`);
        if (res.data && res.data.success) {
          const dash = res.data.dashboard || {};
          setStats({
            walletBalance: dash.wallet_balance || user.wallet_balance || 0,
            totalEarnings: dash.total_income || dash.total_earnings || 0,
            directReferrals: dash.direct_referrals_count || 0,
            matchingPairs: dash.matching_pairs_count || 0,
            pendingWithdrawals: dash.pending_withdrawals || 0,
          });
        }

        // 2. Fetch Member Card Preview
        try {
          const cardRes = await api.get(`/vgk/member-card-preview/me`);
          if (cardRes.data && cardRes.data.success) {
            setMemberCard(cardRes.data.card_data);
          }
        } catch (e) {
          console.log("Card preview error (can safely ignore if not generated)", e);
        }

        // 3. Fetch Bonanzas
        try {
          const bonanzaRes = await api.get(`/bonanza/my-bonanzas`);
          if (bonanzaRes.data && bonanzaRes.data.success) {
            setBonanzas(bonanzaRes.data.bonanzas || []);
          }
        } catch (e) {
          console.log("Bonanza fetch error", e);
        }

        // 4. Fetch Leads Summary
        try {
          const leadsRes = await api.get(`/vgk/dashboard/leads/`);
          if (leadsRes.data) {
            setLeadsSummary({
              total: leadsRes.data.total_leads || 0,
              converted: leadsRes.data.converted_leads || 0
            });
          }
        } catch (e) {
          console.log("Leads summary error", e);
        }

      } catch (err) {
        console.error("Dashboard data fetch failed", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [user]);

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <i className="fas fa-circle-notch fa-spin text-4xl text-emerald-500"></i>
          <p className="text-slate-500 font-medium">Synchronizing Ecosystem Data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Welcome Hero Panel */}
      <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-200 mb-8 relative overflow-hidden flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-50 rounded-full blur-3xl opacity-60 -mr-10 -mt-10 pointer-events-none"></div>
        <div className="absolute bottom-0 right-32 w-48 h-48 bg-blue-50 rounded-full blur-3xl opacity-60 -mb-10 pointer-events-none"></div>
        
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-bold uppercase tracking-wider mb-4">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Member Dashboard V2
          </div>
          <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight mb-2">
            Welcome back, {user?.name || user?.first_name || 'Member'}!
          </h1>
          <p className="text-slate-600 text-lg">
            Your Account Status is <span className="font-bold text-emerald-600">{user?.account_status || 'Active'}</span>. 
            View your real-time network growth and earnings below.
          </p>
        </div>
        
        <div className="relative z-10 flex gap-4 w-full md:w-auto">
          <Link href="/member/wallet/withdraw" className="flex-1 md:flex-none px-6 py-3.5 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center justify-center gap-2">
            <i className="fas fa-arrow-down"></i> Withdraw
          </Link>
          <button className="flex-1 md:flex-none px-6 py-3.5 bg-white border border-slate-200 text-slate-700 font-bold rounded-xl hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 transition-all flex items-center justify-center gap-2">
            <i className="fas fa-share-alt"></i> Promo Link
          </button>
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
        
        {/* KPI 1 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-wallet"></i>
            </div>
            <span className="text-emerald-500 bg-emerald-50 px-2 py-1 rounded-md text-xs font-bold">+12%</span>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Current Wallet Balance</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">₹{stats.walletBalance.toLocaleString()}</p>
        </div>

        {/* KPI 2 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-chart-line"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Total Lifetime Earnings</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">₹{stats.totalEarnings.toLocaleString()}</p>
        </div>

        {/* KPI 3 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-users"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Direct Referrals</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{stats.directReferrals}</p>
        </div>

        {/* KPI 4 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 relative overflow-hidden group">
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
              <i className="fas fa-sitemap"></i>
            </div>
          </div>
          <h3 className="text-slate-500 font-semibold text-sm mb-1 relative z-10">Matching Pairs</h3>
          <p className="text-3xl font-black text-slate-900 relative z-10">{stats.matchingPairs}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column - Bonanzas & Leads */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Active Bonanzas */}
          <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-200">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">Active Bonanza Challenges</h2>
              <Link href="/member/benefits/awards" className="text-sm font-bold text-indigo-600 hover:text-indigo-700">View All</Link>
            </div>
            
            {bonanzas.length === 0 ? (
              <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center">
                <div className="w-16 h-16 bg-slate-200 text-slate-400 rounded-full flex items-center justify-center text-2xl mx-auto mb-4">
                  <i className="fas fa-trophy"></i>
                </div>
                <h3 className="text-lg font-bold text-slate-700 mb-1">No Active Bonanzas</h3>
                <p className="text-sm text-slate-500">Check back later for new promotional challenges.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {bonanzas.map((b, idx) => (
                  <div key={idx} className="border border-slate-200 rounded-2xl p-5 hover:border-indigo-300 transition-colors">
                    <h4 className="font-bold text-slate-900 mb-2">{b.title || 'Bonanza Challenge'}</h4>
                    <p className="text-xs text-slate-500 mb-4">{b.description || 'Complete targets to earn rewards.'}</p>
                    <div className="w-full bg-slate-100 rounded-full h-2 mb-2">
                      <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${Math.min(100, (b.progress/b.target)*100 || 0)}%` }}></div>
                    </div>
                    <div className="flex justify-between text-xs font-bold text-slate-600">
                      <span>{b.progress || 0} / {b.target || 0}</span>
                      <span>{Math.round(Math.min(100, (b.progress/b.target)*100 || 0))}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Cross-Auth / Cross-Promotion */}
          <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-200">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight mb-2">Cross-Platform Access</h2>
            <p className="text-slate-500 text-sm mb-6">Instantly jump to other MyntReal ecosystem platforms using your current secure session.</p>
            
            <div className="flex flex-wrap gap-4">
              <button className="px-5 py-3 border border-slate-200 rounded-xl font-bold text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all flex items-center gap-3">
                <img src="https://ui-avatars.com/api/?name=Partner+Network&background=e2e8f0&color=475569" className="w-6 h-6 rounded-md" alt="icon"/>
                Partner Catalog
              </button>
              <button className="px-5 py-3 border border-slate-200 rounded-xl font-bold text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all flex items-center gap-3">
                <img src="https://ui-avatars.com/api/?name=EV+Portal&background=e2e8f0&color=475569" className="w-6 h-6 rounded-md" alt="icon"/>
                EV Connect
              </button>
            </div>
          </div>

        </div>

        {/* Right Column - ID Card & Summary */}
        <div className="space-y-8">
          
          {/* Member ID Card */}
          <div className="bg-slate-900 rounded-3xl p-1 shadow-lg relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500 to-purple-600 opacity-20 group-hover:opacity-40 transition-opacity"></div>
            <div className="bg-slate-900 rounded-[22px] p-6 h-full relative z-10 border border-slate-700 flex flex-col">
              
              <div className="flex justify-between items-start mb-8">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center shadow-lg">
                    <span className="text-slate-900 font-black text-sm tracking-tighter">V</span>
                  </div>
                  <span className="text-white font-bold tracking-widest text-xs uppercase">VGK Pass</span>
                </div>
                <i className="fas fa-wifi text-slate-600 rotate-90"></i>
              </div>

              <div className="mt-auto">
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Cardholder</p>
                <p className="text-white font-black text-xl tracking-tight mb-4">{user?.name || user?.first_name || 'Member'}</p>
                
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-slate-500 text-[10px] uppercase tracking-widest mb-1">VGK ID</p>
                    <p className="text-slate-300 font-mono text-sm tracking-widest">{user?.vgk_id || 'VGK-XXXX-XXXX'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-slate-500 text-[10px] uppercase tracking-widest mb-1">KYC</p>
                    <p className={`font-bold text-xs ${user?.kyc_status === 'Approved' ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {user?.kyc_status || 'Pending'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* CRM Leads Summary */}
          <div className="bg-white rounded-3xl p-6 shadow-sm border border-slate-200">
            <h2 className="text-lg font-bold text-slate-900 mb-4 tracking-tight">Leads Overview</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center text-sm">
                    <i className="fas fa-funnel-dollar"></i>
                  </div>
                  <span className="font-semibold text-slate-700 text-sm">Total Leads</span>
                </div>
                <span className="font-black text-slate-900">{leadsSummary.total}</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center text-sm">
                    <i className="fas fa-check-circle"></i>
                  </div>
                  <span className="font-semibold text-slate-700 text-sm">Converted</span>
                </div>
                <span className="font-black text-slate-900">{leadsSummary.converted}</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
