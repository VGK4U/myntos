"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";

export default function MetaCampaignsPage() {
  const { hasRole } = useStaffAuth();
  
  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Campaign Manager</h1>
          <p className="text-sm text-gray-500 mt-2">Manage all active campaigns, ad sets, and ads linked to your Meta Business account.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/marketing/meta/dashboard" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-chart-pie mr-2 text-indigo-500"></i> Ads Overview
          </Link>
          <button className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg shadow-sm hover:bg-blue-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Create Campaign
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex flex-wrap gap-4 items-center justify-between">
          <div className="flex space-x-2">
            <button className="px-3 py-1.5 bg-white border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-50">
              <i className="fas fa-filter mr-1 text-gray-400"></i> Filter
            </button>
            <button className="px-3 py-1.5 bg-white border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-50">
              <i className="fas fa-calendar mr-1 text-gray-400"></i> Lifetime
            </button>
          </div>
          <div className="relative w-64">
            <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm"></i>
            <input 
              type="text" 
              placeholder="Search campaigns..." 
              className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded text-sm focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider w-10 text-center">
                  <input type="checkbox" className="rounded text-blue-600" />
                </th>
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Campaign Name</th>
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Delivery</th>
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Budget</th>
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Results</th>
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Reach</th>
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Cost per Result</th>
                <th className="p-3 text-xs font-bold text-gray-500 uppercase tracking-wider">Amount Spent</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {/* Campaign 1 */}
              <tr className="hover:bg-blue-50/30 transition-colors group cursor-pointer">
                <td className="p-3 text-center border-r border-gray-100">
                  <input type="checkbox" className="rounded text-blue-600" />
                </td>
                <td className="p-3 border-r border-gray-100">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    <p className="text-sm font-medium text-blue-700 hover:underline">VGK Builders - Monsoon Offer (FB)</p>
                  </div>
                  <div className="flex gap-2 mt-1 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-gray-500 font-medium">
                    <button className="hover:text-blue-600">View Charts</button> | 
                    <button className="hover:text-blue-600">Edit</button> | 
                    <button className="hover:text-blue-600">Duplicate</button>
                  </div>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-xs text-gray-700">Active</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-xs text-gray-700">₹2,000.00 / day</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <p className="text-sm font-medium text-gray-900">312</p>
                  <p className="text-[10px] text-gray-500">Leads</p>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-sm text-gray-700">45,800</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-sm text-gray-700">₹144.87</span>
                </td>
                <td className="p-3">
                  <span className="text-sm font-medium text-gray-900">₹45,200.00</span>
                </td>
              </tr>

              {/* Campaign 2 */}
              <tr className="hover:bg-blue-50/30 transition-colors group cursor-pointer">
                <td className="p-3 text-center border-r border-gray-100">
                  <input type="checkbox" className="rounded text-blue-600" />
                </td>
                <td className="p-3 border-r border-gray-100">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    <p className="text-sm font-medium text-blue-700 hover:underline">Solar Commercial Retargeting (IG)</p>
                  </div>
                  <div className="flex gap-2 mt-1 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-gray-500 font-medium">
                    <button className="hover:text-blue-600">View Charts</button> | 
                    <button className="hover:text-blue-600">Edit</button> | 
                    <button className="hover:text-blue-600">Duplicate</button>
                  </div>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-xs text-gray-700">Active</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-xs text-gray-700">₹1,500.00 / day</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <p className="text-sm font-medium text-gray-900">145</p>
                  <p className="text-[10px] text-gray-500">Leads</p>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-sm text-gray-700">22,100</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-sm text-gray-700">₹196.55</span>
                </td>
                <td className="p-3">
                  <span className="text-sm font-medium text-gray-900">₹28,500.00</span>
                </td>
              </tr>

              {/* Campaign 3 */}
              <tr className="bg-gray-50/50 hover:bg-gray-100/50 transition-colors group cursor-pointer opacity-75">
                <td className="p-3 text-center border-r border-gray-100">
                  <input type="checkbox" className="rounded text-blue-600" />
                </td>
                <td className="p-3 border-r border-gray-100">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-gray-400"></div>
                    <p className="text-sm font-medium text-blue-700 hover:underline">Generic Brand Awareness</p>
                  </div>
                  <div className="flex gap-2 mt-1 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] text-gray-500 font-medium">
                    <button className="hover:text-blue-600">View Charts</button> | 
                    <button className="hover:text-blue-600">Edit</button> | 
                    <button className="hover:text-blue-600">Duplicate</button>
                  </div>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-xs text-gray-500">Off</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-xs text-gray-500">₹5,000.00 / Lifetime</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <p className="text-sm font-medium text-gray-500">42</p>
                  <p className="text-[10px] text-gray-400">Leads</p>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-sm text-gray-500">18,400</span>
                </td>
                <td className="p-3 border-r border-gray-100">
                  <span className="text-sm text-gray-500">₹285.71</span>
                </td>
                <td className="p-3">
                  <span className="text-sm font-medium text-gray-500">₹12,000.00</span>
                </td>
              </tr>

            </tbody>
            {/* Totals row */}
            <tfoot className="bg-gray-100 font-bold sticky bottom-0">
              <tr>
                <td className="p-3 border-r border-gray-200"></td>
                <td className="p-3 border-r border-gray-200 text-sm text-gray-700">Results from 3 campaigns</td>
                <td className="p-3 border-r border-gray-200"></td>
                <td className="p-3 border-r border-gray-200"></td>
                <td className="p-3 border-r border-gray-200 text-sm text-gray-900">499 <span className="text-[10px] font-normal text-gray-500 ml-1">Leads</span></td>
                <td className="p-3 border-r border-gray-200 text-sm text-gray-900">86,300</td>
                <td className="p-3 border-r border-gray-200 text-sm text-gray-900">₹171.74 <span className="text-[10px] font-normal text-gray-500 ml-1">Per Lead</span></td>
                <td className="p-3 text-sm text-gray-900">₹85,700.00</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
