"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";
import { Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface IncomeTransaction {
  id: number;
  transaction_id: string;
  member_id: string;
  member_name: string;
  source: string; // REFERRAL, VENDOR_COMMISSION, BONUS
  amount: number;
  date: string;
  status: string; // CREDITED, PENDING, REVERSED
}

export default function VGKIncomePage() {
  const { token } = useStaffAuth();
  const [transactions, setTransactions] = useState<IncomeTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    
    const fetchIncome = async () => {
      try {
        setLoading(true);
        // Generic endpoint for Staff to view VGK Income/Transactions
        const res = await fetch(`${getApiUrl()}/api/v1/staff/vgk/income`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setTransactions(data.items || []);
        } else {
          setTransactions([]);
        }
      } catch (err) {
        console.warn("Failed to fetch income data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchIncome();
  }, [token]);

  const revenueData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
    datasets: [
      {
        label: 'Total Platform Commission (₹)',
        data: [45000, 52000, 48000, 61000, 59000, 72000, 85000],
        borderColor: 'rgba(99, 102, 241, 1)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        tension: 0.4,
        fill: true,
      }
    ],
  };

  const distributionData = {
    labels: ['Referrals', 'Vendor Commissions', 'Bonuses'],
    datasets: [
      {
        data: [45, 40, 15],
        backgroundColor: [
          'rgba(99, 102, 241, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(245, 158, 11, 0.8)'
        ],
        borderWidth: 0,
      }
    ]
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">VGK Income & Earnings</h1>
          <p className="text-sm text-gray-500 mt-2">Monitor network commissions, referral payouts, and platform revenue.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/vgk/members" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-users mr-2"></i> Members
          </Link>
          <button className="px-4 py-2 bg-green-600 text-white font-medium rounded-lg shadow-sm hover:bg-green-700 transition-colors">
            <i className="fas fa-file-invoice-dollar mr-2"></i> Process Payouts
          </button>
        </div>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <div>
            <p className="text-sm font-bold text-gray-500 uppercase">Platform Revenue (MTD)</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">₹ 2,45,000</p>
          </div>
          <div className="mt-4 flex items-center text-sm font-medium text-green-600">
            <i className="fas fa-arrow-up mr-1"></i> 12.5% vs last month
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <div>
            <p className="text-sm font-bold text-gray-500 uppercase">Total Member Payouts (MTD)</p>
            <p className="text-3xl font-bold text-indigo-600 mt-2">₹ 1,82,500</p>
          </div>
          <div className="mt-4 flex items-center text-sm font-medium text-gray-500">
            74% of revenue distributed
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between">
          <div>
            <p className="text-sm font-bold text-gray-500 uppercase">Pending Withdrawals</p>
            <p className="text-3xl font-bold text-amber-500 mt-2">₹ 45,200</p>
          </div>
          <div className="mt-4 flex items-center text-sm font-medium text-amber-600 cursor-pointer hover:underline">
            View 42 requests <i className="fas fa-chevron-right ml-1 text-xs"></i>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Platform Commission Growth</h2>
          <div className="h-64">
            <Line 
              data={revenueData} 
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                  y: { beginAtZero: true, grid: { color: '#f3f4f6' } },
                  x: { grid: { display: false } }
                }
              }} 
            />
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col items-center justify-center">
          <h2 className="text-lg font-bold text-gray-900 mb-4 w-full text-left">Payout Distribution</h2>
          <div className="w-48 h-48 relative">
            <Doughnut 
              data={distributionData}
              options={{
                cutout: '75%',
                plugins: { legend: { display: false } }
              }}
            />
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
              <span className="text-sm font-bold text-gray-500 block">Total</span>
              <span className="text-xl font-bold text-gray-900">100%</span>
            </div>
          </div>
          <div className="w-full mt-6 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="flex items-center text-gray-600"><span className="w-3 h-3 rounded-full bg-indigo-500 mr-2"></span>Referrals</span>
              <span className="font-bold">45%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="flex items-center text-gray-600"><span className="w-3 h-3 rounded-full bg-emerald-500 mr-2"></span>Vendor Comms</span>
              <span className="font-bold">40%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="flex items-center text-gray-600"><span className="w-3 h-3 rounded-full bg-amber-500 mr-2"></span>Bonuses</span>
              <span className="font-bold">15%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <h2 className="font-bold text-gray-900">Recent Network Transactions</h2>
          <button className="text-sm font-medium text-indigo-600 hover:text-indigo-800">View All</button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-2xl mb-3 text-indigo-500"></i>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Transaction ID & Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Member</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Source</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {transactions.map(txn => (
                  <tr key={txn.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-mono text-gray-900">{txn.transaction_id}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{new Date(txn.date).toLocaleString()}</p>
                    </td>
                    <td className="p-4">
                      <p className="text-sm font-medium text-indigo-600">{txn.member_name}</p>
                      <p className="text-xs text-gray-500">{txn.member_id}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
                        txn.source === "REFERRAL" ? "border-blue-200 bg-blue-50 text-blue-700" :
                        txn.source === "VENDOR_COMMISSION" ? "border-green-200 bg-green-50 text-green-700" : 
                        "border-amber-200 bg-amber-50 text-amber-700"
                      }`}>
                        {txn.source.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-sm font-bold text-green-600">+ ₹ {txn.amount.toLocaleString()}</span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        txn.status === "CREDITED" ? "bg-green-100 text-green-800" :
                        txn.status === "PENDING" ? "bg-amber-100 text-amber-800" : 
                        "bg-red-100 text-red-800"
                      }`}>
                        {txn.status}
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
