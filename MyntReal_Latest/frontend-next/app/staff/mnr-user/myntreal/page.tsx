"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useStaffFetch } from '@/hooks/useStaffFetch';
import MemberSearchHeader from '@/components/shared/MemberSearchHeader';
import StatCard from '@/components/dashboard/StatCard';

function MyntrealContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { staffFetch } = useStaffFetch();
  
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'properties' | 'earnings'>('properties');
  
  const [propertiesData, setPropertiesData] = useState<any>(null);
  const [earningsData, setEarningsData] = useState<any>(null);

  useEffect(() => {
    const mnrParam = searchParams.get('mnr_id');
    if (mnrParam && !propertiesData && !isSearching) {
      handleSearch(mnrParam);
    }
  }, [searchParams]);

  const handleSearch = async (mnrId: string) => {
    let cleanMnrId = mnrId.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (!cleanMnrId.startsWith('MNR')) cleanMnrId = 'MNR' + cleanMnrId;

    if (!/^MNR\d{1,17}$/.test(cleanMnrId)) {
      setError('Please enter a valid MNR ID (e.g., MNR123456)');
      return;
    }

    const newParams = new URLSearchParams(searchParams.toString());
    newParams.set('mnr_id', cleanMnrId);
    router.push(`${pathname}?${newParams.toString()}`);

    setIsSearching(true);
    setError(null);

    try {
      const [propRes, earnRes] = await Promise.all([
        staffFetch(`/api/v1/staff/mnr-user/myntreal/${cleanMnrId}?tab=properties`),
        staffFetch(`/api/v1/staff/mnr-user/myntreal/${cleanMnrId}?tab=earnings`)
      ]);

      if (!propRes.ok || !earnRes.ok) {
        throw new Error('Failed to load MyntReal data');
      }

      setPropertiesData(await propRes.json());
      setEarningsData(await earnRes.json());
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
      setPropertiesData(null);
      setEarningsData(null);
    } finally {
      setIsSearching(false);
    }
  };

  const getMemberName = () => {
    return propertiesData?.member_info?.name || earningsData?.member_info?.name || searchParams.get('mnr_id');
  };

  const hasData = propertiesData || earningsData;

  return (
    <div className="max-w-7xl mx-auto pb-12">
      <MemberSearchHeader 
        title="MyntReal Data"
        subtitle="View member property referrals and MyntReal earnings"
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
        }
        onSearch={handleSearch}
        isSearching={isSearching}
        memberInfo={hasData ? { name: getMemberName(), id: searchParams.get('mnr_id') || '' } : null}
      />

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {hasData && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex border-b border-gray-200 mb-6">
            <button
              onClick={() => setActiveTab('properties')}
              className={`px-6 py-3 font-medium text-sm transition-colors border-b-2 ${
                activeTab === 'properties' 
                  ? 'border-brand-warning text-brand-warning' 
                  : 'border-transparent text-gray-500 hover:text-slate-200'
              }`}
            >
              Properties
            </button>
            <button
              onClick={() => setActiveTab('earnings')}
              className={`px-6 py-3 font-medium text-sm transition-colors border-b-2 ${
                activeTab === 'earnings' 
                  ? 'border-brand-warning text-brand-warning' 
                  : 'border-transparent text-gray-500 hover:text-slate-200'
              }`}
            >
              Service Activity Overview
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <StatCard 
              title="Total Properties" 
              value={propertiesData?.data?.total || 0}
            />
            <StatCard 
              title="Total Earnings" 
              value={`₹${(earningsData?.data?.total_earnings || 0).toLocaleString('en-IN')}`}
            />
            <StatCard 
              title="Pending Earnings" 
              value={`₹${(earningsData?.data?.pending_earnings || 0).toLocaleString('en-IN')}`}
            />
          </div>

          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              {activeTab === 'properties' ? (
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-brand-warning uppercase bg-brand-warning/10 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-4 font-semibold">ID</th>
                      <th className="px-6 py-4 font-semibold">Name</th>
                      <th className="px-6 py-4 font-semibold">Mobile</th>
                      <th className="px-6 py-4 font-semibold">Category</th>
                      <th className="px-6 py-4 font-semibold">Status</th>
                      <th className="px-6 py-4 font-semibold">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/30">
                    {propertiesData?.data?.properties?.map((p: any) => (
                      <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 text-gray-600">{p.id}</td>
                        <td className="px-6 py-4 text-gray-600">{p.name || '-'}</td>
                        <td className="px-6 py-4 text-gray-600">{p.mobile || '-'}</td>
                        <td className="px-6 py-4 text-gray-600">{p.category || '-'}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            p.status === 'converted' ? 'bg-green-500/10 text-green-400' :
                            p.status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' :
                            'bg-slate-500/10 text-gray-500'
                          }`}>
                            {p.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-500">
                          {p.created_at ? new Date(p.created_at).toLocaleDateString('en-IN') : '-'}
                        </td>
                      </tr>
                    ))}
                    {!propertiesData?.data?.properties?.length && (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-400">
                          No property referrals found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              ) : (
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-brand-warning uppercase bg-brand-warning/10 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-4 font-semibold">ID</th>
                      <th className="px-6 py-4 font-semibold">Lead ID</th>
                      <th className="px-6 py-4 font-semibold">Revenue</th>
                      <th className="px-6 py-4 font-semibold">Service Activity Overview</th>
                      <th className="px-6 py-4 font-semibold">Status</th>
                      <th className="px-6 py-4 font-semibold">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/30">
                    {earningsData?.data?.earnings?.map((e: any) => (
                      <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 text-gray-600">{e.id}</td>
                        <td className="px-6 py-4 text-gray-600">{e.lead_id || '-'}</td>
                        <td className="px-6 py-4 text-gray-600">₹{(e.revenue_amount || 0).toLocaleString('en-IN')}</td>
                        <td className="px-6 py-4 font-semibold text-green-400">₹{(e.mnr_amount || 0).toLocaleString('en-IN')}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium bg-slate-500/10 text-gray-600`}>
                            {e.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-500">
                          {e.created_at ? new Date(e.created_at).toLocaleDateString('en-IN') : '-'}
                        </td>
                      </tr>
                    ))}
                    {!earningsData?.data?.earnings?.length && (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-400">
                          No MyntReal earnings found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MyntrealPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading MyntReal Data...</div>}>
      <MyntrealContent />
    </Suspense>
  );
}
