"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface JVEntry {
  id: number;
  jv_number: string;
  jv_date: string;
  amount: number;
  debit_account: string;
  credit_account: string;
  status: string;
  narration: string;
}

export default function JournalVouchersPage() {
  const { token } = useStaffAuth();
  const [activeTab, setActiveTab] = useState("all");
  const [entries, setEntries] = useState<JVEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // JV Form state
  const [jvRows, setJvRows] = useState([{ id: 1, account: "", debit: "", credit: "" }, { id: 2, account: "", debit: "", credit: "" }]);

  useEffect(() => {
    if (!token) return;
    
    // Fallback data in case the endpoint isn't fully ready yet
    const fetchJVs = async () => {
      try {
        setLoading(true);
        // Using generic transactions endpoint with JV filter
        const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/journal/transactions`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setEntries(data.items || []);
        } else {
          setEntries([]);
        }
      } catch (err: any) {
        console.warn("Failed to fetch journal vouchers, using empty state", err);
        setEntries([]);
      } finally {
        setLoading(false);
      }
    };

    fetchJVs();
  }, [token]);

  const addJvRow = () => {
    setJvRows([...jvRows, { id: Date.now(), account: "", debit: "", credit: "" }]);
  };

  const removeJvRow = (id: number) => {
    if (jvRows.length > 2) {
      setJvRows(jvRows.filter(row => row.id !== id));
    }
  };

  const calculateTotal = (type: 'debit' | 'credit') => {
    return jvRows.reduce((sum, row) => sum + (Number(row[type]) || 0), 0);
  };

  const isBalanced = calculateTotal('debit') === calculateTotal('credit') && calculateTotal('debit') > 0;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Journal Vouchers (JV)</h1>
          <p className="text-sm text-gray-500 mt-2">Record complex accounting adjustments, write-offs, and multi-ledger entries.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/general-ledger" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-book mr-2"></i> General Ledger
          </Link>
          <button onClick={() => setActiveTab("new")} className="px-4 py-2 bg-purple-600 text-white font-medium rounded-lg shadow-sm hover:bg-purple-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Create JV
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-purple-500 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <p className="text-xs font-bold text-gray-500 uppercase">Total JVs</p>
            <i className="fas fa-book-journal-whills text-purple-300 text-xl"></i>
          </div>
          <p className="text-3xl font-bold text-gray-900 mt-2">{entries.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <p className="text-xs font-bold text-gray-500 uppercase">Total Volume</p>
            <i className="fas fa-rupee-sign text-indigo-300 text-xl"></i>
          </div>
          <p className="text-3xl font-bold text-indigo-600 mt-2">
            ₹{entries.reduce((sum, e) => sum + Number(e.amount || 0), 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-yellow-500 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <p className="text-xs font-bold text-gray-500 uppercase">Draft / Unbalanced</p>
            <i className="fas fa-balance-scale-left text-yellow-300 text-xl"></i>
          </div>
          <p className="text-3xl font-bold text-yellow-600 mt-2">
            0
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-6 border-b border-gray-200 mb-6 overflow-x-auto">
        <button onClick={() => setActiveTab("all")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 ${activeTab === "all" ? "border-purple-600 text-purple-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <i className="fas fa-list mr-2"></i> All JVs
        </button>
        <button onClick={() => setActiveTab("new")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 ${activeTab === "new" ? "border-purple-600 text-purple-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <i className="fas fa-pen-nib mr-2"></i> Create JV
        </button>
      </div>

      {/* Content Area */}
      {activeTab === "all" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
            <h2 className="font-semibold text-gray-800"><i className="fas fa-book-journal-whills mr-2 text-purple-500"></i> Journal Entries</h2>
          </div>
          
          {loading ? (
            <div className="p-12 text-center text-gray-500">
              <i className="fas fa-spinner fa-spin text-3xl mb-3 text-purple-500"></i>
              <p>Loading journal entries...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center text-red-500 bg-red-50">
              <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
              <p>{error}</p>
            </div>
          ) : entries.length === 0 ? (
            <div className="p-16 text-center text-gray-500 flex flex-col items-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <i className="fas fa-book-journal-whills text-2xl text-gray-400"></i>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-1">No journal vouchers found</h3>
              <p className="text-gray-500 mb-4">There are currently no journal vouchers recorded in the system.</p>
              <button onClick={() => setActiveTab("new")} className="px-4 py-2 bg-purple-50 text-purple-600 font-medium rounded hover:bg-purple-100 transition-colors">
                Create First JV
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">JV No.</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Primary Debit</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Primary Credit</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount (₹)</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {entries.map(entry => (
                    <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                      <td className="p-4 text-sm text-gray-600">{new Date(entry.jv_date).toLocaleDateString()}</td>
                      <td className="p-4 text-sm font-medium text-purple-600">{entry.jv_number}</td>
                      <td className="p-4">
                        <span className="text-sm font-semibold text-gray-900">{entry.debit_account}</span>
                      </td>
                      <td className="p-4">
                        <span className="text-sm font-semibold text-gray-900">{entry.credit_account}</span>
                      </td>
                      <td className="p-4 text-sm font-bold text-gray-900 text-right">{entry.amount.toFixed(2)}</td>
                      <td className="p-4 text-center">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                          entry.status === "CONFIRMED" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                        }`}>
                          {entry.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "new" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-6 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Create Journal Voucher (JV)</h2>
              <p className="text-gray-500 text-sm mt-1">Ensure total debits equal total credits to successfully post the JV.</p>
            </div>
            <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
              <i className="fas fa-scale-balanced text-purple-600"></i>
            </div>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-2">JV Date *</label>
                <input type="date" className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all outline-none" defaultValue={new Date().toISOString().split('T')[0]} />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Reference No. (Optional)</label>
                <input type="text" className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all outline-none" placeholder="e.g. INV-1234, ADJ-99" />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-2">JV Type</label>
                <select className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all outline-none">
                  <option value="REGULAR">Regular Adjustment</option>
                  <option value="OPENING">Opening Balance</option>
                  <option value="DEPRECIATION">Depreciation</option>
                  <option value="WRITE_OFF">Write-off / Bad Debt</option>
                </select>
              </div>
            </div>

            <div className="border border-gray-200 rounded-lg overflow-hidden mb-6">
              <table className="w-full text-left border-collapse">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="p-3 text-xs font-bold text-gray-600 uppercase w-10 text-center">#</th>
                    <th className="p-3 text-xs font-bold text-gray-600 uppercase">Ledger Account</th>
                    <th className="p-3 text-xs font-bold text-gray-600 uppercase w-40">Debit (₹)</th>
                    <th className="p-3 text-xs font-bold text-gray-600 uppercase w-40">Credit (₹)</th>
                    <th className="p-3 text-xs font-bold text-gray-600 uppercase w-12 text-center"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {jvRows.map((row, index) => (
                    <tr key={row.id}>
                      <td className="p-3 text-center text-sm text-gray-400 font-medium">{index + 1}</td>
                      <td className="p-3">
                        <input type="text" className="w-full p-2 bg-transparent border border-gray-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none" placeholder="Search account..." value={row.account} onChange={(e) => {
                          const newRows = [...jvRows];
                          newRows[index].account = e.target.value;
                          setJvRows(newRows);
                        }} />
                      </td>
                      <td className="p-3">
                        <input type="number" min="0" step="0.01" className="w-full p-2 bg-transparent border border-gray-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none text-right font-medium text-red-600" placeholder="0.00" value={row.debit} onChange={(e) => {
                          const newRows = [...jvRows];
                          newRows[index].debit = e.target.value;
                          if (e.target.value) newRows[index].credit = "";
                          setJvRows(newRows);
                        }} disabled={!!row.credit} />
                      </td>
                      <td className="p-3">
                        <input type="number" min="0" step="0.01" className="w-full p-2 bg-transparent border border-gray-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none text-right font-medium text-green-600" placeholder="0.00" value={row.credit} onChange={(e) => {
                          const newRows = [...jvRows];
                          newRows[index].credit = e.target.value;
                          if (e.target.value) newRows[index].debit = "";
                          setJvRows(newRows);
                        }} disabled={!!row.debit} />
                      </td>
                      <td className="p-3 text-center">
                        <button type="button" onClick={() => removeJvRow(row.id)} className={`text-gray-400 hover:text-red-500 transition-colors ${jvRows.length <= 2 ? 'opacity-50 cursor-not-allowed' : ''}`} disabled={jvRows.length <= 2}>
                          <i className="fas fa-trash"></i>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-gray-50 border-t border-gray-200">
                  <tr>
                    <td colSpan={2} className="p-3">
                      <button type="button" onClick={addJvRow} className="text-sm font-semibold text-purple-600 hover:text-purple-700 flex items-center">
                        <i className="fas fa-plus-circle mr-1"></i> Add Row
                      </button>
                    </td>
                    <td className="p-3 text-right font-bold text-red-600">₹{calculateTotal('debit').toFixed(2)}</td>
                    <td className="p-3 text-right font-bold text-green-600">₹{calculateTotal('credit').toFixed(2)}</td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>
            
            <div className="mb-6">
              <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Narration (Mandatory) *</label>
              <textarea rows={3} className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200 transition-all outline-none" placeholder="Enter detailed reason for this journal voucher..."></textarea>
            </div>
            
            <div className="flex items-center justify-between pt-4 border-t border-gray-100">
              <div className="flex items-center">
                {isBalanced ? (
                  <span className="flex items-center text-sm font-medium text-green-600 bg-green-50 px-3 py-1.5 rounded-full">
                    <i className="fas fa-check-circle mr-2"></i> JV is balanced and ready to post
                  </span>
                ) : (
                  <span className="flex items-center text-sm font-medium text-red-500 bg-red-50 px-3 py-1.5 rounded-full">
                    <i className="fas fa-exclamation-circle mr-2"></i> Debits must equal Credits
                  </span>
                )}
              </div>
              <div className="flex space-x-3">
                <button type="button" onClick={() => setActiveTab("all")} className="px-5 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">
                  Cancel
                </button>
                <button type="button" disabled={!isBalanced} className={`px-5 py-2.5 font-medium rounded-lg shadow-sm flex items-center transition-colors ${isBalanced ? 'bg-purple-600 text-white hover:bg-purple-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}>
                  <i className="fas fa-save mr-2"></i> Post Voucher
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
