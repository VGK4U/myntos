"use client";

import React, { useState } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";

export default function SuperAdminExpensesPage() {
  const { user } = useSuperAdminAuth();

  const expenses = [
    { id: 'EXP-1011', description: 'Server Hosting (AWS)', amount: 45000, date: '2026-08-01', category: 'IT Infrastructure', payee: 'Amazon Web Services', status: 'PAID' },
    { id: 'EXP-1012', description: 'Office Rent - Head Office', amount: 250000, date: '2026-08-05', category: 'Facilities', payee: 'Prestige Estates', status: 'PAID' },
    { id: 'EXP-1013', description: 'Staff Travel Claims (July)', amount: 85400, date: '2026-08-10', category: 'Operations', payee: 'Internal Transfer', status: 'PENDING_APPROVAL' },
    { id: 'EXP-1014', description: 'Meta Ads Budget (August)', amount: 500000, date: '2026-08-12', category: 'Marketing', payee: 'Facebook Ireland Ltd.', status: 'PAID' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Expense Ledgers</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Track & Approve Company Outgoing Capital</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-yellow-600 text-white font-bold rounded shadow-sm hover:bg-yellow-700 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-plus mr-2"></i> Record Expense
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <div className="relative w-96">
            <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm"></i>
            <input 
              type="text" 
              placeholder="Search Payee, Description or ID..." 
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded text-sm focus:ring-1 focus:ring-yellow-500 outline-none"
            />
          </div>
          <div className="flex gap-2">
            <select className="border border-gray-300 rounded text-xs font-bold text-gray-600 uppercase tracking-wider px-3 py-2 outline-none">
              <option>Status: All</option>
              <option>Pending Approval</option>
              <option>Paid</option>
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-0">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">EXP ID / Date</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Payee / Description</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Category</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Amount</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Status & Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {expenses.map((exp, idx) => (
                <tr key={idx} className="hover:bg-yellow-50/30 transition-colors">
                  <td className="p-4">
                    <p className="font-mono text-xs font-bold text-gray-900">{exp.id}</p>
                    <p className="text-[10px] text-gray-500 mt-1 uppercase">{new Date(exp.date).toLocaleDateString()}</p>
                  </td>
                  <td className="p-4">
                    <p className="font-bold text-gray-900 text-sm">{exp.payee}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{exp.description}</p>
                  </td>
                  <td className="p-4">
                    <span className="bg-gray-100 text-gray-700 text-[10px] font-black px-2 py-1 rounded uppercase tracking-wider border border-gray-200">
                      {exp.category}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <span className="font-black text-red-600 text-lg">- ₹ {exp.amount.toLocaleString('en-IN')}</span>
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex flex-col items-end">
                      <span className={`text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider mb-2 ${
                        exp.status === 'PAID' ? 'bg-gray-200 text-gray-700' : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {exp.status.replace('_', ' ')}
                      </span>
                      {exp.status === 'PENDING_APPROVAL' && (
                        <button className="text-[10px] font-bold text-green-600 hover:text-green-700 uppercase tracking-wider border border-green-600 px-2 py-1 rounded">
                          Approve Release
                        </button>
                      )}
                    </div>
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
