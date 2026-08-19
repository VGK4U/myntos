"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import api from "@/lib/api";

interface AuditLog {
  id: number;
  action: string;
  module: string;
  ip_address: string;
  user_agent: string;
  timestamp: string;
  status: string; // SUCCESS, FAILED, WARNING
}

export default function StaffAuditLogsPage() {
  const { token } = useStaffAuth();
  
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      try {
        const res = await api.get('/staff/settings/audit-logs');
        setLogs(res.data);
      } catch (error) {
        console.error("Failed to fetch logs", error);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [token]);

  const filteredLogs = logs.filter(l => 
    l.action.toLowerCase().includes(searchTerm.toLowerCase()) || 
    l.module.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col md:flex-row gap-8 h-[calc(100vh-80px)]">
      {/* Settings Sidebar Nav */}
      <div className="w-full md:w-64 shrink-0 space-y-2">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 px-3">Settings Menu</h2>
        
        <Link href="/staff/settings/profile" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-user-circle text-lg w-6 text-gray-400"></i>
          Profile & Preferences
        </Link>
        
        <Link href="/staff/settings/security" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center text-gray-600 hover:bg-gray-100">
          <i className="fas fa-shield-alt text-lg w-6 text-gray-400"></i>
          Security & 2FA
        </Link>
        
        <Link href="/staff/settings/audit-logs" className="w-full text-left px-4 py-3 rounded-lg font-medium transition-colors flex items-center bg-indigo-50 text-indigo-700">
          <i className="fas fa-history text-lg w-6 text-indigo-600"></i>
          Audit & Activity Logs
        </Link>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0">
        <div className="mb-6 shrink-0 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Activity & Audit Logs</h1>
            <p className="text-sm text-gray-500 mt-2">A comprehensive history of actions performed on your account.</p>
          </div>
          <button className="px-4 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-download mr-2"></i> Export Logs
          </button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col flex-1 overflow-hidden min-h-0">
          <div className="p-4 border-b border-gray-100 bg-gray-50 flex items-center">
            <div className="relative flex-grow max-w-md">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input 
                type="text" 
                placeholder="Search actions or modules..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none" 
              />
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-12 text-center text-gray-500 flex flex-col items-center">
                <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
                <p>Retrieving activity logs...</p>
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="p-16 text-center text-gray-500 flex flex-col items-center">
                <div className="w-16 h-16 bg-gray-100 text-gray-400 rounded-full flex items-center justify-center mb-4">
                  <i className="fas fa-history text-2xl"></i>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-1">No logs found</h3>
                <p className="text-gray-500">There is no activity matching your search.</p>
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-white border-b border-gray-200 sticky top-0 z-10">
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Timestamp</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Action Details</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Module</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">IP / Device</th>
                    <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredLogs.map(log => (
                    <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                      <td className="p-4 whitespace-nowrap">
                        <p className="text-sm font-medium text-gray-900">{new Date(log.timestamp).toLocaleDateString()}</p>
                        <p className="text-xs text-gray-500">{new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}</p>
                      </td>
                      <td className="p-4">
                        <p className="text-sm font-medium text-gray-900">{log.action}</p>
                      </td>
                      <td className="p-4">
                        <span className="inline-block bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-[10px] font-bold">
                          {log.module}
                        </span>
                      </td>
                      <td className="p-4">
                        <p className="text-xs font-mono text-gray-600 mb-0.5">{log.ip_address}</p>
                        <p className="text-[10px] text-gray-400 max-w-[150px] truncate" title={log.user_agent}>{log.user_agent}</p>
                      </td>
                      <td className="p-4 text-center">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
                          log.status === "SUCCESS" ? "border-green-200 bg-green-50 text-green-700" :
                          log.status === "WARNING" ? "border-amber-200 bg-amber-50 text-amber-700" : 
                          "border-red-200 bg-red-50 text-red-700"
                        }`}>
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-center text-xs text-gray-500">
            <i className="fas fa-info-circle mr-1 mt-0.5"></i> Logs are retained for 90 days in accordance with security policies.
          </div>
        </div>
      </div>
    </div>
  );
}
