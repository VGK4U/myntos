"use client";

import React, { useState, useEffect } from 'react';
import api from '@/lib/api';

interface GenericDataTableProps {
  endpoint: string;
  title: string;
  subtitle?: string;
  icon?: string;
  dataKey?: string; // If the array is nested inside res.data[dataKey]
  allowSearch?: boolean;
}

export default function GenericDataTable({ 
  endpoint, 
  title, 
  subtitle = "Manage and view records", 
  icon = "fa-table",
  dataKey,
  allowSearch = true
}: GenericDataTableProps) {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchData();
  }, [endpoint]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(endpoint);
      let arr = [];
      if (Array.isArray(res.data)) {
        arr = res.data;
      } else if (dataKey && res.data && Array.isArray(res.data[dataKey])) {
        arr = res.data[dataKey];
      } else if (res.data && Array.isArray(res.data.data)) {
        arr = res.data.data;
      } else if (res.data && Array.isArray(res.data.items)) {
        arr = res.data.items;
      } else {
        // Try to find the first array in the object
        for (const key in res.data) {
          if (Array.isArray(res.data[key])) {
            arr = res.data[key];
            break;
          }
        }
      }
      setData(arr);
    } catch (err: any) {
      console.error(`Failed to fetch from ${endpoint}:`, err);
      setError(err?.response?.data?.detail || "Failed to load data. The endpoint might require specific parameters or permissions.");
    } finally {
      setLoading(false);
    }
  };

  const filteredData = data.filter((item: any) => {
    if (!searchTerm) return true;
    const s = searchTerm.toLowerCase();
    return Object.values(item).some(val => 
      String(val).toLowerCase().includes(s)
    );
  });

  // Extract columns from first item
  const columns = data.length > 0 ? Object.keys(data[0]).filter(k => typeof data[0][k] !== 'object') : [];

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-xs font-bold uppercase tracking-wider mb-2">
            Auto-Generated Module
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">{title}</h1>
          <p className="text-slate-500 mt-1">{subtitle}</p>
        </div>
        <button onClick={fetchData} className="px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-bold rounded-xl shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2 text-sm">
          <i className="fas fa-sync-alt"></i> Refresh
        </button>
      </div>

      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        {allowSearch && (
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-bold text-slate-800 flex items-center gap-2">
              <i className={`fas ${icon} text-blue-500`}></i> Data Records
            </h2>
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
              <input 
                type="text" 
                placeholder="Search across all columns..." 
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 w-64 bg-slate-50" 
              />
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                {columns.map(col => (
                  <th key={col} className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                    {col.replace(/_/g, ' ')}
                  </th>
                ))}
                {columns.length === 0 && !loading && !error && (
                  <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={Math.max(columns.length, 1)} className="px-6 py-12 text-center text-slate-400">
                    <i className="fas fa-circle-notch fa-spin text-3xl mb-3"></i>
                    <p className="font-medium">Loading from {endpoint}...</p>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={Math.max(columns.length, 1)} className="px-6 py-12 text-center text-rose-500 bg-rose-50/30">
                    <i className="fas fa-exclamation-triangle text-3xl mb-3"></i>
                    <p className="font-medium">{error}</p>
                    <p className="text-xs mt-2 text-rose-400 font-mono">{endpoint}</p>
                  </td>
                </tr>
              ) : filteredData.length === 0 ? (
                <tr>
                  <td colSpan={Math.max(columns.length, 1)} className="px-6 py-16 text-center text-slate-500">
                    <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center text-3xl text-slate-400 mx-auto mb-4">
                      <i className="fas fa-database"></i>
                    </div>
                    <p className="font-bold text-slate-700 text-lg mb-1">No records found</p>
                    <p className="text-sm">The endpoint returned an empty list.</p>
                  </td>
                </tr>
              ) : (
                filteredData.map((item, idx) => (
                  <tr key={idx} className="hover:bg-blue-50/30 transition-colors">
                    {columns.map(col => (
                      <td key={col} className="px-6 py-4 text-sm text-slate-700 whitespace-nowrap">
                        {String(item[col])}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
