"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";

export default function SuperAdminRevenuePage() {
  const { user, token } = useSuperAdminAuth();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    
    const fetchData = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/super-admin/finance/revenue`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const json = await res.json();
          if (json.success) {
            setData(json.data);
          }
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [token]);

  const transactions = data?.transactions || [];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Company Revenue</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Incoming Cash Flow & Sales Ledgers</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-blue-600 text-white font-bold rounded shadow-sm hover:bg-blue-700 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-file-download mr-2"></i> Export Ledger
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex justify-center items-center">
          <i className="fas fa-circle-notch fa-spin text-3xl text-gray-400"></i>
        </div>
      ) : (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <div className="relative w-96">
            <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm"></i>
            <input 
              type="text" 
              placeholder="Search by Transaction ID or Source..." 
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded text-sm focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div className="flex gap-2">
            <select className="border border-gray-300 rounded text-xs font-bold text-gray-600 uppercase tracking-wider px-3 py-2 outline-none">
              <option>All Categories</option>
              <option>Real Estate</option>
              <option>Solar</option>
              <option>Vendor</option>
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-0">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">TXN ID / Date</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Revenue Source</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Category</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Amount Received</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transactions.map((tx: any, idx: number) => (
                <tr key={idx} className="hover:bg-blue-50/30 transition-colors">
                  <td className="p-4">
                    <p className="font-mono text-xs font-bold text-gray-900">{tx.id}</p>
                    <p className="text-[10px] text-gray-500 mt-1 uppercase">{new Date(tx.date).toLocaleDateString()}</p>
                  </td>
                  <td className="p-4">
                    <p className="font-bold text-gray-900 text-sm">{tx.source}</p>
                  </td>
                  <td className="p-4">
                    <span className="bg-gray-100 text-gray-700 text-[10px] font-black px-2 py-1 rounded uppercase tracking-wider border border-gray-200">
                      {tx.category || 'Revenue'}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <span className="font-black text-green-600 text-lg">+ ₹ {tx.amount.toLocaleString('en-IN')}</span>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider ${
                      tx.status === 'CLEARED' || tx.status.toLowerCase() === 'collected' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {tx.status.replace('_', ' ')}
                    </span>
                  </td>
                </tr>
              ))}
              {transactions.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-gray-500 text-sm font-bold uppercase tracking-wider">
                    No transactions found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      )}
    </div>
  );
}
