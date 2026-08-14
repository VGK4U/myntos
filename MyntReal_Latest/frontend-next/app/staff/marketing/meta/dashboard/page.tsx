"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function MetaAdsDashboardPage() {
  const { token } = useStaffAuth();
  
  // Mock data for Meta Ads Dashboard
  const metrics = {
    totalSpend: 145000,
    impressions: 1250400,
    clicks: 45200,
    cpc: 3.2,
    ctr: 3.6,
    leadsGen: 845,
    cpl: 171.6
  };

  return (
    <div className="p-6 max-w-7xl mx-auto h-[calc(100vh-80px)] flex flex-col">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Meta Ads Center</h1>
          <p className="text-sm text-gray-500 mt-2">Manage your Facebook & Instagram ad campaigns, track spend, and analyze CPL.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/marketing/meta/studio" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-magic mr-2 text-indigo-500"></i> Creative Studio
          </Link>
          <Link href="/staff/marketing/meta/campaigns" className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow-sm hover:bg-blue-700 transition-colors">
            <i className="fas fa-bullhorn mr-2"></i> Manage Campaigns
          </Link>
        </div>
      </div>

      <div className="bg-gradient-to-r from-blue-600 to-indigo-800 rounded-xl p-6 text-white mb-6 shrink-0 shadow-lg relative overflow-hidden">
        <i className="fab fa-meta absolute right-[-20px] bottom-[-40px] text-9xl opacity-20 transform -rotate-12"></i>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
              <i className="fab fa-facebook-f text-blue-600 text-xl"></i>
            </div>
            <div className="w-10 h-10 bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 rounded-full flex items-center justify-center">
              <i className="fab fa-instagram text-white text-xl"></i>
            </div>
            <h2 className="text-xl font-bold ml-2">MyntReal Advertising Account</h2>
            <span className="bg-green-500 text-white text-xs font-bold px-2 py-0.5 rounded-full uppercase ml-2">Active</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-blue-200 text-xs font-bold uppercase tracking-wider mb-1">Total Ad Spend (MTD)</p>
              <h3 className="text-3xl font-bold">₹ {(metrics.totalSpend / 1000).toFixed(1)}k</h3>
            </div>
            <div>
              <p className="text-blue-200 text-xs font-bold uppercase tracking-wider mb-1">Total Impressions</p>
              <h3 className="text-3xl font-bold">{(metrics.impressions / 1000000).toFixed(2)}M</h3>
            </div>
            <div>
              <p className="text-blue-200 text-xs font-bold uppercase tracking-wider mb-1">Leads Generated</p>
              <h3 className="text-3xl font-bold">{metrics.leadsGen}</h3>
            </div>
            <div>
              <p className="text-blue-200 text-xs font-bold uppercase tracking-wider mb-1">Cost Per Lead (CPL)</p>
              <h3 className="text-3xl font-bold">₹ {metrics.cpl}</h3>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 min-h-0">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col">
          <h3 className="font-bold text-gray-900 mb-4 border-b border-gray-100 pb-2">Performance Metrics</h3>
          <div className="flex-1 space-y-6 flex flex-col justify-center">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">Click-Through Rate (CTR)</span>
                <span className="text-sm font-bold text-indigo-600">{metrics.ctr}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-indigo-600 h-2 rounded-full" style={{ width: '65%' }}></div>
              </div>
              <p className="text-xs text-gray-500 mt-1">Industry avg: 1.2% - You are performing well.</p>
            </div>
            
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">Cost Per Click (CPC)</span>
                <span className="text-sm font-bold text-blue-600">₹ {metrics.cpc}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full" style={{ width: '40%' }}></div>
              </div>
            </div>
            
            <div className="pt-4 border-t border-gray-100">
              <button className="w-full py-2 bg-gray-50 text-gray-700 font-medium rounded-lg hover:bg-gray-100 transition-colors text-sm">
                View Detailed Reports
              </button>
            </div>
          </div>
        </div>

        <div className="md:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-0 flex flex-col">
          <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
            <h3 className="font-bold text-gray-900">Top Performing Campaigns</h3>
            <span className="text-xs text-gray-500 font-medium">Last 30 Days</span>
          </div>
          
          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase">Campaign Name</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase text-right">Spend</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase text-right">Leads</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase text-right">CPL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <p className="text-sm font-bold text-gray-900">VGK Builders - Monsoon Offer (FB)</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">Objective: Lead Generation</p>
                  </td>
                  <td className="p-4">
                    <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-1 rounded-full border border-green-200">ACTIVE</span>
                  </td>
                  <td className="p-4 text-right text-sm font-medium text-gray-700">₹ 45,200</td>
                  <td className="p-4 text-right text-sm font-bold text-indigo-600">312</td>
                  <td className="p-4 text-right text-sm font-medium text-gray-700">₹ 144</td>
                </tr>
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <p className="text-sm font-bold text-gray-900">Solar Commercial Retargeting (IG)</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">Objective: Conversions</p>
                  </td>
                  <td className="p-4">
                    <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-1 rounded-full border border-green-200">ACTIVE</span>
                  </td>
                  <td className="p-4 text-right text-sm font-medium text-gray-700">₹ 28,500</td>
                  <td className="p-4 text-right text-sm font-bold text-indigo-600">145</td>
                  <td className="p-4 text-right text-sm font-medium text-gray-700">₹ 196</td>
                </tr>
                <tr className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <p className="text-sm font-bold text-gray-900">Generic Brand Awareness</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">Objective: Reach</p>
                  </td>
                  <td className="p-4">
                    <span className="bg-gray-100 text-gray-600 text-[10px] font-bold px-2 py-1 rounded-full border border-gray-200">PAUSED</span>
                  </td>
                  <td className="p-4 text-right text-sm font-medium text-gray-700">₹ 12,000</td>
                  <td className="p-4 text-right text-sm font-bold text-indigo-600">42</td>
                  <td className="p-4 text-right text-sm font-medium text-gray-700">₹ 285</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="p-3 border-t border-gray-100 bg-gray-50 text-center">
            <Link href="/staff/marketing/meta/campaigns" className="text-sm text-indigo-600 font-medium hover:text-indigo-800">
              View All Campaigns <i className="fas fa-arrow-right ml-1"></i>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
