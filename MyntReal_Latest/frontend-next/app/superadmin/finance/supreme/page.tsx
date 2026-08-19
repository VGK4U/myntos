"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";

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
          if (json.success) {
            setData(json.data);
          }
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
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Supreme Finance</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Master Financial Overview & Executive Ledger</p>
        </div>
        <div className="flex space-x-2">
          <button onClick={() => setTimeframe('MTD')} className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded border ${timeframe === 'MTD' ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>MTD</button>
          <button onClick={() => setTimeframe('QTD')} className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded border ${timeframe === 'QTD' ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>QTD</button>
          <button onClick={() => setTimeframe('YTD')} className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded border ${timeframe === 'YTD' ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>YTD</button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex justify-center items-center">
          <i className="fas fa-circle-notch fa-spin text-3xl text-gray-400"></i>
        </div>
      ) : (
      <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 shrink-0">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-l-4 border-l-blue-600">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2">Total Gross Revenue</p>
          <h3 className="text-3xl font-black text-gray-900 mb-1">{data?.metrics?.[0]?.value || '₹ 0'}</h3>
          <p className="text-[10px] font-bold text-green-600 uppercase tracking-wider"><i className="fas fa-arrow-up mr-1"></i> {data?.metrics?.[0]?.trend || '0%'} vs Last Year</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-l-4 border-l-red-600">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2">Total Payouts / Expenses</p>
          <h3 className="text-3xl font-black text-gray-900 mb-1">{data?.metrics?.[1]?.value || '₹ 0'}</h3>
          <p className="text-[10px] font-bold text-red-600 uppercase tracking-wider"><i className="fas fa-arrow-up mr-1"></i> {data?.metrics?.[1]?.trend || '0%'} vs Last Year</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 border-l-4 border-l-yellow-500">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2">Net Profit</p>
          <h3 className="text-3xl font-black text-gray-900 mb-1">{data?.metrics?.[2]?.value || '₹ 0'}</h3>
          <p className="text-[10px] font-bold text-green-600 uppercase tracking-wider"><i className="fas fa-arrow-down mr-1"></i> {data?.metrics?.[2]?.trend || '0%'} vs Last Year</p>
        </div>

        <div className="bg-[#111827] p-6 rounded-lg shadow-lg border border-gray-800 border-l-4 border-l-green-500 relative overflow-hidden">
          <div className="absolute right-[-10px] bottom-[-10px] opacity-10">
            <i className="fas fa-piggy-bank text-7xl text-white"></i>
          </div>
          <div className="relative z-10">
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Net Profit Margin</p>
            <h3 className="text-3xl font-black text-white mb-1">{data?.net_profit_margin || '0'}%</h3>
            <p className="text-[10px] font-bold text-green-400 uppercase tracking-wider">{data?.runway_months || '0'} Months Runway</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        
        {/* Revenue Breakdown */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col p-6">
          <h3 className="text-sm font-black text-gray-900 uppercase tracking-widest mb-6 border-b border-gray-100 pb-2 flex justify-between">
            <span>Revenue Sources (YTD)</span>
            <i className="fas fa-chart-pie text-gray-400"></i>
          </h3>
          
          <div className="flex-1 flex flex-col justify-center">
            <div className="space-y-6">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-bold text-gray-700">Real Estate Sales</span>
                  <span className="font-black text-gray-900">₹ 3.2Cr (71%)</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3">
                  <div className="bg-blue-600 h-3 rounded-full" style={{ width: '71%' }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-bold text-gray-700">Solar Installations</span>
                  <span className="font-black text-gray-900">₹ 85.5L (19%)</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3">
                  <div className="bg-yellow-500 h-3 rounded-full" style={{ width: '19%' }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-bold text-gray-700">Vendor Partnerships</span>
                  <span className="font-black text-gray-900">₹ 44.5L (10%)</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3">
                  <div className="bg-purple-600 h-3 rounded-full" style={{ width: '10%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Action Center */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
            <h3 className="text-sm font-black text-gray-900 uppercase tracking-widest">Financial Operations</h3>
          </div>
          
          <div className="p-6 space-y-4">
            <div className="p-4 rounded-lg border border-gray-200 hover:border-blue-500 hover:shadow-md transition-all cursor-pointer group flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-blue-50 rounded text-blue-600 flex items-center justify-center text-xl mr-4">
                  <i className="fas fa-file-invoice"></i>
                </div>
                <div>
                  <h4 className="font-bold text-gray-900">Generate Master Audit Report</h4>
                  <p className="text-xs text-gray-500 mt-1">Export full PDF ledger for external auditors.</p>
                </div>
              </div>
              <i className="fas fa-chevron-right text-gray-300 group-hover:text-blue-500"></i>
            </div>

            <div className="p-4 rounded-lg border border-gray-200 hover:border-red-500 hover:shadow-md transition-all cursor-pointer group flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-red-50 rounded text-red-600 flex items-center justify-center text-xl mr-4">
                  <i className="fas fa-money-check-alt"></i>
                </div>
                <div>
                  <h4 className="font-bold text-gray-900">Process Bulk Payouts</h4>
                  <p className="text-xs text-gray-500 mt-1">Initiate NEFT/RTGS transfers for all pending withdrawals.</p>
                </div>
              </div>
              <i className="fas fa-chevron-right text-gray-300 group-hover:text-red-500"></i>
            </div>

            <div className="p-4 rounded-lg border border-gray-200 hover:border-green-500 hover:shadow-md transition-all cursor-pointer group flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-green-50 rounded text-green-600 flex items-center justify-center text-xl mr-4">
                  <i className="fas fa-university"></i>
                </div>
                <div>
                  <h4 className="font-bold text-gray-900">Reconcile Bank Statements</h4>
                  <p className="text-xs text-gray-500 mt-1">Upload CSV from bank to auto-match internal ledger.</p>
                </div>
              </div>
              <i className="fas fa-chevron-right text-gray-300 group-hover:text-green-500"></i>
            </div>
          </div>
        </div>

      </div>
      </>
      )}
    </div>
  );
}
