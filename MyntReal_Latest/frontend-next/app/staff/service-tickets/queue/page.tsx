"use client";

import React, { useState, useEffect } from 'react';

export default function QueuePage() {
  const [tickets, setTickets] = useState([
    { id: 'TKT-001', title: 'Network Outage', priority: 'High', status: 'Open', date: '2026-08-19' },
    { id: 'TKT-002', title: 'Laptop Replacement', priority: 'Medium', status: 'In Progress', date: '2026-08-18' },
    { id: 'TKT-003', title: 'Software License', priority: 'Low', status: 'Pending', date: '2026-08-17' },
  ]);

  useEffect(() => {
    // Fetch from /staff/service-tickets/queue
  }, []);

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Service Queue</h1>
          <p className="text-gray-500 mt-1">Manage and resolve open service tickets (/staff/service-tickets/queue)</p>
        </div>
        <div className="flex gap-3">
          <input type="text" placeholder="Search tickets..." className="px-4 py-2 border border-gray-200 rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 outline-none" />
          <button className="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-lg font-medium shadow-sm hover:bg-gray-50">Filter</button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100 text-sm font-medium text-gray-500 uppercase tracking-wider">
              <th className="p-4">Ticket ID</th>
              <th className="p-4">Title</th>
              <th className="p-4">Priority</th>
              <th className="p-4">Status</th>
              <th className="p-4">Date</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {tickets.map(t => (
              <tr key={t.id} className="hover:bg-gray-50 transition-colors">
                <td className="p-4 font-medium text-gray-900">{t.id}</td>
                <td className="p-4 text-gray-700">{t.title}</td>
                <td className="p-4">
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${t.priority === 'High' ? 'bg-rose-100 text-rose-700' : t.priority === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>
                    {t.priority}
                  </span>
                </td>
                <td className="p-4">
                  <span className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded-md">{t.status}</span>
                </td>
                <td className="p-4 text-sm text-gray-500">{t.date}</td>
                <td className="p-4 flex gap-2 justify-end">
                  <button className="text-indigo-600 hover:text-indigo-900 text-sm font-medium">Resolve</button>
                  <button className="text-rose-600 hover:text-rose-900 text-sm font-medium">Escalate</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
