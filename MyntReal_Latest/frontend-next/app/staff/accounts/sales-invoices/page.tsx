"use client";

import { useState } from "react";

export default function SalesInvoices() {
  const [activeStatus, setActiveStatus] = useState("all");

  const invoices = [
    { id: "INV-2026-001", client: "Vikram Reddy", project: "Royal Estates", amount: "₹5,00,000", issueDate: "Aug 10, 2026", dueDate: "Aug 17, 2026", status: "Paid" },
    { id: "INV-2026-002", client: "Sunita Sharma", project: "Green Valley V", amount: "₹2,50,000", issueDate: "Aug 11, 2026", dueDate: "Aug 18, 2026", status: "Pending" },
    { id: "INV-2026-003", client: "Arjun Kumar", project: "Royal Estates", amount: "₹10,00,000", issueDate: "Aug 01, 2026", dueDate: "Aug 08, 2026", status: "Overdue" },
    { id: "INV-2026-004", client: "Meera Patel", project: "Mynt City", amount: "₹1,25,000", issueDate: "Aug 12, 2026", dueDate: "Aug 19, 2026", status: "Draft" },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Sales Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">Manage client billing, payments, and generated invoices.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-5 py-2.5 bg-brand-warning text-white rounded-lg text-sm font-bold shadow-md shadow-brand-warning/20 hover:bg-amber-600 transition-colors">
            <i className="fas fa-file-invoice mr-2"></i> Create Invoice
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-gray-500">Total Issued</p>
            <i className="fas fa-file-invoice text-gray-300"></i>
          </div>
          <h3 className="text-2xl font-bold text-gray-900">₹18,75,000</h3>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-gray-500">Collected</p>
            <i className="fas fa-check-circle text-emerald-300"></i>
          </div>
          <h3 className="text-2xl font-bold text-emerald-600">₹5,00,000</h3>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-gray-500">Pending</p>
            <i className="fas fa-clock text-amber-300"></i>
          </div>
          <h3 className="text-2xl font-bold text-amber-600">₹2,50,000</h3>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-semibold text-gray-500">Overdue</p>
            <i className="fas fa-exclamation-circle text-rose-300"></i>
          </div>
          <h3 className="text-2xl font-bold text-rose-600">₹10,00,000</h3>
        </div>
      </div>

      {/* Filters & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <nav className="flex space-x-8">
          {["all", "paid", "pending", "overdue", "draft"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveStatus(tab)}
              className={`
                whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors capitalize -mb-[17px]
                ${activeStatus === tab
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
            placeholder="Search invoice or client..."
          />
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Invoice No.</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Client & Project</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Issue Date</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Due Date</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((invoice, idx) => (
                <tr key={idx} className="hover:bg-gray-50/50 transition-colors group">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm font-bold text-brand-warning">{invoice.id}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-bold text-gray-900">{invoice.client}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{invoice.project}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{invoice.issueDate}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{invoice.dueDate}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right font-mono font-bold text-gray-900">{invoice.amount}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                      invoice.status === 'Paid' ? 'bg-emerald-100 text-emerald-800' :
                      invoice.status === 'Pending' ? 'bg-amber-100 text-amber-800' :
                      invoice.status === 'Overdue' ? 'bg-rose-100 text-rose-800' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {invoice.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="text-gray-400 hover:text-brand-warning transition-colors" title="Download PDF">
                        <i className="fas fa-download"></i>
                      </button>
                      <button className="text-gray-400 hover:text-gray-900 transition-colors" title="More Options">
                        <i className="fas fa-ellipsis-v"></i>
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
