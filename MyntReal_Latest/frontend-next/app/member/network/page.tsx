"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function MemberNetworkPage() {
  const { user } = useMemberAuth();
  const [networkStats, setNetworkStats] = useState({
    directCount: 0,
    matchingCount: 0,
    leftLegVolume: 0,
    rightLegVolume: 0,
    guruCount: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.mnr_id) return;
    
    setLoading(true);
    
    // Fetch network summary
    api.get(`/vgk/network/summary`)
      .then(res => {
        if (res.data && res.data.success) {
          setNetworkStats({
            directCount: res.data.data.direct_count || 0,
            matchingCount: res.data.data.matching_count || 0,
            leftLegVolume: res.data.data.left_leg_volume || 0,
            rightLegVolume: res.data.data.right_leg_volume || 0,
            guruCount: res.data.data.guru_count || 0,
          });
        }
      })
      .catch(err => console.error("Failed to fetch network summary", err))
      .finally(() => setLoading(false));
  }, [user]);

  return (
    <div className="p-6 max-w-[1600px] mx-auto min-h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">My Network</h1>
          <p className="text-slate-500 mt-2 text-lg">Manage your team, track referrals, and explore your genealogy.</p>
        </div>
        <Button className="flex items-center gap-2" size="lg">
          <i className="fas fa-plus"></i> Invite New Member
        </Button>
      </div>

      {/* Network Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card className="hover:border-primary transition-colors cursor-pointer group" onClick={() => window.location.href = '/member/network/direct'}>
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">Direct Referrals</p>
              <h3 className="text-4xl font-black text-slate-900">{loading ? '...' : networkStats.directCount}</h3>
            </div>
            <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
              <i className="fas fa-user-friends"></i>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-primary transition-colors cursor-pointer group" onClick={() => window.location.href = '/member/network/matching'}>
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">Matching Pairs</p>
              <h3 className="text-4xl font-black text-slate-900">{loading ? '...' : networkStats.matchingCount}</h3>
            </div>
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
              <i className="fas fa-sitemap"></i>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-primary transition-colors cursor-pointer group" onClick={() => window.location.href = '/member/network/guru'}>
          <CardContent className="p-6 flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-1">Guru Network</p>
              <h3 className="text-4xl font-black text-slate-900">{loading ? '...' : networkStats.guruCount}</h3>
            </div>
            <div className="w-14 h-14 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
              <i className="fas fa-graduation-cap"></i>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6 flex items-center justify-between">
            <div className="w-full">
              <p className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-3">Leg Volumes</p>
              <div className="flex justify-between w-full mb-1">
                <span className="text-xs font-bold text-slate-700">L: {loading ? '...' : networkStats.leftLegVolume}</span>
                <span className="text-xs font-bold text-slate-700">R: {loading ? '...' : networkStats.rightLegVolume}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2 mb-2 flex">
                <div className="bg-blue-500 h-2 rounded-l-full" style={{ width: `${(networkStats.leftLegVolume / ((networkStats.leftLegVolume + networkStats.rightLegVolume) || 1)) * 100}%` }}></div>
                <div className="bg-emerald-500 h-2 rounded-r-full" style={{ width: `${(networkStats.rightLegVolume / ((networkStats.leftLegVolume + networkStats.rightLegVolume) || 1)) * 100}%` }}></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Genealogy Tree Viewer Placeholder */}
      <Card className="mb-8 border-slate-200">
        <CardHeader className="border-b border-slate-100 bg-slate-50 rounded-t-xl">
          <div className="flex justify-between items-center">
            <div>
              <CardTitle className="text-xl">Genealogy Tree</CardTitle>
              <CardDescription>Visual representation of your downline network</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">
                <i className="fas fa-search mr-2"></i> Search ID
              </Button>
              <Button variant="outline" size="sm">
                <i className="fas fa-expand mr-2"></i> Fullscreen
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="w-full h-[600px] bg-slate-50 flex items-center justify-center relative overflow-hidden">
            {/* Simple static tree for visual representation */}
            <div className="absolute inset-0 pattern-dots text-slate-300 opacity-50" style={{ backgroundSize: '20px 20px', backgroundImage: 'radial-gradient(currentColor 1px, transparent 1px)' }}></div>
            
            <div className="relative z-10 flex flex-col items-center">
              {/* Root Node */}
              <div className="bg-white border-2 border-primary rounded-xl p-4 shadow-lg w-48 text-center relative mb-12 cursor-pointer hover:-translate-y-1 transition-transform">
                <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full mx-auto flex items-center justify-center text-xl font-bold mb-2 shadow-inner">
                  {user?.name?.charAt(0) || 'M'}
                </div>
                <h4 className="font-bold text-slate-900 truncate">{user?.name || 'You'}</h4>
                <p className="text-xs text-primary font-mono font-bold mt-1">{user?.mnr_id || 'ID-HERE'}</p>
                <div className="absolute -bottom-12 left-1/2 w-0.5 h-12 bg-slate-300 -translate-x-1/2"></div>
              </div>

              {/* Children Row */}
              <div className="flex gap-16 relative">
                {/* Horizontal connector */}
                <div className="absolute top-0 left-24 right-24 h-0.5 bg-slate-300"></div>
                
                {/* Left Child */}
                <div className="flex flex-col items-center relative">
                  <div className="absolute -top-12 left-1/2 w-0.5 h-12 bg-slate-300 -translate-x-1/2"></div>
                  <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm w-40 text-center hover:border-primary transition-colors cursor-pointer">
                    <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-full mx-auto flex items-center justify-center font-bold mb-2">L</div>
                    <h4 className="text-sm font-bold text-slate-900">Left Leg</h4>
                    <p className="text-[10px] text-slate-500 mt-1">{networkStats.leftLegVolume} PV</p>
                  </div>
                </div>

                {/* Right Child */}
                <div className="flex flex-col items-center relative">
                  <div className="absolute -top-12 left-1/2 w-0.5 h-12 bg-slate-300 -translate-x-1/2"></div>
                  <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm w-40 text-center hover:border-primary transition-colors cursor-pointer">
                    <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-full mx-auto flex items-center justify-center font-bold mb-2">R</div>
                    <h4 className="text-sm font-bold text-slate-900">Right Leg</h4>
                    <p className="text-[10px] text-slate-500 mt-1">{networkStats.rightLegVolume} PV</p>
                  </div>
                </div>
              </div>

              {/* Notice */}
              <div className="mt-16 bg-white/80 backdrop-blur-sm border border-slate-200 px-6 py-3 rounded-full shadow-sm text-sm font-medium text-slate-600 flex items-center gap-3">
                <i className="fas fa-info-circle text-primary"></i>
                Genealogy tree visualizer active. Click any node to expand their downline.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

    </div>
  );
}
