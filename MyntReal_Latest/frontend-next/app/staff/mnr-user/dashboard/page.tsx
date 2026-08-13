"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useStaffFetch } from '@/hooks/useStaffFetch';
import SearchCard from '@/components/dashboard/SearchCard';
import StatCard from '@/components/dashboard/StatCard';
import WalletSummary from '@/components/dashboard/WalletSummary';
import QuickActions from '@/components/dashboard/QuickActions';

// Interface definitions for the API response
interface DashboardData {
  mnr_id: string;
  member_info: {
    name: string;
    status: string;
  };
  data: {
    direct_referrals: number;
    team_counts: {
      total_count: number;
      left_count: number;
      right_count: number;
    };
    wallet: {
      earning_wallet: number;
      withdrawable_wallet: number;
      upgrade_wallet: number;
      total_withdrawn: number;
    };
  };
}

function DashboardContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { staffFetch } = useStaffFetch();
  
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);

  // Extract initial MNR ID from URL if present
  useEffect(() => {
    const mnrParam = searchParams.get('mnr_id');
    if (mnrParam && !dashboardData && !isSearching) {
      handleSearch(mnrParam);
    }
  }, [searchParams]);

  const handleSearch = async (mnrId: string) => {
    let cleanMnrId = mnrId.trim().toUpperCase();
    if (!cleanMnrId.startsWith('MNR')) {
      cleanMnrId = 'MNR' + cleanMnrId;
    }

    // Update URL without reloading page
    const newParams = new URLSearchParams(searchParams.toString());
    newParams.set('mnr_id', cleanMnrId);
    router.push(`${pathname}?${newParams.toString()}`);

    setIsSearching(true);
    setError(null);
    setDashboardData(null);

    try {
      const response = await staffFetch(`/api/v1/staff/mnr-user/dashboard/${cleanMnrId}`);
      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail || 'Member not found');
      }

      const data = await response.json();
      setDashboardData(data);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
          <svg className="w-6 h-6 text-brand-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          MNR Member Dashboard
        </h1>
        <p className="text-slate-400 mt-1">Staff access to member network data and financial summaries</p>
      </div>

      <SearchCard 
        onSearch={handleSearch} 
        isSearching={isSearching} 
        memberInfo={dashboardData ? {
          name: dashboardData.member_info.name,
          id: dashboardData.mnr_id,
          status: dashboardData.member_info.status
        } : null}
      />

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6 flex items-center gap-3">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>{error}</p>
        </div>
      )}

      {dashboardData && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <StatCard 
              title="Total Team" 
              value={dashboardData.data.team_counts.total_count}
              icon={<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>}
            />
            <StatCard 
              title="Direct Facilitations" 
              value={dashboardData.data.direct_referrals}
              icon={<svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>}
            />
            <StatCard 
              title="Group A" 
              value={dashboardData.data.team_counts.left_count}
              icon={<svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" /></svg>}
            />
            <StatCard 
              title="Group B" 
              value={dashboardData.data.team_counts.right_count}
              icon={<svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" /></svg>}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <WalletSummary data={dashboardData.data.wallet} />
            <QuickActions mnrId={dashboardData.mnr_id} />
          </div>
        </div>
      )}

      {!dashboardData && !error && !isSearching && (
        <div className="text-center py-16 px-4">
          <div className="w-16 h-16 mx-auto bg-slate-800/50 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-slate-300">No Member Selected</h3>
          <p className="text-slate-500 mt-2">Enter an MNR ID above to view the dashboard</p>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-400">Loading Dashboard...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
