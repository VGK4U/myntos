"use client";

import { useState, useEffect } from "react";

export default function AuditLogPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock initial load
    setTimeout(() => {
      setLogs([
        { id: 1, staff_name: "Anil Kumar", emp_code: "EMP-001", action_type: "view", mnr_id: "MNR10025", page: "Profile Dashboard", created_at: "2023-10-15T10:30:00Z" },
        { id: 2, staff_name: "Ramesh Singh", emp_code: "EMP-042", action_type: "export", mnr_id: "MNR10025", page: "Financial Statement", created_at: "2023-10-15T09:15:00Z" },
        { id: 3, staff_name: "Priya Sharma", emp_code: "EMP-015", action_type: "search", mnr_id: "MNR88210", page: "Global Search", created_at: "2023-10-14T16:45:00Z" },
      ]);
      setLoading(false);
    }, 800);
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gray-900/5 flex items-center justify-center">
            <i className="fas fa-clipboard-list text-gray-700"></i>
          </div>
          Staff Access Audit Log
        </h1>
        <p className="text-gray-500">
          Track all staff access to member data for security and compliance.
        </p>
      </div>

      {/* Filter Card */}
      <div className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">MNR ID</label>
            <input type="text" className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2 px-3 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900 uppercase" placeholder="MNR ID" />
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Staff Employee</label>
            <input type="text" className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2 px-3 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900" placeholder="Emp Code" />
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Action Type</label>
            <select className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2 px-3 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900">
              <option value="">All Actions</option>
              <option value="view">View</option>
              <option value="search">Search</option>
              <option value="export">Export</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Date From</label>
            <input type="date" className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2 px-3 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900" />
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Date To</label>
            <input type="date" className="w-full bg-gray-50 border border-gray-200 rounded-lg py-2 px-3 text-gray-900 focus:ring-2 focus:ring-gray-900/20 focus:border-gray-900" />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-gray-100">
          <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors shadow-sm">
            <i className="fas fa-times mr-2"></i>Clear
          </button>
          <button className="px-6 py-2 bg-gray-900 hover:bg-black text-white font-bold rounded-lg transition-colors shadow-sm">
            <i className="fas fa-search mr-2"></i>Search
          </button>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-gray-500 font-medium">Total records: <span className="text-gray-900 font-bold">{logs.length}</span></span>
        <button className="px-4 py-2 bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium rounded-lg hover:bg-emerald-100 transition-colors shadow-sm text-sm">
          <i className="fas fa-download mr-2"></i>Export CSV
        </button>
      </div>

      {/* Results */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 font-medium">Staff Member</th>
              <th className="px-6 py-3 font-medium">Action</th>
              <th className="px-6 py-3 font-medium">Target Member</th>
              <th className="px-6 py-3 font-medium">Page/Context</th>
              <th className="px-6 py-3 font-medium text-right">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={5} className="px-6 py-12 text-center text-gray-400"><i className="fas fa-spinner fa-spin fa-2x mb-3"></i><p>Loading audit logs...</p></td></tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-bold text-gray-900">{log.staff_name}</div>
                    <div className="text-xs text-gray-500">{log.emp_code}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-xs rounded-lg font-bold uppercase tracking-wider ${
                      log.action_type === 'view' ? 'bg-sky-50 text-sky-700 border border-sky-200' :
                      log.action_type === 'search' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                      'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    }`}>
                      {log.action_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-medium text-gray-900">{log.mnr_id}</td>
                  <td className="px-6 py-4 text-gray-600">{log.page}</td>
                  <td className="px-6 py-4 text-right text-gray-500 tabular-nums">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
