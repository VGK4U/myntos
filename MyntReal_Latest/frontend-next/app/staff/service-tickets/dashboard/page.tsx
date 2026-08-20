"use client";

import React, { useState, useEffect } from 'react';

export default function DashboardPage() {
  const [data, setData] = useState([]);
  const [metrics, setMetrics] = useState({ total: 142, open: 24, resolved: 110, escalated: 8 });

  useEffect(() => {
    // Fetch from /staff/service-tickets/dashboard
  }, []);

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Service Tickets Dashboard</h1>
        <button className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-medium shadow-sm transition-colors">
          Generate Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[
          { label: 'Total Tickets', value: metrics.total, color: 'text-indigo-600', bg: 'bg-indigo-50' },
          { label: 'Open Tickets', value: metrics.open, color: 'text-amber-600', bg: 'bg-amber-50' },
          { label: 'Resolved', value: metrics.resolved, color: 'text-emerald-600', bg: 'bg-emerald-50' },
          { label: 'Escalated', value: metrics.escalated, color: 'text-rose-600', bg: 'bg-rose-50' },
        ].map((metric, i) => (
          <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col justify-between">
            <span className="text-gray-500 text-sm font-medium">{metric.label}</span>
            <div className={`text-4xl font-extrabold mt-4 ${metric.color}`}>{metric.value}</div>
            <div className={`mt-4 text-xs font-medium px-2.5 py-1 rounded-full w-fit ${metric.bg} ${metric.color}`}>
              +12% from last month
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-800">Recent Activity</h2>
          <span className="text-sm text-gray-500">Auto-mapped data viewer for /staff/service-tickets/dashboard</span>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-center h-64 text-gray-400 bg-gray-50 rounded-lg border border-dashed border-gray-200">
            [Chart or Activity Feed Placeholder]
          </div>
        </div>
      </div>
    </div>
  );
}
