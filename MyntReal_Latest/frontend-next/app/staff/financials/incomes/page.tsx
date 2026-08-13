"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useStaffFetch } from '@/hooks/useStaffFetch';
import StatCard from '@/components/dashboard/StatCard';
import StatusBadge from '@/components/financials/StatusBadge';
import IncomeTypePill from '@/components/financials/IncomeTypePill';

function IncomesContent() {
  const { staffFetch } = useStaffFetch();
  
  const [activeTab, setActiveTab] = useState<'records' | 'userView' | 'tdsTracking'>('records');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [role, setRole] = useState({ can_validate: false, can_approve: false });
  const [data, setData] = useState<any>(null);
  
  // Filters
  const [statusFilter, setStatusFilter] = useState('all');
  const [fromDate, setFromDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().split('T')[0];
  });
  const [toDate, setToDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [searchMnr, setSearchMnr] = useState('');

  // Bulk Actions
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    fetchRole();
    fetchData();
  }, [activeTab]);

  const fetchRole = async () => {
    try {
      const res = await staffFetch('/api/v1/income-verification/staff/role');
      if (res.ok) {
        const json = await res.json();
        setRole(json.data || { can_validate: true, can_approve: false });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    setSelectedIds(new Set()); // Reset selections on fetch

    let endpoint = '';
    if (activeTab === 'records') endpoint = '/api/v1/income-verification/list';
    else if (activeTab === 'userView') endpoint = '/api/v1/income-verification/user-view';
    else if (activeTab === 'tdsTracking') endpoint = '/api/v1/income-verification/tds-view';

    const params = new URLSearchParams();
    if (statusFilter !== 'all') params.append('status', statusFilter);
    if (fromDate) params.append('from_date', fromDate);
    if (toDate) params.append('to_date', toDate);
    if (searchMnr) params.append('mnr_id', searchMnr);

    try {
      const res = await staffFetch(`${endpoint}?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to fetch data');
      const json = await res.json();
      setData(json.data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSelection = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const toggleAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked && data?.records) {
      setSelectedIds(new Set(data.records.map((r: any) => r.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleBulkAction = async (action: 'validate' | 'approve') => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Are you sure you want to ${action} ${selectedIds.size} records?`)) return;

    setIsProcessing(true);
    try {
      const res = await staffFetch(`/api/v1/income-verification/bulk-action`, {
        method: 'POST',
        body: JSON.stringify({
          action,
          record_ids: Array.from(selectedIds)
        })
      });

      if (!res.ok) throw new Error(`Failed to ${action} records`);
      
      // Refresh
      await fetchData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-screen-2xl mx-auto px-4 pb-12">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
          <span className="text-brand-warning">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </span>
          Unified Income Management
        </h1>
        <p className="text-gray-500 mt-1">View, Verify, Approve, and Process all MNR incomes</p>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-gray-200 mb-6 scrollbar-thin scrollbar-thumb-slate-700">
        {[
          { id: 'records', label: 'Income Records', icon: 'M4 6h16M4 10h16M4 14h16M4 18h16' },
          { id: 'userView', label: 'User View', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z' },
          { id: 'tdsTracking', label: 'TDS Tracking', icon: 'M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z' }
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={`px-6 py-3 font-medium text-sm transition-colors border-b-2 whitespace-nowrap flex items-center gap-2 ${
              activeTab === t.id 
                ? 'border-brand-warning text-brand-warning bg-brand-warning/5' 
                : 'border-transparent text-gray-500 hover:text-slate-200 hover:bg-gray-50'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={t.icon} />
            </svg>
            {t.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6 shadow-sm">
        <h3 className="text-sm font-medium text-gray-600 uppercase tracking-wider mb-4 flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
          Filters
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select 
              value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full bg-gray-50 border border-gray-300 rounded text-sm text-slate-200 p-2 focus:ring-1 focus:ring-brand-warning outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="Pending">Pending</option>
              <option value="Staff Validated">Staff Validated</option>
              <option value="Completed">Completed</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">From Date</label>
            <input 
              type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
              className="w-full bg-gray-50 border border-gray-300 rounded text-sm text-slate-200 p-2 focus:ring-1 focus:ring-brand-warning outline-none" 
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">To Date</label>
            <input 
              type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
              className="w-full bg-gray-50 border border-gray-300 rounded text-sm text-slate-200 p-2 focus:ring-1 focus:ring-brand-warning outline-none" 
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">MNR ID</label>
            <input 
              type="text" value={searchMnr} onChange={(e) => setSearchMnr(e.target.value.toUpperCase())} placeholder="e.g. MNR123456"
              className="w-full bg-gray-50 border border-gray-300 rounded text-sm text-slate-200 p-2 focus:ring-1 focus:ring-brand-warning outline-none" 
            />
          </div>
          <div className="flex items-end">
            <button 
              onClick={fetchData} disabled={isLoading}
              className="w-full bg-brand-warning hover:bg-yellow-500 text-slate-900 font-medium py-2 px-4 rounded text-sm transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Loading...' : 'Apply Filters'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Summary Stats Row */}
      {data?.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-4 mb-6">
          <StatCard title="Total Gross" value={`₹${(data.summary.total_gross || 0).toLocaleString('en-IN')}`} />
          <StatCard title="Total Net" value={`₹${(data.summary.total_net || 0).toLocaleString('en-IN')}`} />
          <StatCard title="Overall Pending" value={(data.summary.overall_pending_count || 0)} />
          <StatCard title="Pending" value={(data.summary.pending_count || 0)} />
          <StatCard title="Validated" value={(data.summary.validated_count || 0)} />
          <StatCard title="Completed" value={(data.summary.completed_count || 0)} />
          <StatCard title="Cleared" value={(data.summary.cleared_count || 0)} />
          <StatCard title="Total Rows" value={(data.summary.total_records || 0)} />
        </div>
      )}

      {/* Bulk Action Bar for Records Tab */}
      {activeTab === 'records' && (role.can_validate || role.can_approve) && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 flex items-center justify-between shadow-sm">
          <div className="flex gap-3">
            {role.can_validate && (
              <button 
                onClick={() => handleBulkAction('validate')}
                disabled={selectedIds.size === 0 || isProcessing}
                className="bg-blue-600 hover:bg-blue-500 text-gray-900 font-medium py-1.5 px-4 rounded text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                Validate ({selectedIds.size})
              </button>
            )}
            {role.can_approve && (
              <button 
                onClick={() => handleBulkAction('approve')}
                disabled={selectedIds.size === 0 || isProcessing}
                className="bg-green-600 hover:bg-green-500 text-gray-900 font-medium py-1.5 px-4 rounded text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                Approve & Pay ({selectedIds.size})
              </button>
            )}
          </div>
          <div className="text-sm text-gray-500">
            {selectedIds.size} records selected
          </div>
        </div>
      )}

      {/* Data Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-brand-warning uppercase bg-brand-warning/10 border-b border-gray-200">
              <tr>
                {activeTab === 'records' && (
                  <th className="px-4 py-4 w-12">
                    <input type="checkbox" onChange={toggleAll} className="rounded border-gray-300 bg-gray-100 text-brand-warning focus:ring-brand-warning" />
                  </th>
                )}
                <th className="px-6 py-4 font-semibold">User Details</th>
                <th className="px-6 py-4 font-semibold text-right">Gross (₹)</th>
                {activeTab === 'tdsTracking' && <th className="px-6 py-4 font-semibold text-right">TDS 2% (₹)</th>}
                <th className="px-6 py-4 font-semibold text-right">Net (₹)</th>
                {activeTab !== 'userView' && <th className="px-6 py-4 font-semibold">Date / Type</th>}
                <th className="px-6 py-4 font-semibold text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {!data?.records?.length ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-400">
                    {isLoading ? 'Loading records...' : 'No records found matching filters'}
                  </td>
                </tr>
              ) : (
                data.records.map((row: any) => (
                  <tr key={row.id || row.user_id} className="hover:bg-gray-50 transition-colors">
                    {activeTab === 'records' && (
                      <td className="px-4 py-4">
                        <input 
                          type="checkbox" 
                          checked={selectedIds.has(row.id)}
                          onChange={() => toggleSelection(row.id)}
                          className="rounded border-gray-300 bg-gray-100 text-brand-warning focus:ring-brand-warning" 
                        />
                      </td>
                    )}
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-200">{row.user_name || row.member_name}</div>
                      <div className="text-xs text-gray-400 font-mono">{row.user_id || row.mnr_id}</div>
                    </td>
                    <td className="px-6 py-4 text-right text-gray-600">
                      {(row.gross_amount || row.total_gross || 0).toLocaleString('en-IN')}
                    </td>
                    {activeTab === 'tdsTracking' && (
                      <td className="px-6 py-4 text-right text-red-400">
                        {(row.tds_amount || row.total_tds || 0).toLocaleString('en-IN')}
                      </td>
                    )}
                    <td className="px-6 py-4 text-right text-green-400 font-medium">
                      {(row.net_amount || row.total_net || 0).toLocaleString('en-IN')}
                    </td>
                    {activeTab !== 'userView' && (
                      <td className="px-6 py-4">
                        <div className="text-gray-600">{new Date(row.created_at || row.date).toLocaleDateString('en-IN')}</div>
                        {row.income_type && <div className="mt-1"><IncomeTypePill type={row.income_type} /></div>}
                      </td>
                    )}
                    <td className="px-6 py-4 text-center">
                      {activeTab === 'userView' ? (
                        <div className="flex flex-col gap-1 items-center">
                          {row.pending_amount > 0 && <StatusBadge status="Pending" />}
                          {row.cleared_amount > 0 && <StatusBadge status="Cleared" />}
                        </div>
                      ) : (
                        <StatusBadge status={row.status || 'Completed'} />
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

export default function IncomesPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-gray-500">Loading Unified Income...</div>}>
      <IncomesContent />
    </Suspense>
  );
}
