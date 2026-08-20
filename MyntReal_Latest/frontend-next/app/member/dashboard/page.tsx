"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
  const [leadsSummary, setLeadsSummary] = useState<any>({ total: 0, converted: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.id) return;

    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // 1. Fetch Dashboard stats
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

        // 2. Fetch Bonanzas
        try {
          const bonanzaRes = await api.get(`/bonanza/my-bonanzas`);
          if (bonanzaRes.data && bonanzaRes.data.success) {
            setBonanzas(bonanzaRes.data.bonanzas || []);
          }
        } catch (e) {
          console.log("Bonanza fetch error", e);
        }

        // 3. Fetch Leads Summary
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
          <i className="fas fa-circle-notch fa-spin text-4xl text-primary"></i>
          <p className="text-muted-foreground font-medium">Synchronizing Ecosystem Data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Welcome Hero Panel */}
      <Card className="mb-8 border-slate-200 shadow-sm relative overflow-hidden bg-white">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-50 rounded-full blur-3xl opacity-60 -mr-10 -mt-10 pointer-events-none"></div>
        <div className="absolute bottom-0 right-32 w-48 h-48 bg-blue-50 rounded-full blur-3xl opacity-60 -mb-10 pointer-events-none"></div>
        <CardContent className="p-8 flex flex-col md:flex-row justify-between items-center gap-6 relative z-10">
          <div>
            <Badge variant="secondary" className="mb-4 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border-emerald-100">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse mr-2"></span>
              Member Dashboard V2
            </Badge>
            <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight mb-2">
              Welcome back, {user?.name || user?.first_name || 'Member'}!
            </h1>
            <p className="text-slate-600 text-lg">
              Your Account Status is <span className="font-bold text-emerald-600">{user?.account_status || 'Active'}</span>. 
              View your real-time network growth and earnings below.
            </p>
          </div>
          <div className="flex gap-4 w-full md:w-auto">
            <Link href="/member/wallet/withdraw" className="w-full md:w-auto">
              <Button size="lg" className="w-full flex items-center gap-2">
                <i className="fas fa-arrow-down"></i> Withdraw
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="w-full md:w-auto flex items-center gap-2 text-slate-700">
              <i className="fas fa-share-alt"></i> Promo Link
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
        
        <Card className="overflow-hidden group">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
                <i className="fas fa-wallet"></i>
              </div>
            </div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Current Wallet Balance</p>
            <h3 className="text-3xl font-black text-slate-900">₹{stats.walletBalance.toLocaleString()}</h3>
          </CardContent>
        </Card>

        <Card className="overflow-hidden group">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
                <i className="fas fa-chart-line"></i>
              </div>
            </div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Total Lifetime Earnings</p>
            <h3 className="text-3xl font-black text-slate-900">₹{stats.totalEarnings.toLocaleString()}</h3>
          </CardContent>
        </Card>

        <Card className="overflow-hidden group">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
                <i className="fas fa-users"></i>
              </div>
            </div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Direct Referrals</p>
            <h3 className="text-3xl font-black text-slate-900">{stats.directReferrals}</h3>
          </CardContent>
        </Card>

        <Card className="overflow-hidden group">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-xl flex items-center justify-center text-xl shadow-inner group-hover:scale-110 transition-transform">
                <i className="fas fa-sitemap"></i>
              </div>
            </div>
            <p className="text-sm font-medium text-muted-foreground mb-1">Matching Pairs</p>
            <h3 className="text-3xl font-black text-slate-900">{stats.matchingPairs}</h3>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column - Bonanzas & Leads */}
        <div className="lg:col-span-2 space-y-8">
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xl">Active Bonanza Challenges</CardTitle>
              <Link href="/member/benefits/awards" className="text-sm font-bold text-primary hover:underline">View All</Link>
            </CardHeader>
            <CardContent>
              {bonanzas.length === 0 ? (
                <div className="bg-slate-50 border border-slate-100 rounded-2xl p-8 text-center mt-4">
                  <div className="w-16 h-16 bg-slate-200 text-slate-400 rounded-full flex items-center justify-center text-2xl mx-auto mb-4">
                    <i className="fas fa-trophy"></i>
                  </div>
                  <h3 className="text-lg font-bold text-slate-700 mb-1">No Active Bonanzas</h3>
                  <p className="text-sm text-slate-500">Check back later for new promotional challenges.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                  {bonanzas.map((b, idx) => (
                    <div key={idx} className="border border-slate-200 rounded-2xl p-5 hover:border-primary transition-colors">
                      <h4 className="font-bold text-slate-900 mb-2">{b.title || 'Bonanza Challenge'}</h4>
                      <p className="text-xs text-slate-500 mb-4">{b.description || 'Complete targets to earn rewards.'}</p>
                      <div className="w-full bg-slate-100 rounded-full h-2 mb-2">
                        <div className="bg-primary h-2 rounded-full" style={{ width: `${Math.min(100, (b.progress/b.target)*100 || 0)}%` }}></div>
                      </div>
                      <div className="flex justify-between text-xs font-bold text-slate-600">
                        <span>{b.progress || 0} / {b.target || 0}</span>
                        <span>{Math.round(Math.min(100, (b.progress/b.target)*100 || 0))}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Cross-Platform Access</CardTitle>
              <CardDescription>Instantly jump to other MyntReal ecosystem platforms using your current secure session.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <Button variant="outline" className="h-auto py-3 px-5 flex items-center gap-3 font-bold text-slate-700">
                  <img src="https://ui-avatars.com/api/?name=Partner+Network&background=e2e8f0&color=475569" className="w-6 h-6 rounded-md" alt="icon"/>
                  Partner Catalog
                </Button>
                <Button variant="outline" className="h-auto py-3 px-5 flex items-center gap-3 font-bold text-slate-700">
                  <img src="https://ui-avatars.com/api/?name=EV+Portal&background=e2e8f0&color=475569" className="w-6 h-6 rounded-md" alt="icon"/>
                  EV Connect
                </Button>
              </div>
            </CardContent>
          </Card>

        </div>

        {/* Right Column - ID Card & Summary */}
        <div className="space-y-8">
          
          <div className="bg-slate-900 rounded-3xl p-1 shadow-lg relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500 to-purple-600 opacity-20 group-hover:opacity-40 transition-opacity"></div>
            <div className="bg-slate-900 rounded-[22px] p-6 relative z-10 border border-slate-700 flex flex-col h-full min-h-[200px]">
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

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Leads Overview</CardTitle>
            </CardHeader>
            <CardContent>
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
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
