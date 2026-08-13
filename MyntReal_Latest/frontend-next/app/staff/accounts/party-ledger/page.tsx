"use client";

import { useState, useEffect } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";
import Link from "next/link";

interface PartyStatementEntry {
  id: number;
  date: string;
  voucher_no: string;
  particulars: string;
  debit: number;
  credit: number;
  balance: number;
}

export default function PartyLedgerPage() {
  const { token } = useStaffAuth();
  const [entries, setEntries] = useState<PartyStatementEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchLedger = async () => {
    // In a real implementation, we would pass party_id and date range
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/party-ledger`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch party ledger");
      setEntries(data.entries || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto animate-in fade-in zoom-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <i className="fas fa-users text-purple-600"></i>
            Party Ledger
          </h1>
          <p className="text-sm text-gray-500 mt-1">View account statements for Vendors, B2B Partners, and Customers.</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg shadow hover:bg-purple-700 transition-colors flex items-center gap-2 text-sm">
            <i className="fas fa-print"></i> Print Statement
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Select Party</label>
            <select className="w-full p-2 border border-gray-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500">
              <option value="">-- Choose Party --</option>
              {/* Dynamic list of parties will go here */}
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">From Date</label>
            <input type="date" className="w-full p-2 border border-gray-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500" />
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-700 uppercase mb-1">To Date</label>
            <input type="date" className="w-full p-2 border border-gray-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500" />
          </div>
          <div className="flex items-end">
            <button className="w-full px-4 py-2 bg-gray-900 text-white font-semibold rounded shadow hover:bg-black transition-colors">
              <i className="fas fa-search mr-2"></i> View Ledger
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h2 className="font-semibold text-gray-800">Statement of Account</h2>
        </div>
        
        {loading ? (
          <div className="p-10 text-center text-gray-500"><i className="fas fa-spinner fa-spin text-2xl mb-2"></i><p>Generating statement...</p></div>
        ) : error ? (
          <div className="p-10 text-center text-gray-500">
            <i className="fas fa-search text-3xl mb-3 text-gray-300"></i>
            <p>Select a party to view their ledger statement.</p>
          </div>
        ) : entries.length === 0 ? (
           <div className="p-10 text-center text-gray-500">No transactions found for the selected period.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white border-b border-gray-200">
                  <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Voucher No</th>
                  <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Particulars</th>
                  <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Debit (?)</th>
                  <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Credit (?)</th>
                  <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Balance (?)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {/* Simulated rows */}
                <tr className="hover:bg-gray-50">
                  <td className="p-3 text-sm text-gray-600">01/08/2026</td>
                  <td className="p-3 text-sm text-gray-900">-</td>
                  <td className="p-3 text-sm font-semibold text-gray-800">Opening Balance</td>
                  <td className="p-3 text-sm text-right">-</td>
                  <td className="p-3 text-sm text-right">5000.00</td>
                  <td className="p-3 text-sm font-bold text-right text-gray-900">5000.00 Cr</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
