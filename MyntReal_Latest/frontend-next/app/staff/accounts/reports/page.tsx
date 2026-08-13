"use client";

import { useState } from "react";

export default function FinancialReportsDashboard() {
  const [dateRange, setDateRange] = useState("This Month");

  const metrics = [
    { label: "Total Revenue", value: "₹45,23,500", trend: "+12.5%", status: "success", icon: "fa-rupee-sign" },
    { label: "Accounts Receivable", value: "₹12,45,000", trend: "+2.1%", status: "warning", icon: "fa-file-invoice-dollar" },
    { label: "Accounts Payable", value: "₹8,30,200", trend: "-5.4%", status: "success", icon: "fa-money-bill-transfer" },
    { label: "Cash in Hand", value: "₹5,10,000", trend: "Stable", status: "neutral", icon: "fa-wallet" },
  ];

  const recentTransactions = [
    { id: "TXN-8091", date: "Aug 13, 2026", description: "Client Payment - Royal Estates Plot 45", type: "Credit", amount: "₹5,00,000", status: "Completed" },
    { id: "TXN-8090", date: "Aug 12, 2026", description: "Vendor Payment - Marketing Ads", type: "Debit", amount: "₹45,000", status: "Completed" },
    { id: "TXN-8089", date: "Aug 12, 2026", description: "Staff Salary Disbursement", type: "Debit", amount: "₹18,50,000", status: "Processing" },
    { id: "TXN-8088", date: "Aug 11, 2026", description: "VGK Commission Payout", type: "Debit", amount: "₹2,15,000", status: "Completed" },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Financial Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Macro-level overview of MyntReal's financial health.</p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium focus:ring-brand-warning focus:border-brand-warning shadow-sm"
          >
            <option>This Week</option>
            <option>This Month</option>
            <option>Last Month</option>
            <option>This Quarter</option>
            <option>Financial Year</option>
          </select>
          <button className="px-5 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-bold shadow-md shadow-gray-900/20 hover:bg-black transition-colors">
            <i className="fas fa-file-export mr-2"></i> Export PDF
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
        {metrics.map((metric, idx) => (
          <div key={idx} className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-all group relative overflow-hidden">
             <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <i className={`fas ${metric.icon} text-6xl`}></i>
             </div>
             <div className="relative z-10">
                <div className="flex justify-between items-start mb-4">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white shadow-sm ${
                    metric.status === "success" ? "bg-emerald-500" :
                    metric.status === "warning" ? "bg-amber-500" :
                    "bg-blue-500"
                  }`}>
                    <i className={`fas ${metric.icon}`}></i>
                  </div>
                  <span className={`text-xs font-bold px-2 py-1 rounded-full ${
                    metric.trend.startsWith('+') ? 'bg-emerald-50 text-emerald-700' :
                    metric.trend.startsWith('-') ? 'bg-rose-50 text-rose-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {metric.trend}
                  </span>
                </div>
                <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">{metric.label}</h4>
                <p className="text-3xl font-extrabold text-gray-900 mt-1">{metric.value}</p>
             </div>
          </div>
        ))}
      </div>

      {/* Charts & Graphs Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex flex-col min-h-[350px]">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Revenue vs Expenses</h3>
          <div className="flex-1 bg-gray-50 border border-dashed border-gray-200 rounded-lg flex items-center justify-center">
             <div className="text-center">
               <i className="fas fa-chart-bar text-4xl text-gray-300 mb-3"></i>
               <p className="text-sm text-gray-500 font-medium">Bar Chart Visualization</p>
             </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex flex-col min-h-[350px]">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Cash Flow Analysis</h3>
          <div className="flex-1 bg-gray-50 border border-dashed border-gray-200 rounded-lg flex items-center justify-center">
             <div className="text-center">
               <i className="fas fa-chart-area text-4xl text-gray-300 mb-3"></i>
               <p className="text-sm text-gray-500 font-medium">Area Chart Visualization</p>
             </div>
          </div>
        </div>
      </div>

      {/* Recent Transactions Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 flex justify-between items-center bg-gray-50/50">
          <h3 className="text-lg font-bold text-gray-900">Recent Transactions</h3>
          <a href="/staff/accounts/general-ledger" className="text-sm font-bold text-brand-warning hover:text-amber-600 transition-colors">
            View Ledger <i className="fas fa-arrow-right ml-1"></i>
          </a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white border-b border-gray-100">
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Transaction ID</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Description</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recentTransactions.map((txn) => (
                <tr key={txn.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-brand-warning">{txn.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{txn.date}</td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{txn.description}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-bold ${
                      txn.type === 'Credit' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}>
                      {txn.type === 'Credit' ? <i className="fas fa-arrow-down mr-1"></i> : <i className="fas fa-arrow-up mr-1"></i>}
                      {txn.type}
                    </span>
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm font-bold text-right ${
                    txn.type === 'Credit' ? 'text-emerald-600' : 'text-gray-900'
                  }`}>{txn.amount}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      txn.status === 'Completed' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {txn.status}
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
