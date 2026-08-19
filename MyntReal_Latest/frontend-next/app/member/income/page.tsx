"use client";

import React, { useState, useEffect } from "react";
import { useMemberAuth } from "@/contexts/MemberAuthContext";
import api from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function MemberIncomePage() {
  const { user } = useMemberAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  
  const [totals, setTotals] = useState({
    lifetimeEarned: 0,
    direct: 0,
    matching: 0,
    other: 0
  });
  
  const [incomeHistory, setIncomeHistory] = useState<any[]>([]);

  useEffect(() => {
    if (!user || !user.mnr_id) return;

    const fetchFinancialData = async () => {
      try {
        setLoading(true);
        const res = await api.get(`/user/${user.mnr_id}/financial-summary`);
        if (res.data && res.data.success) {
          const summary = res.data.income_summary?.income_streams || {};
          const financialTotals = res.data.financial_totals || {};
          
          setTotals({
            lifetimeEarned: financialTotals.total_earned || res.data.income_summary?.total_monthly_income || 0,
            direct: summary.direct_referral?.total_income || 0,
            matching: summary.matching_referral?.total_income || 0,
            other: (summary.ved_income?.ved_amount || 0) + (summary.guru_dakshina?.guru_dakshina_amount || 0)
          });

          const txs = res.data.recent_transactions || [];
          setIncomeHistory(txs.map((tx: any) => ({
            id: tx.id || Math.random(),
            date: tx.date || tx.created_at || new Date().toISOString(),
            type: tx.transaction_type || 'Income',
            amount: Math.abs(tx.amount || 0),
            ref: tx.description || 'Reference',
            status: tx.status || 'CREDITED'
          })));
        }
      } catch (err) {
        console.error("Failed to fetch income data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchFinancialData();
  }, [user]);

  // Chart Data
  const monthlyData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Direct Income',
        data: [0, 0, 0, 0, 0, totals.direct],
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
      },
      {
        label: 'Matching Income',
        data: [0, 0, 0, 0, 0, totals.matching],
        backgroundColor: 'rgba(168, 85, 247, 0.5)',
      }
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
        ticks: { callback: (value: any) => '₹' + value / 1000 + 'k' }
      },
      x: { grid: { display: false } }
    },
    plugins: {
      legend: { position: 'top' as const },
    }
  };

  if (loading) {
    return (
      <div className="min-h-[calc(100vh-80px)] flex items-center justify-center">
        <i className="fas fa-circle-notch fa-spin text-3xl text-amber-500"></i>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Income & Earnings</h1>
          <p className="text-sm text-gray-500 mt-2">Track your direct, matching, and bonus earnings across the VGK Network.</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-file-invoice mr-2"></i> Download Tax Statement
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6 shrink-0">
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Lifetime Earned</p>
          <h3 className="text-2xl font-bold text-gray-900">₹ {totals.lifetimeEarned.toLocaleString('en-IN')}</h3>
        </div>
        <div className="bg-blue-50 p-5 rounded-xl shadow-sm border border-blue-100 flex flex-col justify-between">
          <p className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-1">Direct Commission</p>
          <h3 className="text-2xl font-bold text-blue-900">₹ {totals.direct.toLocaleString('en-IN')}</h3>
        </div>
        <div className="bg-purple-50 p-5 rounded-xl shadow-sm border border-purple-100 flex flex-col justify-between">
          <p className="text-xs font-bold text-purple-600 uppercase tracking-wider mb-1">Matching Bonus</p>
          <h3 className="text-2xl font-bold text-purple-900">₹ {totals.matching.toLocaleString('en-IN')}</h3>
        </div>
        <div className="bg-amber-50 p-5 rounded-xl shadow-sm border border-amber-100 flex flex-col justify-between">
          <p className="text-xs font-bold text-amber-600 uppercase tracking-wider mb-1">Other Bonuses</p>
          <h3 className="text-2xl font-bold text-amber-900">₹ {totals.other.toLocaleString('en-IN')}</h3>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="flex space-x-6 px-6 pt-4 shrink-0 border-b border-gray-200">
          <button 
            onClick={() => setActiveTab("overview")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'overview' ? 'border-amber-500 text-amber-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            Analytics Overview
          </button>
          <button 
            onClick={() => setActiveTab("history")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'history' ? 'border-amber-500 text-amber-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            Detailed Ledger
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 gap-6">
              <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <h3 className="font-bold text-gray-900 mb-4">6-Month Earnings Trend</h3>
                <div className="h-72 w-full">
                  <Bar data={monthlyData} options={chartOptions} />
                </div>
              </div>
            </div>
          )}

          {activeTab === "history" && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                <div className="flex space-x-2">
                  <select className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white outline-none focus:ring-1 focus:ring-amber-500">
                    <option>All Income Types</option>
                    <option>Direct Commission</option>
                    <option>Matching Bonus</option>
                    <option>Guru Dakshina</option>
                  </select>
                  <input type="month" className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white outline-none focus:ring-1 focus:ring-amber-500" />
                </div>
              </div>
              <table className="w-full text-left">
                <thead className="bg-white">
                  <tr className="border-b border-gray-200">
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Income Type</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Reference</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Amount</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {incomeHistory.length === 0 && (
                     <tr><td colSpan={5} className="p-4 text-center text-sm text-gray-500">No recent transactions found.</td></tr>
                  )}
                  {incomeHistory.map((row) => (
                    <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                      <td className="p-4 text-sm text-gray-900">{new Date(row.date).toLocaleDateString()}</td>
                      <td className="p-4 text-sm font-medium text-gray-900">{row.type}</td>
                      <td className="p-4 text-sm text-gray-500">{row.ref}</td>
                      <td className="p-4 text-sm font-bold text-green-600">+ ₹{row.amount.toLocaleString('en-IN')}</td>
                      <td className="p-4">
                        <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-1 rounded-full uppercase">
                          {row.status}
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
    </div>
  );
}
