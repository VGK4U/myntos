"use client";

import React, { useState } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";

export default function SuperAdminCashLedgerPage() {
  const { user } = useSuperAdminAuth();

  const transactions = [
    { id: 'CSH-0912', type: 'IN', source: 'Property Advance (Cash)', amount: 50000, date: '2026-08-14', handler: 'Ajay Clerk', location: 'HQ Chennai' },
    { id: 'CSH-0911', type: 'OUT', source: 'Petty Cash - Office Supplies', amount: 4500, date: '2026-08-13', handler: 'Srinivas', location: 'HQ Chennai' },
    { id: 'CSH-0910', type: 'IN', source: 'Site Visit Booking Fee', amount: 10000, date: '2026-08-13', handler: 'Rahul Agent', location: 'Site B' },
    { id: 'CSH-0909', type: 'OUT', source: 'Vendor Payment (Decor)', amount: 15000, date: '2026-08-11', handler: 'Ajay Clerk', location: 'HQ Chennai' },
  ];

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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 shrink-0">
        <div className="bg-[#111827] p-6 rounded-lg shadow-lg border border-gray-800">
          <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Physical Vault Balance (HQ)</p>
          <h3 className="text-4xl font-black text-white mt-1">₹ 4,25,500</h3>
          <p className="text-[10px] text-gray-500 font-mono mt-2">Last reconciled: Today, 09:00 AM</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-t-4 border-t-green-500">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">Cash In (MTD)</p>
          <h3 className="text-2xl font-black text-gray-900 mt-1">₹ 8,40,000</h3>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-t-4 border-t-red-500">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">Cash Out (MTD)</p>
          <h3 className="text-2xl font-black text-gray-900 mt-1">₹ 1,12,000</h3>
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
              {transactions.map((tx, idx) => (
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
                    <p className="font-bold text-gray-900 text-sm">{tx.source}</p>
                  </td>
                  <td className="p-4">
                    <p className="text-xs font-bold text-gray-700">{tx.handler}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5"><i className="fas fa-map-marker-alt mr-1"></i>{tx.location}</p>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`font-black text-lg ${tx.type === 'IN' ? 'text-green-600' : 'text-red-600'}`}>
                      {tx.type === 'IN' ? '+' : '-'} ₹ {tx.amount.toLocaleString('en-IN')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
