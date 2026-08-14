"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMemberAuth } from "@/contexts/MemberAuthContext";

export default function DirectReferralsPage() {
  const { user } = useMemberAuth();

  const [searchTerm, setSearchTerm] = useState("");

  const directReferrals = [
    { id: 'VGK00214', name: 'Rahul Sharma', joinDate: '2026-07-15', status: 'ACTIVE', properties: 1, totalSales: 4500000, commissionEarned: 225000 },
    { id: 'VGK00388', name: 'Priya Desai', joinDate: '2026-07-22', status: 'ACTIVE', properties: 0, totalSales: 0, commissionEarned: 0 },
    { id: 'VGK00412', name: 'Vikram Singh', joinDate: '2026-08-01', status: 'INACTIVE', properties: 0, totalSales: 0, commissionEarned: 0 },
    { id: 'VGK00441', name: 'Anita Patel', joinDate: '2026-08-05', status: 'ACTIVE', properties: 2, totalSales: 8500000, commissionEarned: 425000 },
    { id: 'VGK00502', name: 'Sanjay Gupta', joinDate: '2026-08-10', status: 'ACTIVE', properties: 0, totalSales: 0, commissionEarned: 0 },
  ];

  const filteredReferrals = directReferrals.filter(ref => 
    ref.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    ref.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-80px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Direct Referrals</h1>
          <p className="text-sm text-gray-500 mt-2">Manage members who joined directly using your referral link and track your direct commissions.</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Invite Member
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 shrink-0">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="w-14 h-14 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center text-2xl shrink-0">
            <i className="fas fa-users"></i>
          </div>
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Directs</p>
            <h3 className="text-3xl font-bold text-gray-900">5</h3>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="w-14 h-14 bg-green-50 text-green-600 rounded-full flex items-center justify-center text-2xl shrink-0">
            <i className="fas fa-check-circle"></i>
          </div>
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Active Directs</p>
            <h3 className="text-3xl font-bold text-gray-900">4</h3>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center gap-4">
          <div className="w-14 h-14 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center text-2xl shrink-0">
            <i className="fas fa-hand-holding-usd"></i>
          </div>
          <div>
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">Total Direct Comm.</p>
            <h3 className="text-3xl font-bold text-gray-900">₹6.5L</h3>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
          <div className="relative w-72">
            <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
            <input 
              type="text" 
              placeholder="Search by Name or VGK ID..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-1 focus:ring-amber-500 outline-none"
            />
          </div>
          
          <button className="text-gray-500 hover:text-gray-700 px-3 py-1.5 border border-gray-300 rounded bg-white text-sm">
            <i className="fas fa-filter mr-2"></i> Filter
          </button>
        </div>

        <div className="flex-1 overflow-auto">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Member Details</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Join Date</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Properties Sold</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Commission Earned (5%)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredReferrals.map((ref, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center font-bold text-gray-600">
                        {ref.name.charAt(0)}
                      </div>
                      <div>
                        <p className="font-bold text-gray-900">{ref.name}</p>
                        <p className="text-xs text-gray-500 font-mono">{ref.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4 text-sm text-gray-600">
                    {new Date(ref.joinDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </td>
                  <td className="p-4">
                    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                      ref.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {ref.status}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className="font-bold text-gray-900">{ref.properties}</span>
                    <p className="text-[10px] text-gray-500 uppercase mt-1">₹ {(ref.totalSales/100000).toFixed(1)}L Volume</p>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`font-bold ${ref.commissionEarned > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                      ₹ {ref.commissionEarned > 0 ? ref.commissionEarned.toLocaleString('en-IN') : '0'}
                    </span>
                  </td>
                </tr>
              ))}
              
              {filteredReferrals.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-12 text-center text-gray-500">
                    <i className="fas fa-search text-4xl mb-3 text-gray-300"></i>
                    <p>No direct referrals found matching your search.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
