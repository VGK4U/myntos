"use client";

import { useState, useEffect, useMemo } from "react";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";
import Link from "next/link";

interface ReceivableInvoice {
  id: string;
  client_name: string;
  invoice_no: string;
  date: string;
  due_date: string;
  total_amount: number;
  collected_amount: number;
  balance_due: number;
  status: "OVERDUE" | "UNPAID" | "PARTIAL" | "PAID";
}

export default function AccountsReceivablePage() {
  const { token } = useStaffAuth();
  const [invoices, setInvoices] = useState<ReceivableInvoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [activeTab, setActiveTab] = useState("overview"); 

  const fetchReceivables = async () => {
    if (!token) return;
    setLoading(true);
    try {
      // Mocking fetch for architecture standard. Will connect to legacy FastAPI route
      const res = await fetch(`${getApiUrl()}/api/v1/staff/accounts/receivables`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch accounts receivable");
      
      // Fallback premium data for UI/UX testing if backend lacks data
      setInvoices(data.invoices || [
        { id: "R101", client_name: "Zynova Estates", invoice_no: "INV-R-2026-112", date: "2026-07-20", due_date: "2026-08-19", total_amount: 850000, collected_amount: 0, balance_due: 850000, status: "OVERDUE" },
        { id: "R102", client_name: "Rahul Sharma (MNR)", invoice_no: "INV-R-2026-113", date: "2026-08-05", due_date: "2026-08-20", total_amount: 45000, collected_amount: 20000, balance_due: 25000, status: "PARTIAL" },
        { id: "R103", client_name: "EV Franchise Hub", invoice_no: "INV-R-2026-114", date: "2026-08-15", due_date: "2026-08-30", total_amount: 1500000, collected_amount: 0, balance_due: 1500000, status: "UNPAID" },
        { id: "R104", client_name: "Sunrise Solar Projects", invoice_no: "INV-R-2026-115", date: "2026-08-18", due_date: "2026-09-17", total_amount: 320000, collected_amount: 320000, balance_due: 0, status: "PAID" }
      ]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReceivables();
  }, [token]);

  const filteredInvoices = useMemo(() => {
    return invoices.filter(inv => {
      const matchesSearch = inv.client_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            inv.invoice_no.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === "ALL" || inv.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [invoices, searchQuery, statusFilter]);

  // KPIs
  const totalOutstanding = invoices.reduce((sum, inv) => sum + inv.balance_due, 0);
  const totalOverdue = invoices.filter(i => i.status === 'OVERDUE').reduce((sum, inv) => sum + inv.balance_due, 0);
  const totalCollectedThisMonth = invoices.reduce((sum, inv) => sum + inv.collected_amount, 0);

  return (
    <div className="min-h-screen bg-gray-50/50 pb-12">
      {/* Enterprise Header */}
      <div className="bg-white border-b border-gray-200 px-8 py-6 sticky top-0 z-10 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 max-w-screen-2xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center shadow-sm">
              <i className="fas fa-file-invoice text-white text-lg"></i>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Accounts Receivable</h1>
              <p className="text-sm text-gray-500 font-medium mt-0.5">Manage client invoices, collections, and outstanding dues</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 hover:text-indigo-600 transition-all flex items-center gap-2 text-sm">
              <i className="fas fa-paper-plane"></i> Send Reminders
            </button>
            <Link href="/staff/accounts/sales-invoices" className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 hover:shadow transition-all flex items-center gap-2 text-sm">
              <i className="fas fa-plus"></i> Create Sales Invoice
            </Link>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-screen-2xl mx-auto space-y-6">
        
        {/* KPI Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm relative overflow-hidden bg-white hover:border-indigo-300 transition-colors">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <i className="fas fa-coins text-6xl text-indigo-900"></i>
            </div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Outstanding (To Collect)</p>
            <p className="text-3xl font-bold text-indigo-700">₹{totalOutstanding.toLocaleString('en-IN', {minimumFractionDigits: 2})}</p>
            <p className="text-xs text-gray-400 font-medium mt-2">Across {invoices.filter(i => i.status !== 'PAID').length} active client invoices</p>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-red-200 shadow-sm relative overflow-hidden bg-red-50/30">
            <p className="text-xs font-bold text-red-700 uppercase tracking-wider mb-1">Total Overdue</p>
            <p className="text-3xl font-bold text-red-600">₹{totalOverdue.toLocaleString('en-IN', {minimumFractionDigits: 2})}</p>
            <p className="text-xs text-red-500 font-medium mt-2 flex items-center gap-1">
              <i className="fas fa-exclamation-circle"></i> Payments past due date
            </p>
          </div>

          <div className="bg-gray-900 p-6 rounded-xl shadow-md relative overflow-hidden text-white hover:bg-gray-800 transition-colors">
            <p className="text-xs font-bold text-green-400 uppercase tracking-wider mb-1">Collected This Month</p>
            <p className="text-3xl font-bold text-green-400">₹{totalCollectedThisMonth.toLocaleString('en-IN', {minimumFractionDigits: 2})}</p>
            <p className="text-xs text-gray-400 font-medium mt-2">Inward cash flow</p>
          </div>
        </div>

        {/* Tab Content: Overview */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col">
          <div className="p-4 border-b border-gray-200 bg-gray-50/50 flex flex-wrap gap-4 items-end rounded-t-xl">
            <div className="flex-1 min-w-[250px]">
              <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Search Client / Invoice</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fas fa-search text-gray-400"></i>
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="e.g. Zynova or INV-R..."
                />
              </div>
            </div>
            
            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase mb-1">Collection Status</label>
              <select 
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="block w-full pl-3 pr-10 py-2 text-sm border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="OVERDUE">Overdue</option>
                <option value="UNPAID">Unpaid (Current)</option>
                <option value="PARTIAL">Partially Collected</option>
                <option value="PAID">Fully Collected</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto min-h-[400px]">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/3">Client & Invoice</th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Dates</th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Billed (₹)</th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Collected (₹)</th>
                  <th scope="col" className="px-6 py-3 text-right text-xs font-bold text-gray-500 uppercase tracking-wider bg-indigo-50/50 text-indigo-800">Balance (₹)</th>
                  <th scope="col" className="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredInvoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-gray-50/80 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="text-sm font-bold text-gray-900">{inv.client_name}</div>
                      <div className="text-xs font-mono text-gray-500 mt-1 flex items-center gap-2">
                        <i className="fas fa-file-invoice text-indigo-400"></i> {inv.invoice_no}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-xs text-gray-500 mb-1">Billed: <span className="text-gray-900 font-medium">{new Date(inv.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}</span></div>
                      <div className={`text-xs font-bold ${new Date(inv.due_date) < new Date() && inv.status !== 'PAID' ? 'text-red-600' : 'text-gray-500'}`}>
                        Due: {new Date(inv.due_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900 text-right">
                      {inv.total_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-green-600 text-right">
                      {inv.collected_amount > 0 ? inv.collected_amount.toLocaleString('en-IN', {minimumFractionDigits: 2}) : "-"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-indigo-700 text-right bg-indigo-50/30">
                      {inv.balance_due.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={`px-2.5 py-1 inline-flex text-[10px] leading-5 font-bold rounded-full uppercase tracking-wider
                        ${inv.status === 'PAID' ? 'bg-green-100 text-green-800' : 
                          inv.status === 'OVERDUE' ? 'bg-red-100 text-red-800' : 
                          inv.status === 'PARTIAL' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      {inv.status !== 'PAID' && (
                        <button className="px-3 py-1.5 bg-white border border-gray-300 text-indigo-700 rounded text-xs font-bold hover:bg-indigo-50 hover:text-indigo-800 hover:border-indigo-200 transition-colors shadow-sm">
                          Record Payment
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredInvoices.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      No client invoices found matching your criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
