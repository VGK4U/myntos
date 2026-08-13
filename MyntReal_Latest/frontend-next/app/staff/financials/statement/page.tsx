"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useStaffFetch } from '@/hooks/useStaffFetch';
import StatCard from '@/components/dashboard/StatCard';
import StatusBadge from '@/components/financials/StatusBadge';

const TABS = [
  { id: 'finStatement', label: 'Financial Statement' },
  { id: 'deliverables', label: 'Deliverables Overview' },
  { id: 'revDash', label: 'Revenue Intelligence' },
  { id: 'expenses', label: 'Expenses' },
  { id: 'vgkComm', label: 'VGK4U Commissions' },
  { id: 'pnl', label: 'P&L' },
  { id: 'cashHolding', label: 'Cash Holding' },
  { id: 'dar', label: 'DAR' },
  { id: 'cashflowReg', label: 'Cash Flow Register' }
] as const;

type TabId = typeof TABS[number]['id'];

function FinancialStatementContent() {
  const { staffFetch } = useStaffFetch();
  
  const [activeTab, setActiveTab] = useState<TabId>('finStatement');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);

  // Filters
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().split('T')[0];
  });
  const [toDate, setToDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [category, setCategory] = useState('');

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);

    const params = new URLSearchParams();
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    if (category) params.append('category', category);
    params.append('tab', activeTab);

    try {
      const res = await staffFetch(`/api/v1/financial-statement/summary?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to fetch financial data');
      const json = await res.json();
      setData(json.data || json);
    } catch (err: any) {
      setError(err.message);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  };

  const setPresetDate = (preset: 'ftd' | 'yesterday' | 'week' | 'mtd' | 'fy' | 'overall') => {
    const today = new Date();
    let from = new Date();
    let to = new Date();

    switch(preset) {
      case 'ftd':
        break; // Today
      case 'yesterday':
        from.setDate(today.getDate() - 1);
        to.setDate(today.getDate() - 1);
        break;
      case 'week':
        const day = today.getDay() || 7; 
        if(day !== 1) from.setHours(-24 * (day - 1));
        break;
      case 'mtd':
        from.setDate(1);
        break;
      case 'fy':
        from.setMonth(3, 1); // April 1st
        if (today.getMonth() < 3) from.setFullYear(today.getFullYear() - 1);
        break;
      case 'overall':
        from = new Date('2020-01-01'); // Arbitrary far past
        break;
    }
    
    setFromDate(from.toISOString().split('T')[0]);
    setToDate(to.toISOString().split('T')[0]);
    // Automatically trigger fetch in a real scenario, or wait for explicit Apply
  };

  const renderTabContent = () => {
    if (!data) return null;

    if (activeTab === 'finStatement') {
      const s = data.summary || {};
      return (
        <div className="space-y-6">
          {/* Summary Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <StatCard title="Total Revenue" value={`₹${(s.total_revenue || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Admin Charges" value={`₹${(s.admin_charges || 0).toLocaleString('en-IN')}`} />
            <StatCard title="TDS Received" value={`₹${(s.tds_received || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Income Paid" value={`₹${(s.income_paid || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Total Withdrawals" value={`₹${(s.withdrawals || 0).toLocaleString('en-IN')}`} />
            <StatCard title="Amount Payable" value={`₹${(s.amount_payable || 0).toLocaleString('en-IN')}`} />
          </div>

          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-brand-warning uppercase bg-brand-warning/10 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Date</th>
                    <th className="px-4 py-3 font-semibold">Category</th>
                    <th className="px-4 py-3 font-semibold text-right text-green-400">Revenue (₹)</th>
                    <th className="px-4 py-3 font-semibold text-right text-cyan-400">Payable (₹)</th>
                    <th className="px-4 py-3 font-semibold text-right text-red-400">Payout (₹)</th>
                    <th className="px-4 py-3 font-semibold text-right text-yellow-400">Liability (₹)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/30">
                  {data.records?.map((r: any, i: number) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-600">{new Date(r.date || r.created_at).toLocaleDateString('en-IN')}</td>
                      <td className="px-4 py-3 text-slate-200">{r.category}</td>
                      <td className="px-4 py-3 text-right text-green-400">{(r.revenue || 0).toLocaleString('en-IN')}</td>
                      <td className="px-4 py-3 text-right text-cyan-400">{(r.payable || 0).toLocaleString('en-IN')}</td>
                      <td className="px-4 py-3 text-right text-red-400">{(r.payout || 0).toLocaleString('en-IN')}</td>
                      <td className="px-4 py-3 text-right text-yellow-400">{(r.liability || 0).toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                  {!data.records?.length && (
                    <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No financial records found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      );
    }

    // Generic fallback table for other tabs (Deliverables, Revenue, P&L etc)
    return (
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-brand-warning uppercase bg-brand-warning/10 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 font-semibold">Description</th>
                <th className="px-6 py-4 font-semibold text-right">Amount (₹)</th>
                <th className="px-6 py-4 font-semibold text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {data.records?.map((r: any, i: number) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-slate-200">{r.description || r.category || 'N/A'}</td>
                  <td className="px-6 py-4 text-right font-medium">
                    {(r.amount || r.value || 0).toLocaleString('en-IN')}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <StatusBadge status={r.status || 'Completed'} />
                  </td>
                </tr>
              ))}
              {!data.records?.length && (
                <tr><td colSpan={3} className="px-6 py-8 text-center text-gray-400">No records found for {activeTab}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-screen-2xl mx-auto px-4 pb-12">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
          <span className="text-brand-warning">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
          </span>
          Company Financial Statement
        </h1>
        <p className="text-gray-500 mt-1">Macro-level Revenue, Payouts & Liabilities Overview</p>
      </div>

      {/* Universal Date Bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider mr-2">Quick Filter:</span>
          {['ftd', 'yesterday', 'week', 'mtd', 'fy', 'overall'].map((preset) => (
            <button 
              key={preset}
              onClick={() => setPresetDate(preset as any)}
              className="px-3 py-1 text-xs border border-gray-300 rounded text-gray-600 hover:border-brand-warning hover:text-brand-warning transition-colors"
            >
              {preset.toUpperCase()}
            </button>
          ))}
        </div>
        
        <div className="flex items-center gap-3 w-full md:w-auto">
          <input 
            type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
            className="bg-gray-50 border border-gray-300 rounded text-sm text-slate-200 p-1.5 focus:ring-1 focus:ring-brand-warning outline-none" 
          />
          <span className="text-gray-400">→</span>
          <input 
            type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
            className="bg-gray-50 border border-gray-300 rounded text-sm text-slate-200 p-1.5 focus:ring-1 focus:ring-brand-warning outline-none" 
          />
          {activeTab === 'finStatement' && (
            <select 
              value={category} onChange={(e) => setCategory(e.target.value)}
              className="bg-gray-50 border border-gray-300 rounded text-sm text-slate-200 p-1.5 focus:ring-1 focus:ring-brand-warning outline-none"
            >
              <option value="">All Categories</option>
              <option value="pin_revenue">PIN Revenue</option>
              <option value="income">Income Payouts</option>
              <option value="withdrawal">Withdrawals</option>
            </select>
          )}
          <button 
            onClick={fetchData} disabled={isLoading}
            className="bg-brand-warning hover:bg-yellow-500 text-slate-900 font-medium py-1.5 px-4 rounded text-sm transition-colors disabled:opacity-50"
          >
            {isLoading ? '...' : 'Apply'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-gray-200 mb-6 scrollbar-thin scrollbar-thumb-slate-700">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
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

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Main Content Area */}
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
        {renderTabContent()}
      </div>

    </div>
  );
}

export default function FinancialStatementPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading Statement...</div>}>
      <FinancialStatementContent />
    </Suspense>
  );
}
