"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";
import { IndianRupee, ArrowDownToLine, ArrowUpFromLine, Download, Plus, Landmark, History, Search } from "lucide-react";

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
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Cash Ledgers</h1>
          <p className="text-sm text-slate-500 mt-1">Physical Cash Intake & Dispersal</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-emerald-600 text-white hover:bg-emerald-700 h-9 px-4 py-2 shadow">
            <Plus className="mr-2 h-4 w-4" /> New Cash Entry
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border bg-slate-900 text-white shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-6 opacity-10">
                <Landmark className="h-24 w-24" />
              </div>
              <div className="p-6 relative z-10">
                <h3 className="text-slate-400 text-sm font-medium mb-2">Physical Vault Balance (HQ)</h3>
                <div className="text-4xl font-bold">₹ {(data?.vault_balance || 0).toLocaleString('en-IN')}</div>
                <div className="text-xs text-slate-500 mt-4 font-mono">Last reconciled: {data?.last_reconciled ? new Date(data.last_reconciled).toLocaleString() : 'N/A'}</div>
              </div>
            </div>
            <div className="rounded-xl border border-t-4 border-t-emerald-500 bg-white text-slate-950 shadow-sm">
              <div className="p-6">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-slate-500 text-sm font-medium">Cash In (MTD)</h3>
                  <ArrowDownToLine className="h-4 w-4 text-emerald-500" />
                </div>
                <div className="text-3xl font-bold">₹ {(data?.cash_in_mtd || 0).toLocaleString('en-IN')}</div>
              </div>
            </div>
            <div className="rounded-xl border border-t-4 border-t-rose-500 bg-white text-slate-950 shadow-sm">
              <div className="p-6">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-slate-500 text-sm font-medium">Cash Out (MTD)</h3>
                  <ArrowUpFromLine className="h-4 w-4 text-rose-500" />
                </div>
                <div className="text-3xl font-bold">₹ {(data?.cash_out_mtd || 0).toLocaleString('en-IN')}</div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border bg-white text-slate-950 shadow-sm overflow-hidden flex flex-col">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 border-b gap-4 bg-slate-50/50">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-slate-500" />
                <h3 className="font-semibold text-slate-800">Vault Transaction History</h3>
              </div>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Search entries..."
                    className="flex h-9 w-[200px] sm:w-[250px] rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 pl-9"
                  />
                </div>
                <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-slate-200 bg-white hover:bg-slate-100 hover:text-slate-900 h-9 px-4 py-2">
                  <Download className="mr-2 h-4 w-4" /> PDF Report
                </button>
              </div>
            </div>

            <div className="relative w-full overflow-auto">
              <table className="w-full caption-bottom text-sm">
                <thead className="[&_tr]:border-b">
                  <tr className="border-b transition-colors hover:bg-slate-50">
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Entry Details</th>
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Direction</th>
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Source / Reason</th>
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Handler</th>
                    <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Amount</th>
                  </tr>
                </thead>
                <tbody className="[&_tr:last-child]:border-0">
                  {transactions.map((tx: any, idx: number) => (
                    <tr key={idx} className="border-b transition-colors hover:bg-slate-50">
                      <td className="p-6 align-middle">
                        <div className="font-mono font-medium text-slate-900">{tx.id}</div>
                        <div className="text-xs text-slate-500 mt-1">{new Date(tx.date).toLocaleDateString()}</div>
                      </td>
                      <td className="p-6 align-middle">
                        <div className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          tx.type === 'IN' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                        }`}>
                          {tx.type}
                        </div>
                      </td>
                      <td className="p-6 align-middle">
                        <div className="font-medium text-slate-900">{tx.source}</div>
                      </td>
                      <td className="p-6 align-middle">
                        <div className="font-medium text-slate-700">{tx.handler}</div>
                        <div className="text-xs text-slate-500">{tx.location}</div>
                      </td>
                      <td className="p-6 align-middle text-right">
                        <div className={`text-base font-bold ${tx.type === 'IN' ? 'text-emerald-600' : 'text-slate-900'}`}>
                          {tx.type === 'IN' ? '+' : '-'} ₹ {tx.amount.toLocaleString()}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {transactions.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-12 text-center text-slate-500">
                        <History className="mx-auto h-12 w-12 mb-4 opacity-20" />
                        <p className="text-lg font-medium text-slate-900">No transactions recorded</p>
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
