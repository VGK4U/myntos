"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { useStaffFetch } from '@/hooks/useStaffFetch';
import MemberSearchHeader from '@/components/shared/MemberSearchHeader';
import StatCard from '@/components/dashboard/StatCard';
import StatusBadge from '@/components/financials/StatusBadge';
import IncomeTypePill from '@/components/financials/IncomeTypePill';

const TABS = [
  { id: 'summary', label: 'Summary' },
  { id: 'direct', label: 'Direct Facilitation' },
  { id: 'matching', label: 'Group Performance' },
  { id: 'ved', label: 'VED Leadership' },
  { id: 'guru', label: 'Mentorship (Guru)' },
  { id: 'withdrawals', label: 'Withdrawals' },
  { id: 'points', label: 'VGK4U Points' },
  { id: 'benefits', label: 'Benefits' },
  { id: 'wallet', label: 'Wallet Ledger' }
] as const;

type TabId = typeof TABS[number]['id'];

function EarningsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const { staffFetch } = useStaffFetch();
  
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('summary');
  const [data, setData] = useState<any>(null);
  
  // Basic pagination state (if needed by specific tabs)
  const [page, setPage] = useState(1);

  useEffect(() => {
    const mnrParam = searchParams.get('mnr_id');
    const tabParam = searchParams.get('tab') as TabId;
    
    if (tabParam && TABS.some(t => t.id === tabParam)) {
      setActiveTab(tabParam);
    }

    if (mnrParam && (!data || activeTab !== tabParam) && !isSearching) {
      fetchData(mnrParam, tabParam || activeTab, 1);
    }
  }, [searchParams]);

  const fetchData = async (mnrId: string, tabId: TabId, pageNum: number = 1) => {
    let cleanMnrId = mnrId.trim().toUpperCase();
    if (!cleanMnrId.startsWith('MNR')) cleanMnrId = 'MNR' + cleanMnrId;

    const newParams = new URLSearchParams(searchParams.toString());
    newParams.set('mnr_id', cleanMnrId);
    newParams.set('tab', tabId);
    router.push(`${pathname}?${newParams.toString()}`);

    setIsSearching(true);
    setError(null);
    setPage(pageNum);

    try {
      const response = await staffFetch(`/api/v1/staff/mnr-user/mnr/${cleanMnrId}?tab=${tabId}&page=${pageNum}`);
      if (!response.ok) {
        throw new Error(`Failed to load ${tabId} data`);
      }
      const jsonData = await response.json();
      setData(jsonData);
      setActiveTab(tabId);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
      setData(null);
    } finally {
      setIsSearching(false);
    }
  };

  const renderTabContent = () => {
    if (!data) return null;

    if (activeTab === 'summary') {
      const summary = data.summary || {};
      return (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard title="Direct Facilitation" value={`₹${(summary.direct_income || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Group Performance" value={`₹${(summary.matching_income || 0).toLocaleString('en-IN')}`} />
            <StatCard title="VED Leadership" value={`₹${(summary.ved_income || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Mentorship (Guru)" value={`₹${(summary.guru_dakshina || 0).toLocaleString('en-IN')}`} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <StatCard title="Total Earnings" value={`₹${(summary.total_income || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Total Withdrawals" value={`₹${(summary.total_withdrawal || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Wallet Balance" value={`₹${(summary.wallet_balance || 0).toLocaleString('en-IN')}`} />
          </div>
        </div>
      );
    }

    if (activeTab === 'wallet') {
      return (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-brand-warning uppercase bg-brand-warning/10 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 font-semibold">Date</th>
                <th className="px-6 py-4 font-semibold">Description</th>
                <th className="px-6 py-4 font-semibold text-right">Amount (₹)</th>
                <th className="px-6 py-4 font-semibold text-right">Balance (₹)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {data.records?.map((record: any, idx: number) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-gray-500">
                    {record.created_at ? new Date(record.created_at).toLocaleDateString('en-IN') : '-'}
                  </td>
                  <td className="px-6 py-4 text-slate-200">{record.description}</td>
                  <td className={`px-6 py-4 text-right font-medium ${record.amount >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {record.amount >= 0 ? '+' : ''}{record.amount.toLocaleString('en-IN')}
                  </td>
                  <td className="px-6 py-4 text-right text-gray-600">
                    {record.balance?.toLocaleString('en-IN') || '-'}
                  </td>
                </tr>
              ))}
              {!data.records?.length && (
                <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-400">No wallet records found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      );
    }

    // Default table for Direct, Matching, VED, Guru, Withdrawals
    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-brand-warning uppercase bg-brand-warning/10 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 font-semibold">Date</th>
              <th className="px-6 py-4 font-semibold">Type/Desc</th>
              <th className="px-6 py-4 font-semibold text-right">Amount (₹)</th>
              <th className="px-6 py-4 font-semibold text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/30">
            {data.records?.map((record: any, idx: number) => (
              <tr key={record.id || idx} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 text-gray-500">
                  {new Date(record.created_at || record.date).toLocaleDateString('en-IN')}
                </td>
                <td className="px-6 py-4">
                  {record.income_type ? <IncomeTypePill type={record.income_type} /> : (record.description || record.type)}
                </td>
                <td className="px-6 py-4 text-right font-medium text-slate-200">
                  {(record.net_amount || record.amount || 0).toLocaleString('en-IN')}
                </td>
                <td className="px-6 py-4 text-center">
                  <StatusBadge status={record.status || 'Completed'} />
                </td>
              </tr>
            ))}
            {!data.records?.length && (
              <tr><td colSpan={4} className="px-6 py-8 text-center text-gray-400">No records found for {activeTab}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto pb-12">
      <MemberSearchHeader 
        title="Member Earnings & Wallets"
        subtitle="Comprehensive financial ledger for member"
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
        onSearch={(id) => fetchData(id, activeTab, 1)}
        isSearching={isSearching}
        memberInfo={data ? { name: data.member_info?.name, id: searchParams.get('mnr_id') || '' } : null}
      />

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {data && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Scrollable Tabs */}
          <div className="flex overflow-x-auto border-b border-gray-200 mb-6 scrollbar-thin scrollbar-thumb-slate-700">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => fetchData(searchParams.get('mnr_id')!, tab.id, 1)}
                className={`px-5 py-3 font-medium text-sm transition-colors border-b-2 whitespace-nowrap ${
                  activeTab === tab.id 
                    ? 'border-brand-warning text-brand-warning bg-brand-warning/5' 
                    : 'border-transparent text-gray-500 hover:text-slate-200 hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {renderTabContent()}

          {/* Pagination Controls (if data supports it) */}
          {data.pagination && data.pagination.total_pages > 1 && (
            <div className="flex justify-between items-center mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <span className="text-sm text-gray-500">
                Page {data.pagination.current_page} of {data.pagination.total_pages}
              </span>
              <div className="flex gap-2">
                <button 
                  disabled={data.pagination.current_page <= 1 || isSearching}
                  onClick={() => fetchData(searchParams.get('mnr_id')!, activeTab, data.pagination.current_page - 1)}
                  className="px-4 py-2 text-sm bg-gray-200 hover:bg-slate-600 text-gray-900 rounded disabled:opacity-50"
                >
                  Previous
                </button>
                <button 
                  disabled={data.pagination.current_page >= data.pagination.total_pages || isSearching}
                  onClick={() => fetchData(searchParams.get('mnr_id')!, activeTab, data.pagination.current_page + 1)}
                  className="px-4 py-2 text-sm bg-gray-200 hover:bg-slate-600 text-gray-900 rounded disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function EarningsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading Earnings Data...</div>}>
      <EarningsContent />
    </Suspense>
  );
}
