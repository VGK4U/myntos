"use client";

import { useState, useEffect } from "react";
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
}

export default function GeneralLedgerPage() {
  const { token } = useStaffAuth();
  const [activeTab, setActiveTab] = useState("daybook");
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
    if (activeTab === "daybook") {
      fetchEntries();
    }
  }, [token, activeTab]);

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <i className="fas fa-book text-indigo-600"></i>
            General Ledger
          </h1>
          <p className="text-sm text-gray-500 mt-1">Day Book � Chart of Accounts � Bank Accounts � Transaction Accounts</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link href="/staff/accounts/journal-voucher" className="px-4 py-2 bg-green-600 text-white font-semibold rounded-lg shadow hover:bg-green-700 transition-colors flex items-center gap-2 text-sm">
            <i className="fas fa-exchange-alt"></i> New Journal / Transfer
          </Link>
          <Link href="/staff/accounts/vendors" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-semibold rounded-lg shadow-sm hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm">
            <i className="fas fa-store"></i> Add Vendor
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Entries</p>
          <p className="text-2xl font-bold text-gray-900">{entries.length}</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Debit</p>
          <p className="text-2xl font-bold text-green-600">
            ?{entries.reduce((sum, e) => sum + Number(e.debit || 0), 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border-l-4 border-red-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Credit</p>
          <p className="text-2xl font-bold text-red-600">
            ?{entries.reduce((sum, e) => sum + Number(e.credit || 0), 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border-l-4 border-purple-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Net (Dr - Cr)</p>
          <p className="text-2xl font-bold text-purple-600">
            ?{(entries.reduce((sum, e) => sum + Number(e.debit || 0), 0) - entries.reduce((sum, e) => sum + Number(e.credit || 0), 0)).toFixed(2)}
          </p>
        </div>
      </div>

      <div className="flex gap-4 border-b border-gray-200 mb-6 overflow-x-auto">
        <button onClick={() => setActiveTab("daybook")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 ${activeTab === "daybook" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <i className="fas fa-book-open mr-2"></i>Day Book
        </button>
        <button onClick={() => setActiveTab("create")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 ${activeTab === "create" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <i className="fas fa-plus-circle mr-2"></i>Add Account
        </button>
        <button onClick={() => setActiveTab("chart")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 ${activeTab === "chart" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <i className="fas fa-layer-group mr-2"></i>Chart of Accounts
        </button>
      </div>

      {activeTab === "daybook" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
            <h2 className="font-semibold text-gray-800"><i className="fas fa-table mr-2 text-indigo-500"></i>Account Ledger Entries</h2>
          </div>
          {loading ? (
            <div className="p-10 text-center text-gray-500"><i className="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Loading entries...</p></div>
          ) : error ? (
            <div className="p-6 text-red-500">{error}</div>
          ) : entries.length === 0 ? (
            <div className="p-10 text-center text-gray-500">No entries found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-white border-b border-gray-200">
                    <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Account</th>
                    <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Debit (?)</th>
                    <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Credit (?)</th>
                    <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Ref</th>
                    <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {entries.map(entry => (
                    <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                      <td className="p-3 text-sm text-gray-600">{new Date(entry.created_at).toLocaleDateString()}</td>
                      <td className="p-3">
                        <p className="text-sm font-semibold text-gray-900">{entry.account_name}</p>
                        <span className="text-[10px] uppercase font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">{entry.entry_type}</span>
                      </td>
                      <td className="p-3 text-sm font-medium text-red-600 text-right">{entry.debit ? entry.debit.toFixed(2) : "-"}</td>
                      <td className="p-3 text-sm font-medium text-green-600 text-right">{entry.credit ? entry.credit.toFixed(2) : "-"}</td>
                      <td className="p-3 text-xs text-gray-500">{entry.reference_no || "-"}</td>
                      <td className="p-3">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded ${entry.status === "CONFIRMED" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>
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

      {activeTab === "create" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Add New Ledger Account</h2>
          <p className="text-gray-500 text-sm mb-6">Create a new account head in the Chart of Accounts.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Account Name *</label>
              <input type="text" className="w-full p-2 border border-gray-300 rounded focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" placeholder="e.g. Petty Cash" />
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Account Type *</label>
              <select className="w-full p-2 border border-gray-300 rounded focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
                <option value="CASH">Cash</option>
                <option value="BANK">Bank Account</option>
                <option value="EXPENSE">Expense</option>
                <option value="INCOME">Income</option>
              </select>
            </div>
          </div>
          <div className="mt-6">
            <button className="px-6 py-2 bg-indigo-600 text-white font-semibold rounded shadow hover:bg-indigo-700 transition-colors">
              Save Account
            </button>
          </div>
        </div>
      )}
      
      {activeTab === "chart" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-10 text-center text-gray-500">
          <i className="fas fa-layer-group text-4xl mb-3 text-gray-300"></i>
          <h3 className="text-lg font-semibold text-gray-900">Chart of Accounts</h3>
          <p className="mt-1">Displays all configured master accounts. Integrate full list API here.</p>
        </div>
      )}
    </div>
  );
}
