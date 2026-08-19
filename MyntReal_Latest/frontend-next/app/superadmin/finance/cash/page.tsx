"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";

export default function SuperAdminCashLedgerPage() {
  const { user, token } = useSuperAdminAuth();
  
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    
    const fetchData = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/super-admin/finance/cash-ledger`, {
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
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Cash Ledgers</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Physical Cash Intake & Dispersal</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-green-600 text-white font-bold rounded shadow-sm hover:bg-green-700 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-hand-holding-usd mr-2"></i> New Cash Entry
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex justify-center items-center">
          <i className="fas fa-circle-notch fa-spin text-3xl text-gray-400"></i>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 shrink-0">
            <div className="bg-[#111827] p-6 rounded-lg shadow-lg border border-gray-800">
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Physical Vault Balance (HQ)</p>
              <h3 className="text-4xl font-black text-white mt-1">₹ {data?.vault_balance?.toLocaleString('en-IN') || 0}</h3>
              <p className="text-[10px] text-gray-500 font-mono mt-2">Last reconciled: {data?.last_reconciled ? new Date(data.last_reconciled).toLocaleString() : 'N/A'}</p>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-t-4 border-t-green-500">
              <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">Cash In (MTD)</p>
              <h3 className="text-2xl font-black text-gray-900 mt-1">₹ {data?.cash_in_mtd?.toLocaleString('en-IN') || 0}</h3>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-t-4 border-t-red-500">
              <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">Cash Out (MTD)</p>
              <h3 className="text-2xl font-black text-gray-900 mt-1">₹ {data?.cash_out_mtd?.toLocaleString('en-IN') || 0}</h3>
            </div>
          </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Vault Transaction History</h3>
          <button className="text-gray-500 hover:text-gray-900 text-xs font-bold uppercase tracking-wider bg-white border border-gray-300 px-3 py-1.5 rounded">
            Download PDF Report
          </button>
        </div>

        <div className="flex-1 overflow-auto p-0">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Entry ID / Date</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Direction</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Source / Reason</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Handler</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transactions.map((tx: any, idx: number) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <p className="font-mono text-xs font-bold text-gray-900">{tx.id}</p>
                    <p className="text-[10px] text-gray-500 mt-1 uppercase">{new Date(tx.date).toLocaleDateString()}</p>
                  </td>
                  <td className="p-4">
                    <span className={`text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider ${
                      tx.type === 'IN' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {tx.type}
                    </span>
                  </td>
                  <td className="p-4">
                    <p className="text-xs font-bold text-gray-900">{tx.source}</p>
                  </td>
                  <td className="p-4 text-xs text-gray-500">
                    <p className="font-bold">{tx.handler}</p>
                    <p className="text-[10px] mt-0.5">{tx.location}</p>
                  </td>
                  <td className="p-4 text-right">
                    <p className={`text-sm font-black ${tx.type === 'IN' ? 'text-green-600' : 'text-gray-900'}`}>
                      {tx.type === 'IN' ? '+' : '-'} ₹ {tx.amount.toLocaleString()}
                    </p>
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
      </>
      )}
    </div>
  );
}
