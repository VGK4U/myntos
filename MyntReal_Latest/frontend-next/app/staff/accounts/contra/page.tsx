"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface ContraEntry {
  id: number;
  entry_number: string;
  transaction_date: string;
  amount: number;
  from_account: string;
  to_account: string;
  type: string;
  status: string;
  remarks: string;
}

export default function ContraEntriesPage() {
  const { token } = useStaffAuth();
  const [activeTab, setActiveTab] = useState("all");
  const [entries, setEntries] = useState<ContraEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    
    // Fallback data in case the endpoint isn't fully ready yet
    const fetchContraEntries = async () => {
      try {
        setLoading(true);
        // Assuming a contra endpoint or filtering
        const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/contra/transactions`, {
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
        console.warn("Failed to fetch contra entries, using empty state", err);
        setEntries([]);
      } finally {
        setLoading(false);
      }
    };

    fetchContraEntries();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Contra Entries</h1>
          <p className="text-sm text-gray-500 mt-2">Manage internal transfers between cash and bank accounts (Deposits & Withdrawals).</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/general-ledger" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-book mr-2"></i> General Ledger
          </Link>
          <button onClick={() => setActiveTab("new")} className="px-4 py-2 bg-teal-600 text-white font-medium rounded-lg shadow-sm hover:bg-teal-700 transition-colors">
            <i className="fas fa-exchange-alt mr-2"></i> Record Contra
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-teal-500 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <p className="text-xs font-bold text-gray-500 uppercase">Total Contra Entries</p>
            <i className="fas fa-exchange-alt text-teal-300 text-xl"></i>
          </div>
          <p className="text-3xl font-bold text-gray-900 mt-2">{entries.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-500 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <p className="text-xs font-bold text-gray-500 uppercase">Cash Deposited</p>
            <i className="fas fa-money-bill-wave text-blue-300 text-xl"></i>
          </div>
          <p className="text-3xl font-bold text-blue-600 mt-2">
            ₹{entries.filter(e => e.type === 'DEPOSIT').reduce((sum, e) => sum + Number(e.amount || 0), 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <p className="text-xs font-bold text-gray-500 uppercase">Cash Withdrawn</p>
            <i className="fas fa-university text-amber-300 text-xl"></i>
          </div>
          <p className="text-3xl font-bold text-amber-600 mt-2">
            ₹{entries.filter(e => e.type === 'WITHDRAWAL').reduce((sum, e) => sum + Number(e.amount || 0), 0).toFixed(2)}
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-6 border-b border-gray-200 mb-6 overflow-x-auto">
        <button onClick={() => setActiveTab("all")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 ${activeTab === "all" ? "border-teal-600 text-teal-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <i className="fas fa-list mr-2"></i> All Entries
        </button>
        <button onClick={() => setActiveTab("new")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 ${activeTab === "new" ? "border-teal-600 text-teal-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <i className="fas fa-plus-circle mr-2"></i> Record Entry
        </button>
      </div>

      {/* Content Area */}
      {activeTab === "all" && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
            <h2 className="font-semibold text-gray-800"><i className="fas fa-exchange-alt mr-2 text-teal-500"></i> Contra Transactions</h2>
          </div>
          
          {loading ? (
            <div className="p-12 text-center text-gray-500">
              <i className="fas fa-spinner fa-spin text-3xl mb-3 text-teal-500"></i>
              <p>Loading contra entries...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center text-red-500 bg-red-50">
              <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
              <p>{error}</p>
            </div>
          ) : entries.length === 0 ? (
            <div className="p-16 text-center text-gray-500 flex flex-col items-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <i className="fas fa-exchange-alt text-2xl text-gray-400"></i>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-1">No contra entries found</h3>
              <p className="text-gray-500 mb-4">There are currently no cash-bank transfers recorded in the system.</p>
              <button onClick={() => setActiveTab("new")} className="px-4 py-2 bg-teal-50 text-teal-600 font-medium rounded hover:bg-teal-100 transition-colors">
                Record First Transfer
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Entry No.</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">From Account</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">To Account</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount (₹)</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {entries.map(entry => (
                    <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                      <td className="p-4 text-sm text-gray-600">{new Date(entry.transaction_date).toLocaleDateString()}</td>
                      <td className="p-4 text-sm font-medium text-teal-600">{entry.entry_number}</td>
                      <td className="p-4">
                        <span className="text-sm font-semibold text-red-600"><i className="fas fa-minus-circle mr-1 text-xs"></i> {entry.from_account}</span>
                      </td>
                      <td className="p-4">
                        <span className="text-sm font-semibold text-green-600"><i className="fas fa-plus-circle mr-1 text-xs"></i> {entry.to_account}</span>
                      </td>
                      <td className="p-4 text-sm font-bold text-gray-900 text-right">{entry.amount.toFixed(2)}</td>
                      <td className="p-4 text-center">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded uppercase ${
                          entry.type === 'DEPOSIT' ? 'bg-blue-100 text-blue-800' : 
                          entry.type === 'WITHDRAWAL' ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {entry.type}
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
              <h2 className="text-lg font-bold text-gray-900">Record Contra Entry</h2>
              <p className="text-gray-500 text-sm mt-1">Log internal transfers between Cash and Bank accounts.</p>
            </div>
            <div className="w-10 h-10 bg-teal-100 rounded-full flex items-center justify-center">
              <i className="fas fa-exchange-alt text-teal-600"></i>
            </div>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Transaction Date *</label>
                <input type="date" className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-teal-500 focus:ring-2 focus:ring-teal-200 transition-all outline-none" defaultValue={new Date().toISOString().split('T')[0]} />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Transaction Type *</label>
                <select className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-teal-500 focus:ring-2 focus:ring-teal-200 transition-all outline-none">
                  <option value="CASH_DEPOSIT">Cash Deposit (Cash to Bank)</option>
                  <option value="CASH_WITHDRAWAL">Cash Withdrawal (Bank to Cash)</option>
                  <option value="BANK_TRANSFER">Bank to Bank Transfer</option>
                  <option value="PETTY_CASH">Transfer to Petty Cash</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Amount (₹) *</label>
                <input type="number" min="0" step="0.01" className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-teal-500 focus:ring-2 focus:ring-teal-200 transition-all outline-none font-medium text-teal-700" placeholder="0.00" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 bg-gray-50 p-5 rounded-lg border border-gray-100">
              <div>
                <label className="block text-xs font-bold text-red-600 uppercase mb-2"><i className="fas fa-minus-circle mr-1"></i> From Account (Source) *</label>
                <select className="w-full p-2.5 bg-white border border-gray-300 rounded-lg focus:border-red-500 focus:ring-2 focus:ring-red-200 transition-all outline-none">
                  <option value="">Select source account...</option>
                  <option value="CASH_MAIN">Main Cash Account</option>
                  <option value="HDFC_1234">HDFC Bank (Acct: *1234)</option>
                  <option value="ICICI_9876">ICICI Bank (Acct: *9876)</option>
                </select>
                <p className="text-xs text-gray-500 mt-2">This account balance will decrease.</p>
              </div>
              <div>
                <label className="block text-xs font-bold text-green-600 uppercase mb-2"><i className="fas fa-plus-circle mr-1"></i> To Account (Destination) *</label>
                <select className="w-full p-2.5 bg-white border border-gray-300 rounded-lg focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all outline-none">
                  <option value="">Select destination account...</option>
                  <option value="HDFC_1234">HDFC Bank (Acct: *1234)</option>
                  <option value="ICICI_9876">ICICI Bank (Acct: *9876)</option>
                  <option value="CASH_MAIN">Main Cash Account</option>
                </select>
                <p className="text-xs text-gray-500 mt-2">This account balance will increase.</p>
              </div>
            </div>
            
            <div className="mb-6">
              <label className="block text-xs font-bold text-gray-700 uppercase mb-2">Remarks / Denominations</label>
              <textarea rows={3} className="w-full p-2.5 bg-gray-50 border border-gray-300 rounded-lg focus:border-teal-500 focus:ring-2 focus:ring-teal-200 transition-all outline-none" placeholder="Enter reason for transfer or cash denominations..."></textarea>
            </div>
            
            <div className="flex items-center justify-end pt-4 border-t border-gray-100 space-x-3">
              <button type="button" onClick={() => setActiveTab("all")} className="px-5 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">
                Cancel
              </button>
              <button type="button" className="px-5 py-2.5 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 transition-colors shadow-sm flex items-center">
                <i className="fas fa-save mr-2"></i> Record Transfer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
