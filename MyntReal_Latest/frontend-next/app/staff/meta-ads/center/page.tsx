"use client";

import React from 'react';
import { 
  Megaphone, 
  MousePointerClick, 
  Eye, 
  Activity,
  ArrowUpRight,
  LineChart,
  BarChart2
} from 'lucide-react';

export default function CenterPage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Megaphone className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Ads Center</h1>
          </div>
          <p className="text-gray-500">Centralized hub for all your active ad accounts, delivery statuses, and top-level metrics.</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm">
            Last 30 Days
          </button>
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm">
            Sync Meta Data
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: "Total Reach", value: "842,500", icon: Eye, color: "text-blue-600", bg: "bg-blue-50" },
          { title: "Link Clicks", value: "24,103", icon: MousePointerClick, color: "text-indigo-600", bg: "bg-indigo-50" },
          { title: "CTR", value: "2.86%", icon: Activity, color: "text-purple-600", bg: "bg-purple-50" },
          { title: "Conversions", value: "482", icon: BarChart2, color: "text-emerald-600", bg: "bg-emerald-50" }
        ].map((metric, i) => (
          <div key={i} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-medium text-gray-500 mb-1">{metric.title}</p>
                <h3 className="text-2xl font-bold text-gray-900">{metric.value}</h3>
              </div>
              <div className={`p-2 rounded-lg ${metric.bg}`}>
                <metric.icon className={`w-5 h-5 ${metric.color}`} />
              </div>
            </div>
            <div className="mt-4 flex items-center text-sm">
              <ArrowUpRight className="w-4 h-4 text-emerald-500 mr-1" />
              <span className="text-emerald-600 font-medium">+15.2%</span>
              <span className="text-gray-400 ml-2">vs last period</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <LineChart className="w-5 h-5 text-indigo-500" />
              Performance Overview
            </h3>
          </div>
          <div className="flex-1 bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-center min-h-[300px]">
            <p className="text-gray-400 font-medium flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Chart visualization goes here
            </p>
          </div>
        </div>

        <div className="lg:col-span-1 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-bold text-gray-900 mb-6">Active Ad Accounts</h3>
          <div className="space-y-4">
            {[
              { name: "MyntReal Hyderabad", status: "Active", spend: "$4,250", balance: "Prepaid" },
              { name: "MyntReal Bangalore", status: "Active", spend: "$1,840", balance: "Prepaid" },
              { name: "MyntReal Commercial", status: "Warning", spend: "$520", balance: "Low Balance" }
            ].map((account, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-lg border border-gray-100 bg-gray-50/50 hover:bg-gray-50 transition-colors">
                <div>
                  <div className="font-medium text-gray-900">{account.name}</div>
                  <div className="text-xs text-gray-500 mt-1">Spend: {account.spend} • {account.balance}</div>
                </div>
                <div className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                  account.status === 'Active' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                }`}>
                  {account.status}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
