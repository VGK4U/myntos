"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Invoice {
  id: number;
  invoice_number: string;
  date: string;
  due_date: string;
  party_name: string;
  total_amount: number;
  balance_due: number;
  status: string;
  type: "SALES" | "PURCHASE";
}

export default function InvoicesPage() {
  const { token } = useStaffAuth();
  const [activeTab, setActiveTab] = useState<"SALES" | "PURCHASE">("SALES");
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    
    // Fallback data in case the endpoint isn't fully ready yet
    const fetchInvoices = async () => {
      try {
        setLoading(true);
        // We'll hit the relevant backend endpoints (e.g. sales invoices or purchase invoices)
        // For demonstration we will fetch a mock unified endpoint or fallback empty
        const endpoint = activeTab === "SALES" 
          ? `${getApiUrl()}/api/v1/staff/accounts/sales/invoices`
          : `${getApiUrl()}/api/v1/staff/accounts/purchase/invoices`;
          
        const res = await fetch(endpoint, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setInvoices(data.items || []);
        } else {
          setInvoices([]); // Fallback to empty if 404
        }
      } catch (err: any) {
        console.warn(`Failed to fetch ${activeTab} invoices, using empty state`, err);
        setInvoices([]);
      } finally {
        setLoading(false);
      }
    };

    fetchInvoices();
  }, [token, activeTab]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Invoices</h1>
          <p className="text-sm text-gray-500 mt-2">Manage customer Sales Invoices and vendor Purchase Invoices.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/receivables" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-file-invoice-dollar mr-2"></i> Receivables
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Create Invoice
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-6 border-b border-gray-200 mb-6 overflow-x-auto">
        <button onClick={() => setActiveTab("SALES")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 flex items-center ${activeTab === "SALES" ? "border-indigo-600 text-indigo-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-2 ${activeTab === "SALES" ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-500"}`}>
            <i className="fas fa-file-invoice"></i>
          </div>
          Sales Invoices
        </button>
        <button onClick={() => setActiveTab("PURCHASE")} className={`pb-3 font-semibold text-sm transition-colors whitespace-nowrap border-b-2 flex items-center ${activeTab === "PURCHASE" ? "border-teal-600 text-teal-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-2 ${activeTab === "PURCHASE" ? "bg-teal-100 text-teal-600" : "bg-gray-100 text-gray-500"}`}>
            <i className="fas fa-shopping-cart"></i>
          </div>
          Purchase Invoices
        </button>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className={`p-4 border-b border-gray-100 flex justify-between items-center ${activeTab === 'SALES' ? 'bg-indigo-50/50' : 'bg-teal-50/50'}`}>
          <div className="flex items-center space-x-4">
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input type="text" placeholder={`Search ${activeTab.toLowerCase()} invoices...`} className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" />
            </div>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none">
              <option value="">All Statuses</option>
              <option value="PAID">Paid</option>
              <option value="UNPAID">Unpaid / Open</option>
              <option value="OVERDUE">Overdue</option>
            </select>
          </div>
          <button className="text-gray-500 hover:text-gray-700">
            <i className="fas fa-filter mr-1"></i> Filter
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className={`fas fa-spinner fa-spin text-3xl mb-3 ${activeTab === 'SALES' ? 'text-indigo-500' : 'text-teal-500'}`}></i>
            <p>Loading {activeTab.toLowerCase()} invoices...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : invoices.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${activeTab === 'SALES' ? 'bg-indigo-50 text-indigo-300' : 'bg-teal-50 text-teal-300'}`}>
              <i className={`fas ${activeTab === 'SALES' ? 'fa-file-invoice' : 'fa-shopping-cart'} text-2xl`}></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No {activeTab.toLowerCase()} invoices found</h3>
            <p className="text-gray-500 mb-4">There are currently no {activeTab.toLowerCase()} invoices in this view.</p>
            <button className={`px-4 py-2 font-medium rounded hover:opacity-90 transition-colors ${activeTab === 'SALES' ? 'bg-indigo-50 text-indigo-600' : 'bg-teal-50 text-teal-600'}`}>
              Create New {activeTab === 'SALES' ? 'Sales Invoice' : 'Purchase Invoice'}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Invoice No.</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Party / Customer</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Due Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Total Amount (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Balance Due (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {invoices.map(inv => (
                  <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm text-gray-600">{new Date(inv.date).toLocaleDateString()}</td>
                    <td className="p-4 text-sm font-medium text-gray-900">
                      <Link href={`/staff/accounts/invoices/${inv.id}`} className="hover:underline hover:text-indigo-600">
                        {inv.invoice_number}
                      </Link>
                    </td>
                    <td className="p-4">
                      <span className="text-sm font-semibold text-gray-900">{inv.party_name}</span>
                    </td>
                    <td className="p-4 text-sm text-gray-600">{new Date(inv.due_date).toLocaleDateString()}</td>
                    <td className="p-4 text-sm font-medium text-gray-900 text-right">{inv.total_amount.toFixed(2)}</td>
                    <td className="p-4 text-sm font-bold text-gray-900 text-right">{inv.balance_due.toFixed(2)}</td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        inv.status === "PAID" ? "bg-green-100 text-green-800" : 
                        inv.status === "UNPAID" ? "bg-gray-100 text-gray-800" :
                        "bg-red-100 text-red-800"
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
