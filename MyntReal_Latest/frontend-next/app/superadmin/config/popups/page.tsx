"use client";

import React, { useState } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";

export default function SuperAdminPopupControl() {
  const { user } = useSuperAdminAuth();

  const popups = [
    { id: 'POP-001', title: 'Diwali Offer Announcement', target: 'Members Only', type: 'Image + Text', status: 'ACTIVE', views: 4205, clicks: 850 },
    { id: 'POP-002', title: 'System Maintenance Notice', target: 'Global (All Users)', type: 'Text Only', status: 'SCHEDULED', views: 0, clicks: 0 },
    { id: 'POP-003', title: 'New Vendor Policy', target: 'Vendors Only', type: 'Text + Link', status: 'INACTIVE', views: 120, clicks: 45 },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Global Popup Control</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Manage System-Wide Alerts, Offers, and Forced Notifications</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-indigo-600 text-white font-bold rounded shadow-sm hover:bg-indigo-700 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-plus mr-2"></i> Create New Popup
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 shrink-0">
        <div className="bg-indigo-900 p-6 rounded-lg shadow-lg border border-indigo-800 text-white">
          <p className="text-[10px] font-black text-indigo-300 uppercase tracking-widest mb-1">Active Broadcasts</p>
          <div className="flex justify-between items-end">
            <h3 className="text-4xl font-black mt-1">1</h3>
            <i className="fas fa-broadcast-tower text-3xl text-indigo-500 opacity-50"></i>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">Total Impressions (MTD)</p>
          <h3 className="text-2xl font-black text-gray-900 mt-1">4,325</h3>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-1">Avg Click-Through Rate</p>
          <h3 className="text-2xl font-black text-gray-900 mt-1">20.4%</h3>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">Popup Inventory</h3>
        </div>

        <div className="flex-1 overflow-auto p-0">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Popup Name / ID</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Target Audience</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Type</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Performance</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Status & Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {popups.map((popup, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <p className="font-bold text-gray-900 text-sm">{popup.title}</p>
                    <p className="font-mono text-[10px] text-gray-500 mt-1">{popup.id}</p>
                  </td>
                  <td className="p-4">
                    <span className="bg-indigo-50 text-indigo-700 text-[10px] font-black px-2 py-1 rounded uppercase tracking-wider border border-indigo-100">
                      {popup.target}
                    </span>
                  </td>
                  <td className="p-4">
                    <p className="text-xs font-bold text-gray-700">{popup.type}</p>
                  </td>
                  <td className="p-4">
                    <div className="flex gap-4">
                      <div>
                        <p className="text-[10px] text-gray-500 uppercase font-bold">Views</p>
                        <p className="text-sm font-black text-gray-900">{popup.views.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-gray-500 uppercase font-bold">Clicks</p>
                        <p className="text-sm font-black text-indigo-600">{popup.clicks.toLocaleString()}</p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex flex-col items-end">
                      <span className={`text-[9px] font-black px-2 py-1 rounded uppercase tracking-wider mb-2 ${
                        popup.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 
                        popup.status === 'SCHEDULED' ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-700'
                      }`}>
                        {popup.status}
                      </span>
                      <div className="flex space-x-2">
                        <button className="text-gray-400 hover:text-indigo-600 px-2 text-sm"><i className="fas fa-edit"></i></button>
                        <button className="text-gray-400 hover:text-red-600 px-2 text-sm"><i className="fas fa-trash"></i></button>
                      </div>
                    </div>
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
