"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function IncentivesDashboardPage() {
  const { hasRole } = useStaffAuth();
  const [activeTab, setActiveTab] = useState("overview");

  const [stats, setStats] = useState({
    totalPoints: 0,
    redeemed: 0,
    balance: 0,
    rank: 0,
    currencyValue: 0
  });
  const [history, setHistory] = useState<any[]>([]);
  const { token } = useStaffAuth();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchIncentives = async () => {
      try {
        setLoading(true);
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/staff/hr/incentives`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.stats) setStats(data.stats);
          if (data.history) setHistory(data.history);
        }
      } catch (err) {
        console.warn("Failed to fetch incentives", err);
      } finally {
        setLoading(false);
      }
    };
    fetchIncentives();
  }, [token]);

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">MyntReal Incentives</h1>
          <p className="text-sm text-gray-500 mt-2">Track your reward points, commission bonuses, and redeem them for perks.</p>
        </div>
        <div className="flex space-x-3">
          {hasRole(['HR', 'ADMIN']) && (
            <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
              <i className="fas fa-check-double mr-2"></i> Approvals
            </button>
          )}
          <button className="px-4 py-2 bg-gradient-to-r from-yellow-500 to-amber-600 text-white font-medium rounded-lg shadow-sm hover:from-yellow-600 hover:to-amber-700 transition-colors">
            <i className="fas fa-gift mr-2"></i> Redeem Points
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 shrink-0">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Available Balance</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-3xl font-bold text-gray-900">{stats.balance}</h3>
              <span className="text-sm font-medium text-gray-500">Pts</span>
            </div>
            <p className="text-sm text-green-600 font-medium mt-1">Value: ₹ {stats.currencyValue}</p>
          </div>
          <div className="w-16 h-16 bg-amber-50 rounded-full flex items-center justify-center text-amber-500 text-2xl shadow-inner border border-amber-100">
            <i className="fas fa-coins"></i>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Lifetime Earned</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-3xl font-bold text-gray-900">{stats.totalPoints}</h3>
              <span className="text-sm font-medium text-gray-500">Pts</span>
            </div>
            <p className="text-sm text-indigo-600 font-medium mt-1">{stats.redeemed} points redeemed</p>
          </div>
          <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-500 text-2xl shadow-inner border border-indigo-100">
            <i className="fas fa-chart-line"></i>
          </div>
        </div>

        <div className="bg-gradient-to-br from-indigo-900 to-purple-900 p-6 rounded-xl shadow-lg flex items-center justify-between text-white relative overflow-hidden">
          <i className="fas fa-trophy absolute right-[-20px] bottom-[-20px] text-8xl opacity-10"></i>
          <div className="relative z-10">
            <p className="text-xs font-bold text-indigo-200 uppercase tracking-wider mb-1">Leaderboard Rank</p>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-2xl font-medium text-indigo-200">#</span>
              <h3 className="text-4xl font-bold text-white">{stats.rank}</h3>
            </div>
            <p className="text-sm text-indigo-100">Top 10% of sales team</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="flex space-x-6 px-6 pt-4 shrink-0 border-b border-gray-200">
          <button 
            onClick={() => setActiveTab("overview")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'overview' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            Points History
          </button>
          <button 
            onClick={() => setActiveTab("how_to_earn")}
            className={`pb-3 font-medium text-sm transition-colors border-b-2 ${activeTab === 'how_to_earn' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            How to Earn
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-0">
          {activeTab === "overview" && (
            <table className="w-full text-left">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr className="border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Description</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {history.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-medium text-gray-900">
                      {new Date(entry.date).toLocaleDateString()}
                    </td>
                    <td className="p-4">
                      <div className="flex items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-3 ${entry.type === 'CREDIT' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                          <i className={`fas ${entry.type === 'CREDIT' ? 'fa-arrow-down' : 'fa-arrow-up'}`}></i>
                        </div>
                        <p className="text-sm font-medium text-gray-900">{entry.source}</p>
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <span className={`text-sm font-bold ${entry.type === 'CREDIT' ? 'text-green-600' : 'text-red-600'}`}>
                        {entry.type === 'CREDIT' ? '+' : ''}{entry.points} Pts
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {activeTab === "how_to_earn" && (
            <div className="p-8 max-w-3xl">
              <h2 className="text-xl font-bold text-gray-900 mb-6 pb-2 border-b border-gray-100">Incentive Structure</h2>
              
              <div className="space-y-6">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-green-50 text-green-600 rounded-xl flex items-center justify-center text-xl shrink-0 border border-green-100">
                    <i className="fas fa-handshake"></i>
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">Real Estate Sales</h3>
                    <p className="text-sm text-gray-600 mt-1 mb-2">Convert leads into confirmed bookings for VGK Builders properties.</p>
                    <span className="inline-block bg-gray-100 text-gray-800 text-xs font-bold px-3 py-1 rounded">50 - 200 Pts per booking</span>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-yellow-50 text-yellow-600 rounded-xl flex items-center justify-center text-xl shrink-0 border border-yellow-100">
                    <i className="fas fa-solar-panel"></i>
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">Solar Installations</h3>
                    <p className="text-sm text-gray-600 mt-1 mb-2">Successfully close a solar panel installation contract.</p>
                    <span className="inline-block bg-gray-100 text-gray-800 text-xs font-bold px-3 py-1 rounded">30 Pts per KW installed</span>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center text-xl shrink-0 border border-blue-100">
                    <i className="fas fa-store-alt"></i>
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">VGK Vendor Onboarding</h3>
                    <p className="text-sm text-gray-600 mt-1 mb-2">Bring new businesses into the VGK Partnership network.</p>
                    <span className="inline-block bg-gray-100 text-gray-800 text-xs font-bold px-3 py-1 rounded">20 Pts per vendor</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
