"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";
import { Search, Download, Filter, TrendingUp, Building2, Sun, Users } from "lucide-react";

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
          if (json.success) setData(json.data);
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
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50 min-h-[calc(100vh-64px)]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Company Revenue</h1>
          <p className="text-sm text-slate-500 mt-1">Incoming Cash Flow & Sales Ledgers</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-9 px-4 py-2 shadow">
            <Download className="mr-2 h-4 w-4" /> Export Ledger
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <div className="rounded-xl border bg-white text-slate-950 shadow-sm overflow-hidden flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 border-b gap-4 bg-slate-50/50">
            <div className="relative w-full sm:w-[350px]">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
              <input 
                type="text" 
                placeholder="Search by Transaction ID or Source..." 
                className="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 pl-9"
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <select className="flex h-9 w-full sm:w-auto rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 font-medium">
                <option>All Categories</option>
                <option>Real Estate</option>
                <option>Solar</option>
                <option>Vendor</option>
              </select>
            </div>
          </div>

          <div className="relative w-full overflow-auto">
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b">
                <tr className="border-b transition-colors hover:bg-slate-50">
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">TXN ID & Date</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Revenue Source</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Category</th>
                  <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Amount Received</th>
                  <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Status</th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {transactions.map((tx: any, idx: number) => (
                  <tr key={idx} className="border-b transition-colors hover:bg-blue-50/30">
                    <td className="p-6 align-middle">
                      <div className="font-mono font-medium text-slate-900">{tx.id}</div>
                      <div className="text-xs text-slate-500 mt-1">{new Date(tx.date).toLocaleDateString()}</div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="font-semibold text-slate-900">{tx.source}</div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800">
                        {tx.category === 'Real Estate' ? <Building2 className="h-3 w-3" /> : 
                         tx.category === 'Solar' ? <Sun className="h-3 w-3" /> : 
                         <Users className="h-3 w-3" />}
                        {tx.category || 'Revenue'}
                      </div>
                    </td>
                    <td className="p-6 align-middle text-right">
                      <div className="text-lg font-bold text-emerald-600">+ ₹ {tx.amount.toLocaleString('en-IN')}</div>
                    </td>
                    <td className="p-6 align-middle text-right">
                      <div className={`inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        tx.status === 'CLEARED' || tx.status.toLowerCase() === 'collected' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {tx.status.replace('_', ' ')}
                      </div>
                    </td>
                  </tr>
                ))}
                {transactions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-slate-500">
                      <TrendingUp className="mx-auto h-12 w-12 mb-4 opacity-20" />
                      <p className="text-lg font-medium text-slate-900">No revenue transactions found</p>
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
