"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useStaffFetch } from '@/hooks/useStaffFetch';
import MemberSearchHeader from '@/components/shared/MemberSearchHeader';
import StatCard from '@/components/dashboard/StatCard';

function Vgk4uContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { staffFetch } = useStaffFetch();
  
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workings' | 'earnings'>('dashboard');
  const [vgkData, setVgkData] = useState<any>(null);

  useEffect(() => {
    const mnrParam = searchParams.get('mnr_id');
    if (mnrParam && !vgkData && !isSearching) {
      handleSearch(mnrParam, activeTab);
    }
  }, [searchParams]);

  const handleSearch = async (mnrId: string, tabToLoad = activeTab) => {
    let cleanMnrId = mnrId.trim().toUpperCase();
    if (!cleanMnrId.startsWith('MNR')) cleanMnrId = 'MNR' + cleanMnrId;

    const newParams = new URLSearchParams(searchParams.toString());
    newParams.set('mnr_id', cleanMnrId);
    router.push(`${pathname}?${newParams.toString()}`);

    setIsSearching(true);
    setError(null);

    try {
      // Note: Legacy API uses 'zynova' for VGK4U data
      const response = await staffFetch(`/api/v1/staff/mnr-user/zynova/${cleanMnrId}?tab=${tabToLoad}`);
      
      if (!response.ok) {
        throw new Error('Failed to load VGK4U data');
      }

      setVgkData(await response.json());
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
      setVgkData(null);
    } finally {
      setIsSearching(false);
    }
  };

  const handleTabChange = (tab: 'dashboard' | 'workings' | 'earnings') => {
    setActiveTab(tab);
    const mnrId = searchParams.get('mnr_id');
    if (mnrId) {
      handleSearch(mnrId, tab);
    }
  };

  return (
    <div className="max-w-7xl mx-auto pb-12">
      <MemberSearchHeader 
        title="VGK4U Segment"
        subtitle="View VGK4U external segment mappings and workings"
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        }
        onSearch={(id) => handleSearch(id, activeTab)}
        isSearching={isSearching}
        memberInfo={vgkData ? { name: vgkData.member_info?.name, id: searchParams.get('mnr_id') || '' } : null}
      />

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {vgkData && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex border-b border-gray-200 mb-6">
            {(['dashboard', 'workings', 'earnings'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => handleTabChange(tab)}
                className={`px-6 py-3 font-medium text-sm transition-colors border-b-2 capitalize ${
                  activeTab === tab 
                    ? 'border-brand-warning text-brand-warning' 
                    : 'border-transparent text-gray-500 hover:text-slate-200'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard title="Level" value={vgkData.summary?.level || '-'} />
            <StatCard title="Points" value={(vgkData.summary?.points || 0).toLocaleString('en-IN')} />
            <StatCard title="Total Earnings" value={`₹${(vgkData.summary?.earnings || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Team Size" value={vgkData.summary?.team || 0} />
          </div>

          <div className="space-y-4">
            {!vgkData.items || vgkData.items.length === 0 ? (
              <div className="text-center py-12 bg-white border border-gray-200 rounded-lg">
                <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <h3 className="text-lg font-medium text-gray-600">No data found</h3>
              </div>
            ) : (
              vgkData.items.map((item: any, idx: number) => (
                <div key={idx} className="bg-white border border-gray-200 rounded-lg p-5 flex justify-between items-center hover:border-gray-300 transition-colors">
                  <div>
                    <span className="text-slate-200 font-medium">{item.description || item.type}</span>
                    {item.segment && (
                      <span className="text-gray-400 ml-3 text-sm">{item.segment}</span>
                    )}
                  </div>
                  <div className="text-right">
                    <span className={`font-bold ${item.amount >= 0 ? 'text-green-400' : 'text-blue-400'}`}>
                      {item.amount ? `₹${Math.abs(item.amount).toLocaleString('en-IN')}` : item.points ? `${item.points} pts` : ''}
                    </span>
                    {item.date && (
                      <div className="text-gray-400 text-xs mt-1">
                        {new Date(item.date).toLocaleDateString('en-IN')}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Vgk4uPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading VGK4U Data...</div>}>
      <Vgk4uContent />
    </Suspense>
  );
}
