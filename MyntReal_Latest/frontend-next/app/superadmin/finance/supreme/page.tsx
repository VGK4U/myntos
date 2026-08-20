"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";
import { TrendingUp, TrendingDown, Wallet, Building2, Sun, Users, FileText, Send, RefreshCcw, PieChart } from "lucide-react";

export default function SupremeFinanceDashboard() {
  const { user, token } = useSuperAdminAuth();
  const [timeframe, setTimeframe] = useState("YTD");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/super-admin/finance/supreme-analytics`, {
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

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50 min-h-[calc(100vh-64px)]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Supreme Finance</h1>
          <p className="text-sm text-slate-500 mt-1">Master Financial Overview & Executive Ledger</p>
        </div>
        <div className="flex items-center bg-white rounded-md border border-slate-200 p-1 shadow-sm">
          {['MTD', 'QTD', 'YTD'].map((t) => (
            <button 
              key={t}
              onClick={() => setTimeframe(t)} 
              className={`px-4 py-1.5 text-sm font-medium rounded transition-colors ${timeframe === t ? 'bg-slate-900 text-white shadow' : 'bg-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-100'}`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900"></div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-l-4 border-l-blue-500 bg-white shadow-sm p-6">
              <h3 className="text-sm font-medium text-slate-500 mb-2">Total Gross Revenue</h3>
              <div className="text-3xl font-bold text-slate-900 mb-2">{data?.metrics?.[0]?.value || '₹ 0'}</div>
              <div className="inline-flex items-center text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                <TrendingUp className="mr-1 h-3 w-3" /> {data?.metrics?.[0]?.trend || '0%'} vs Last Year
              </div>
            </div>

            <div className="rounded-xl border border-l-4 border-l-rose-500 bg-white shadow-sm p-6">
              <h3 className="text-sm font-medium text-slate-500 mb-2">Total Payouts / Expenses</h3>
              <div className="text-3xl font-bold text-slate-900 mb-2">{data?.metrics?.[1]?.value || '₹ 0'}</div>
              <div className="inline-flex items-center text-xs font-semibold text-rose-600 bg-rose-50 px-2 py-1 rounded-full">
                <TrendingUp className="mr-1 h-3 w-3" /> {data?.metrics?.[1]?.trend || '0%'} vs Last Year
              </div>
            </div>

            <div className="rounded-xl border border-l-4 border-l-amber-500 bg-white shadow-sm p-6">
              <h3 className="text-sm font-medium text-slate-500 mb-2">Net Profit</h3>
              <div className="text-3xl font-bold text-slate-900 mb-2">{data?.metrics?.[2]?.value || '₹ 0'}</div>
              <div className="inline-flex items-center text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                <TrendingDown className="mr-1 h-3 w-3" /> {data?.metrics?.[2]?.trend || '0%'} vs Last Year
              </div>
            </div>

            <div className="rounded-xl border border-l-4 border-l-emerald-500 bg-slate-900 shadow-sm p-6 relative overflow-hidden">
              <Wallet className="absolute right-[-10px] bottom-[-10px] h-32 w-32 text-slate-800 opacity-50" />
              <div className="relative z-10">
                <h3 className="text-sm font-medium text-slate-400 mb-2">Net Profit Margin</h3>
                <div className="text-3xl font-bold text-white mb-2">{data?.net_profit_margin || '0'}%</div>
                <div className="text-xs font-semibold text-emerald-400">{data?.runway_months || '0'} Months Runway</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            <div className="rounded-xl border bg-white shadow-sm flex flex-col p-6">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
                <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                  <PieChart className="h-5 w-5 text-slate-400" /> Revenue Sources (YTD)
                </h3>
              </div>
              
              <div className="flex-1 flex flex-col justify-center space-y-8">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-slate-700 flex items-center gap-2"><Building2 className="h-4 w-4 text-blue-500" /> Real Estate Sales</span>
                    <span className="font-bold text-slate-900">₹ 3.2Cr <span className="text-slate-400 font-normal ml-1">(71%)</span></span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: '71%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-slate-700 flex items-center gap-2"><Sun className="h-4 w-4 text-amber-500" /> Solar Installations</span>
                    <span className="font-bold text-slate-900">₹ 85.5L <span className="text-slate-400 font-normal ml-1">(19%)</span></span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full bg-amber-500 rounded-full" style={{ width: '19%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="font-medium text-slate-700 flex items-center gap-2"><Users className="h-4 w-4 text-purple-500" /> Vendor Partnerships</span>
                    <span className="font-bold text-slate-900">₹ 44.5L <span className="text-slate-400 font-normal ml-1">(10%)</span></span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full bg-purple-500 rounded-full" style={{ width: '10%' }}></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-xl border bg-white shadow-sm flex flex-col">
              <div className="p-6 border-b border-slate-100 bg-slate-50/50 rounded-t-xl">
                <h3 className="font-semibold text-slate-900">Financial Operations</h3>
              </div>
              
              <div className="p-6 flex flex-col gap-4">
                <button className="flex items-center text-left p-4 rounded-xl border border-slate-200 hover:border-blue-500 hover:shadow-md transition-all group">
                  <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-blue-50 text-blue-600 mr-4 shrink-0">
                    <FileText className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-900">Generate Master Audit Report</h4>
                    <p className="text-sm text-slate-500 mt-1">Export full PDF ledger for external auditors.</p>
                  </div>
                </button>

                <button className="flex items-center text-left p-4 rounded-xl border border-slate-200 hover:border-rose-500 hover:shadow-md transition-all group">
                  <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-rose-50 text-rose-600 mr-4 shrink-0">
                    <Send className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-900">Process Bulk Payouts</h4>
                    <p className="text-sm text-slate-500 mt-1">Initiate NEFT/RTGS transfers for all pending withdrawals.</p>
                  </div>
                </button>

                <button className="flex items-center text-left p-4 rounded-xl border border-slate-200 hover:border-emerald-500 hover:shadow-md transition-all group">
                  <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-emerald-50 text-emerald-600 mr-4 shrink-0">
                    <RefreshCcw className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-900">Reconcile Bank Statements</h4>
                    <p className="text-sm text-slate-500 mt-1">Upload CSV from bank to auto-match internal ledger.</p>
                  </div>
                </button>
              </div>
            </div>

          </div>
        </>
      )}
    </div>
  );
}
