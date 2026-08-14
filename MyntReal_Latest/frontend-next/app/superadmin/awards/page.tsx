"use client";

import React, { useState } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";

export default function SuperAdminAwardsPage() {
  const { user } = useSuperAdminAuth();

  const awards = [
    { id: 'AWD-001', memberId: 'VGK00214', memberName: 'Rahul Sharma', awardType: 'Gold Coin (10g)', requirement: '100 Directs', status: 'PENDING_PROCUREMENT', requestDate: '2026-08-10' },
    { id: 'AWD-002', memberId: 'VGK00441', memberName: 'Anita Patel', awardType: 'Tata Tiago EV', requirement: '25 Sales', status: 'READY_FOR_DELIVERY', requestDate: '2026-08-01' },
    { id: 'AWD-003', memberId: 'VGK00012', memberName: 'Meera Reddy', awardType: 'Platinum Trophy', requirement: '200 Directs', status: 'DELIVERED', requestDate: '2026-07-15' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Awards Procurement</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Manage fulfillment of physical member rewards and vehicles</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-indigo-600 text-white font-bold rounded shadow-sm hover:bg-indigo-700 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-plus mr-2"></i> Add Custom Reward
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6 shrink-0">
        <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
          <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Pending Procurement</p>
          <div className="flex justify-between items-end">
            <h3 className="text-3xl font-black text-gray-900">1</h3>
            <i className="fas fa-box-open text-2xl text-gray-300"></i>
          </div>
        </div>
        <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200 border-b-4 border-b-blue-500">
          <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Ready For Delivery</p>
          <div className="flex justify-between items-end">
            <h3 className="text-3xl font-black text-gray-900">1</h3>
            <i className="fas fa-truck text-2xl text-blue-200"></i>
          </div>
        </div>
        <div className="bg-white p-5 rounded-lg shadow-sm border border-gray-200 border-b-4 border-b-green-500">
          <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Delivered (YTD)</p>
          <div className="flex justify-between items-end">
            <h3 className="text-3xl font-black text-gray-900">42</h3>
            <i className="fas fa-check-circle text-2xl text-green-200"></i>
          </div>
        </div>
        <div className="bg-[#111827] p-5 rounded-lg shadow-sm border border-gray-800">
          <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Total Procurement Cost</p>
          <div className="flex justify-between items-end">
            <h3 className="text-xl font-black text-white mt-1">₹ 24.5L</h3>
            <i className="fas fa-rupee-sign text-2xl text-gray-600"></i>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <div className="flex space-x-2">
            <button className="px-3 py-1 text-[10px] font-black uppercase tracking-widest bg-gray-900 text-white rounded">All Requests</button>
            <button className="px-3 py-1 text-[10px] font-black uppercase tracking-widest bg-white border border-gray-300 text-gray-600 rounded hover:bg-gray-50">Pending Only</button>
          </div>
          <button className="text-gray-500 hover:text-gray-900 text-xs font-bold uppercase tracking-wider bg-white border border-gray-300 px-3 py-1.5 rounded">
            Export CSV
          </button>
        </div>

        <div className="flex-1 overflow-auto p-0">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Award ID</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Member details</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Reward Item</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Requirement Met</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Status</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Update Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {awards.map((award, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <p className="font-mono text-xs font-bold text-gray-900">{award.id}</p>
                    <p className="text-[10px] text-gray-500 mt-1 uppercase">Req: {new Date(award.requestDate).toLocaleDateString()}</p>
                  </td>
                  <td className="p-4">
                    <p className="font-bold text-gray-900 text-sm">{award.memberName}</p>
                    <p className="text-[10px] text-gray-500 font-mono mt-0.5">{award.memberId}</p>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center">
                      <i className={`fas ${award.awardType.includes('EV') ? 'fa-car' : award.awardType.includes('Coin') ? 'fa-coins' : 'fa-trophy'} text-gray-400 mr-2 text-lg`}></i>
                      <span className="text-sm font-bold text-gray-900">{award.awardType}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="bg-gray-100 text-gray-700 text-[10px] font-black px-2 py-1 rounded uppercase tracking-wider">
                      {award.requirement}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider ${
                      award.status === 'DELIVERED' ? 'bg-green-100 text-green-700' :
                      award.status === 'READY_FOR_DELIVERY' ? 'bg-blue-100 text-blue-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {award.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <select className="text-[10px] font-black uppercase tracking-widest border border-gray-300 rounded px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:border-indigo-500">
                      <option>Update Status...</option>
                      <option>Mark Procured</option>
                      <option>Mark Shipped</option>
                      <option>Mark Delivered</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
