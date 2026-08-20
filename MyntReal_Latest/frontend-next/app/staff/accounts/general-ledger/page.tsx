"use client";

import { useState, useEffect, useMemo } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";
import Link from "next/link";

interface LedgerEntry {
  id: number;
  entry_type: string;
  account_name: string;
  debit: number;
  credit: number;
  reference_no: string;
  reference_type: string;
  created_at: string;
  status: string;
  source: string;
  remarks?: string;
}

export default function GeneralLedgerPage() {
  const { token } = useStaffAuth();
  const [activeTab, setActiveTab] = useState("daybook");
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const fetchEntries = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/general-ledger/entries`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch ledger entries");
      setEntries(data.entries || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, [token]);

  // Derived computations for the Premium UX
  const filteredEntries = useMemo(() => {
    return entries.filter(entry => {
      const matchesSearch = entry.account_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            (entry.reference_no && entry.reference_no.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesStatus = statusFilter === "ALL" || entry.status === statusFilter;
      
      let matchesDate = true;
      if (dateFrom && dateTo) {
        const entryDate = new Date(entry.created_at).getTime();
        matchesDate = entryDate >= new Date(dateFrom).getTime() && entryDate <= new Date(dateTo).getTime();
      }
      
      return matchesSearch && matchesStatus && matchesDate;
    });
  }, [entries, searchQuery, statusFilter, dateFrom, dateTo]);

  const totalDebit = filteredEntries.reduce((sum, e) => sum + Number(e.debit || 0), 0);
  const totalCredit = filteredEntries.reduce((sum, e) => sum + Number(e.credit || 0), 0);
  const netBalance = totalDebit - totalCredit;

  return (
    <div className="min-h-screen bg-gray-50/50 pb-12">
      {/* Enterprise Header */}
      <div className="bg-white border-b border-gray-200 px-8 py-6 sticky top-0 z-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 max-w-screen-2xl mx-auto">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
                <i className="fas fa-book text-white text-lg"></i>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 tracking-tight">General Ledger</h1>
                <p className="text-sm text-gray-500 font-medium mt-0.5">Financial tracking, Day Book, and Chart of Accounts</p>
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={fetchEntries} className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 hover:text-indigo-600 transition-all flex items-center gap-2 text-sm">
              <i className="fas fa-sync-alt"></i> Refresh Data
            </button>
            <Link href="/staff/accounts/journal-voucher" className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 hover:shadow transition-all flex items-center gap-2 text-sm">
              <i className="fas fa-plus"></i> New Journal Entry
            </Link>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-screen-2xl mx-auto space-y-8">
        
        {/* KPI Metrics Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm relative overflow-hidden group hover:border-indigo-300 transition-colors">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <i className="fas fa-file-invoice text-6xl text-indigo-600"></i>
            </div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Entries</p>
            <p className="text-3xl font-bold text-gray-900">{filteredEntries.length}</p>
            <p className="text-xs text-green-600 font-medium mt-2 flex items-center gap-1">
              <i className="fas fa-arrow-up"></i> Based on active filters
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm relative overflow-hidden hover:border-red-300 transition-colors">
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Debit (Dr)</p>
            <p className="text-3xl font-bold text-red-600">₹{totalDebit.toLocaleString('en-IN', {minimumFractionDigits: 2})}</p>
            <p className="text-xs text-gray-400 mt-2">Money flowing out / Assets increasing</p>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm relative overflow-hidden hover:border-green-300 transition-colors">
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Credit (Cr)</p>
            <p className="text-3xl font-bold text-green-600">₹{totalCredit.toLocaleString('en-IN', {minimumFractionDigits: 2})}</p>
            <p className="text-xs text-gray-400 mt-2">Money flowing in / Liabilities increasing</p>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm relative overflow-hidden">
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Net Balance</p>
            <p className={`text-3xl font-bold ${netBalance >= 0 ? 'text-purple-600' : 'text-orange-600'}`}>
              ₹{Math.abs(netBalance).toLocaleString('en-IN', {minimumFractionDigits: 2})} {netBalance >= 0 ? 'Dr' : 'Cr'}
            </p>
            <div className="w-full bg-gray-100 h-1.5 rounded-full mt-4 overflow-hidden flex">
              <div className="bg-red-500 h-full" style={{ width: `${(totalDebit / (totalDebit + totalCredit || 1)) * 100}%` }}></div>
              <div className="bg-green-500 h-full" style={{ width: `${(totalCredit / (totalDebit + totalCredit || 1)) * 100}%` }}></div>
            </div>
          </div>
        </div>

        {/* Modular Tabs */}
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {[
              { id: 'daybook', name: 'Day Book & Transactions', icon: 'fa-list' },
              { id: 'chart', name: 'Chart of Accounts', icon: 'fa-sitemap' },
              { id: 'reports', name: 'Ledger Reports', icon: 'fa-chart-pie' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors
                  ${activeTab === tab.id 
                    ? 'border-indigo-600 text-indigo-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
                `}
              >
                <i className={`fas ${tab.icon}`}></i>
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content: Day Book (The core data table) */}
        {activeTab === "daybook" && (
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col">
            
            {/* Advanced Filters Bar */}
            <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex flex-wrap gap-4 items-end rounded-t-xl">
              <div className="flex-1 min-w-[250px]">
                <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Search Entries</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <i className="fas fa-search text-gray-400"></i>
                  </div>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Search account name, ref no..."
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Status</label>
                <select 
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="CONFIRMED">Confirmed</option>
                  <option value="PENDING">Pending</option>
                  <option value="REJECTED">Rejected</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Date Range</label>
                <div className="flex items-center gap-2">
                  <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} className="block py-2 px-3 text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                  <span className="text-gray-400">to</span>
                  <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} className="block py-2 px-3 text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500" />
                </div>
              </div>

              <div className="flex-shrink-0">
                <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 flex items-center gap-2 transition-colors">
                  <i className="fas fa-download"></i> Export CSV
                </button>
              </div>
            </div>

            {/* Data Table */}
            <div className="overflow-x-auto min-h-[400px]">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full py-20 text-gray-500">
                  <i className="fas fa-circle-notch fa-spin text-4xl text-indigo-600 mb-4"></i>
                  <p className="font-medium">Loading ledger entries...</p>
                </div>
              ) : error ? (
                <div className="p-8">
                  <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
                    <div className="flex">
                      <div className="flex-shrink-0"><i className="fas fa-exclamation-circle text-red-500"></i></div>
                      <div className="ml-3"><p className="text-sm text-red-700">{error}</p></div>
                    </div>
                  </div>
                </div>
              ) : filteredEntries.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                  <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                    <i className="fas fa-folder-open text-3xl text-gray-400"></i>
                  </div>
                  <p className="font-medium text-lg text-gray-900">No entries found</p>
                  <p className="text-sm mt-1">Adjust your filters or add a new journal entry.</p>
                </div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Account Particulars</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Reference</th>
                      <th scope="col" className="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Debit (₹)</th>
                      <th scope="col" className="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Credit (₹)</th>
                      <th scope="col" className="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                      <th scope="col" className="relative px-6 py-3"><span className="sr-only">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredEntries.map((entry) => (
                      <tr key={entry.id} className="hover:bg-gray-50/80 transition-colors group">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {new Date(entry.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center">
                            <div>
                              <div className="text-sm font-bold text-gray-900">{entry.account_name}</div>
                              <div className="text-xs text-gray-500 mt-0.5">
                                <span className="uppercase font-bold tracking-wider text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded mr-2">{entry.entry_type}</span>
                                {entry.remarks || entry.source}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{entry.reference_no || "-"}</div>
                          <div className="text-xs text-gray-500">{entry.reference_type}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-red-600 text-right">
                          {entry.debit > 0 ? entry.debit.toLocaleString('en-IN', {minimumFractionDigits: 2}) : ""}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-green-600 text-right">
                          {entry.credit > 0 ? entry.credit.toLocaleString('en-IN', {minimumFractionDigits: 2}) : ""}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className={`px-2.5 py-1 inline-flex text-[10px] leading-5 font-bold rounded-full uppercase tracking-wider
                            ${entry.status === 'CONFIRMED' ? 'bg-green-100 text-green-800' : 
                              entry.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' : 
                              'bg-red-100 text-red-800'}`}>
                            {entry.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button className="text-gray-400 hover:text-indigo-600 transition-colors opacity-0 group-hover:opacity-100">
                            <i className="fas fa-ellipsis-v p-2"></i>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            {/* Pagination Footer */}
            <div className="bg-gray-50 px-6 py-3 border-t border-gray-200 flex items-center justify-between rounded-b-xl">
              <div className="text-sm text-gray-500">
                Showing <span className="font-medium text-gray-900">{filteredEntries.length > 0 ? 1 : 0}</span> to <span className="font-medium text-gray-900">{filteredEntries.length}</span> of <span className="font-medium text-gray-900">{filteredEntries.length}</span> entries
              </div>
              <div className="flex gap-2">
                <button className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-50 text-sm font-medium"><i className="fas fa-chevron-left"></i></button>
                <button className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-500 hover:bg-gray-50 disabled:opacity-50 text-sm font-medium"><i className="fas fa-chevron-right"></i></button>
              </div>
            </div>
          </div>
        )}

        {/* Tab Content: Chart of Accounts (Placeholder for now) */}
        {activeTab === "chart" && (
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-12 text-center text-gray-500">
             <div className="w-24 h-24 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-6 border border-gray-100">
               <i className="fas fa-sitemap text-4xl text-indigo-200"></i>
             </div>
             <h3 className="text-xl font-bold text-gray-900 mb-2">Chart of Accounts Matrix</h3>
             <p className="max-w-md mx-auto mb-6">Manage all system ledgers, grouped by Assets, Liabilities, Equity, Revenue, and Expenses.</p>
             <button className="px-4 py-2 bg-indigo-50 text-indigo-700 font-medium rounded-lg hover:bg-indigo-100 transition-colors border border-indigo-100">
               <i className="fas fa-plus mr-2"></i> Create Account Head
             </button>
          </div>
        )}
        
      </div>
    </div>
  );
}
