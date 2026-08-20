"use client";

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  DollarSign, 
  Search, 
  Filter, 
  MoreHorizontal, 
  Plus, 
  ArrowUpRight,
  ArrowDownRight,
  Target
} from 'lucide-react';

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Mock data for presentation
  const mockCampaigns = [
    { id: '1', name: 'Summer Special - Plots', status: 'ACTIVE', spend: '$1,240.50', leads: 45, cpl: '$27.56', roas: '2.4x' },
    { id: '2', name: 'Luxury Villas Retargeting', status: 'PAUSED', spend: '$3,450.00', leads: 12, cpl: '$287.50', roas: '1.2x' },
    { id: '3', name: 'First-time Buyers Promo', status: 'ACTIVE', spend: '$890.25', leads: 34, cpl: '$26.18', roas: '3.1x' },
    { id: '4', name: 'Weekend Site Visit Push', status: 'ACTIVE', spend: '$450.00', leads: 8, cpl: '$56.25', roas: '1.8x' },
  ];

  useEffect(() => {
    // Simulate API fetch
    setTimeout(() => {
      setCampaigns(mockCampaigns);
      setLoading(false);
    }, 1000);
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Target className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Ad Campaigns</h1>
          </div>
          <p className="text-gray-500">Manage and optimize your Meta ad campaigns, ad sets, and creatives.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Create Campaign
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-1">Total Spend</p>
              <h3 className="text-2xl font-bold text-gray-900">$5,842.25</h3>
            </div>
            <div className="p-2 bg-blue-50 rounded-lg">
              <DollarSign className="w-5 h-5 text-blue-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center text-sm">
            <ArrowUpRight className="w-4 h-4 text-emerald-500 mr-1" />
            <span className="text-emerald-600 font-medium">+12.5%</span>
            <span className="text-gray-400 ml-2">vs last week</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-1">Total Leads</p>
              <h3 className="text-2xl font-bold text-gray-900">184</h3>
            </div>
            <div className="p-2 bg-emerald-50 rounded-lg">
              <Users className="w-5 h-5 text-emerald-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center text-sm">
            <ArrowUpRight className="w-4 h-4 text-emerald-500 mr-1" />
            <span className="text-emerald-600 font-medium">+24.1%</span>
            <span className="text-gray-400 ml-2">vs last week</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-1">Avg. Cost per Lead</p>
              <h3 className="text-2xl font-bold text-gray-900">$31.75</h3>
            </div>
            <div className="p-2 bg-purple-50 rounded-lg">
              <TrendingUp className="w-5 h-5 text-purple-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center text-sm">
            <ArrowDownRight className="w-4 h-4 text-emerald-500 mr-1" />
            <span className="text-emerald-600 font-medium">-4.2%</span>
            <span className="text-gray-400 ml-2">vs last week</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-sm font-medium text-gray-500 mb-1">Avg. ROAS</p>
              <h3 className="text-2xl font-bold text-gray-900">2.4x</h3>
            </div>
            <div className="p-2 bg-amber-50 rounded-lg">
              <BarChart3 className="w-5 h-5 text-amber-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center text-sm">
            <ArrowUpRight className="w-4 h-4 text-emerald-500 mr-1" />
            <span className="text-emerald-600 font-medium">+0.3x</span>
            <span className="text-gray-400 ml-2">vs last week</span>
          </div>
        </div>
      </div>

      {/* Main Table Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
        {/* Table Toolbar */}
        <div className="p-4 border-b border-gray-100 flex flex-col sm:flex-row gap-4 justify-between items-center bg-gray-50/30">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search campaigns..." 
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
            />
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <button className="flex-1 sm:flex-none items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors flex">
              <Filter className="w-4 h-4" />
              Filters
            </button>
            <button className="flex-1 sm:flex-none items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors flex">
              Status: All
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50/80 text-gray-500 font-medium border-b border-gray-100">
              <tr>
                <th className="px-6 py-4">Campaign Name</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Amount Spent</th>
                <th className="px-6 py-4">Leads</th>
                <th className="px-6 py-4">Cost per Lead</th>
                <th className="px-6 py-4">ROAS</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                [...Array(4)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-3/4"></div></td>
                    <td className="px-6 py-4"><div className="h-5 bg-gray-200 rounded-full w-16"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-1/2"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-1/4"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-1/2"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-1/3"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-8 ml-auto"></div></td>
                  </tr>
                ))
              ) : (
                campaigns.map((campaign) => (
                  <tr key={campaign.id} className="hover:bg-gray-50/50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900 group-hover:text-indigo-600 transition-colors cursor-pointer">{campaign.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">ID: {campaign.id} • Meta Ads</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        campaign.status === 'ACTIVE' 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/50' 
                          : 'bg-amber-50 text-amber-700 border border-amber-200/50'
                      }`}>
                        {campaign.status === 'ACTIVE' ? (
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span>
                        ) : (
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5"></span>
                        )}
                        {campaign.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-600 font-medium">{campaign.spend}</td>
                    <td className="px-6 py-4 text-gray-600">{campaign.leads}</td>
                    <td className="px-6 py-4 text-gray-600">{campaign.cpl}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <span className="text-gray-900 font-medium">{campaign.roas}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors">
                        <MoreHorizontal className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className="p-4 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500 bg-gray-50/30">
          <div>Showing 1 to 4 of 4 campaigns</div>
          <div className="flex gap-1">
            <button className="px-3 py-1 border border-gray-200 bg-white rounded-md hover:bg-gray-50 disabled:opacity-50">Previous</button>
            <button className="px-3 py-1 border border-gray-200 bg-white rounded-md hover:bg-gray-50 disabled:opacity-50">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
