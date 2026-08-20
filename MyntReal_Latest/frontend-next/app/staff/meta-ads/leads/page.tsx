"use client";

import React, { useState } from 'react';
import { 
  UsersRound, 
  Download, 
  Search, 
  Filter, 
  MoreHorizontal,
  Mail,
  Phone,
  Clock
} from 'lucide-react';

export default function LeadsPage() {
  const [loading, setLoading] = useState(false);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white shadow-md shadow-emerald-500/20">
              <UsersRound className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">Lead Gen Forms</h1>
          </div>
          <p className="text-gray-500">View and export leads captured from your Meta Lead Generation campaigns.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 transition-colors shadow-sm">
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-100 flex flex-col sm:flex-row gap-4 justify-between items-center bg-gray-50/30">
          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search leads by name or email..." 
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all"
            />
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <select className="flex-1 sm:flex-none px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500">
              <option>All Campaigns</option>
              <option>Summer Special</option>
              <option>Luxury Villas</option>
            </select>
            <button className="flex-1 sm:flex-none items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors flex">
              <Filter className="w-4 h-4" />
              More Filters
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50/80 text-gray-500 font-medium border-b border-gray-100">
              <tr>
                <th className="px-6 py-4">Lead Info</th>
                <th className="px-6 py-4">Campaign Source</th>
                <th className="px-6 py-4">Date Captured</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[1, 2, 3, 4, 5].map((item) => (
                <tr key={item} className="hover:bg-gray-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">Lead User {item}</div>
                    <div className="flex items-center gap-3 mt-1">
                      <div className="flex items-center text-xs text-gray-500">
                        <Mail className="w-3 h-3 mr-1" />
                        user{item}@example.com
                      </div>
                      <div className="flex items-center text-xs text-gray-500">
                        <Phone className="w-3 h-3 mr-1" />
                        +91 98765 {item}432
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-gray-900">Summer Special - Plots</div>
                    <div className="text-xs text-gray-500 mt-0.5">Form: Main_Lead_Gen_v2</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center text-gray-600">
                      <Clock className="w-3.5 h-3.5 mr-1.5 text-gray-400" />
                      Oct {item + 10}, 2023
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200/50">
                      New
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors">
                      <MoreHorizontal className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="p-4 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500 bg-gray-50/30">
          <div>Showing 1 to 5 of 124 leads</div>
          <div className="flex gap-1">
            <button className="px-3 py-1 border border-gray-200 bg-white rounded-md hover:bg-gray-50 disabled:opacity-50">Previous</button>
            <button className="px-3 py-1 border border-gray-200 bg-white rounded-md hover:bg-gray-50 disabled:opacity-50">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
