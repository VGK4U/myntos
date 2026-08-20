"use client";

import React, { useState, useEffect } from 'react';

export default function ProcurementQueuePage() {
  const [requests, setRequests] = useState([
    { id: 'PRQ-901', item: 'Dell XPS 15', requester: 'John Doe', cost: '$1,500', status: 'Pending Approval' },
    { id: 'PRQ-902', item: 'Office Chair', requester: 'Jane Smith', cost: '$250', status: 'Under Review' },
  ]);

  useEffect(() => {
    // Fetch from /staff/service-tickets/procurement-queue
  }, []);

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Procurement Queue</h1>
          <p className="text-gray-500 mt-1">Review and approve procurement requests (/staff/service-tickets/procurement-queue)</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
          <div className="text-gray-500 text-sm font-medium mb-1">Pending Approval</div>
          <div className="text-3xl font-bold text-amber-600">12</div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
          <div className="text-gray-500 text-sm font-medium mb-1">Approved This Month</div>
          <div className="text-3xl font-bold text-emerald-600">45</div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
          <div className="text-gray-500 text-sm font-medium mb-1">Total Budget Spent</div>
          <div className="text-3xl font-bold text-indigo-600">$24,500</div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-sm font-medium text-gray-500 uppercase tracking-wider">
              <th className="p-4">Request ID</th>
              <th className="p-4">Item</th>
              <th className="p-4">Requester</th>
              <th className="p-4">Est. Cost</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {requests.map(r => (
              <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                <td className="p-4 font-medium text-gray-900">{r.id}</td>
                <td className="p-4 text-gray-700">{r.item}</td>
                <td className="p-4 text-gray-700">{r.requester}</td>
                <td className="p-4 font-medium text-gray-900">{r.cost}</td>
                <td className="p-4">
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-700">
                    {r.status}
                  </span>
                </td>
                <td className="p-4 flex gap-3 justify-end">
                  <button className="bg-emerald-50 text-emerald-600 px-3 py-1.5 rounded-md text-sm font-medium hover:bg-emerald-100 transition-colors">Approve</button>
                  <button className="bg-rose-50 text-rose-600 px-3 py-1.5 rounded-md text-sm font-medium hover:bg-rose-100 transition-colors">Deny</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
