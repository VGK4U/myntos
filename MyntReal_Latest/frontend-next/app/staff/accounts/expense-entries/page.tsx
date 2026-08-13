"use client";

import { useState } from "react";

export default function ExpenseEntries() {
  const [activeTab, setActiveTab] = useState("all");

  const expenses = [
    { id: "EXP-4091", date: "Aug 13, 2026", category: "Marketing", payee: "Meta Platforms Inc", amount: "₹45,000", status: "Cleared", method: "Bank Transfer" },
    { id: "EXP-4090", date: "Aug 12, 2026", category: "Office Supplies", payee: "Staples India", amount: "₹12,500", status: "Pending", method: "Credit Card" },
    { id: "EXP-4089", date: "Aug 10, 2026", category: "Travel", payee: "MakeMyTrip", amount: "₹85,000", status: "Cleared", method: "Bank Transfer" },
    { id: "EXP-4088", date: "Aug 09, 2026", category: "Utilities", payee: "TSSPDCL", amount: "₹34,200", status: "Cleared", method: "Auto-Debit" },
    { id: "EXP-4087", date: "Aug 05, 2026", category: "Repairs", payee: "Urban Company", amount: "₹8,000", status: "Rejected", method: "Petty Cash" },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Expense Entries</h1>
          <p className="text-sm text-gray-500 mt-1">Record, track, and categorize company expenditures.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-5 py-2.5 bg-brand-warning text-white rounded-lg text-sm font-bold shadow-md shadow-brand-warning/20 hover:bg-amber-600 transition-colors">
            <i className="fas fa-plus mr-2"></i> Record Expense
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Total Expenses (This Month)</p>
          <h3 className="text-2xl font-bold text-gray-900">₹1,84,700</h3>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Pending Clearance</p>
          <h3 className="text-2xl font-bold text-amber-600">₹12,500</h3>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-sm font-medium text-gray-500 mb-1">Top Category</p>
          <h3 className="text-2xl font-bold text-gray-900">Marketing</h3>
        </div>
      </div>

      {/* Tabs & Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <nav className="flex space-x-8">
          {["all", "pending", "cleared", "rejected"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors capitalize -mb-[17px]
                ${activeTab === tab
                  ? "border-brand-warning text-brand-warning"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"}
              `}
            >
              {tab}
            </button>
          ))}
        </nav>
        
        <div className="relative w-full md:w-64">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <i className="fas fa-search text-gray-400"></i>
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-gray-200 rounded-lg leading-5 bg-white placeholder-gray-400 focus:outline-none focus:ring-brand-warning focus:border-brand-warning sm:text-sm transition-colors shadow-sm"
            placeholder="Search payee or ID..."
          />
        </div>
      </div>

      {/* Expenses Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Expense ID</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Category</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Payee</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Payment Method</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {expenses.map((expense, idx) => (
                <tr key={idx} className="hover:bg-gray-50/50 transition-colors group">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-brand-warning">{expense.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{expense.date}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2.5 py-1 bg-gray-100 text-gray-600 rounded text-xs font-medium border border-gray-200">
                      {expense.category}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{expense.payee}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{expense.method}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right font-mono font-bold text-gray-900">{expense.amount}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      expense.status === 'Cleared' ? 'bg-emerald-100 text-emerald-800' :
                      expense.status === 'Pending' ? 'bg-amber-100 text-amber-800' :
                      'bg-rose-100 text-rose-800'
                    }`}>
                      {expense.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="text-gray-400 hover:text-brand-warning transition-colors" title="View Receipt">
                        <i className="fas fa-receipt"></i>
                      </button>
                      <button className="text-gray-400 hover:text-gray-900 transition-colors" title="Edit">
                        <i className="fas fa-edit"></i>
                      </button>
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
