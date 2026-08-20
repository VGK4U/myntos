"use client";

import React, { useState, useEffect } from 'react';
import api from '@/lib/api';

export default function IntakePage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/staff/inventory/intake');
      setData(Array.isArray(res.data) ? res.data : (res.data.items || []));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredData = data.filter(item => 
    Object.values(item).some(val => 
      String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-700 text-xs font-bold uppercase tracking-wider mb-2">
            Inventory Domain
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Intake Management</h1>
          <p className="text-slate-500 mt-1">Manage and track intake seamlessly.</p>
        </div>
        
        <div className="flex gap-3">
          <button className="px-5 py-2.5 bg-white text-slate-700 border border-slate-200 font-bold rounded-xl shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2 text-sm">
             Export CSV
          </button>
          <button className="px-5 py-2.5 bg-emerald-600 text-white font-bold rounded-xl shadow-lg shadow-emerald-600/20 hover:bg-emerald-700 transition-all flex items-center gap-2 text-sm">
             Validate / Sync
          </button>
          <button className="px-5 py-2.5 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center gap-2 text-sm">
             Add New
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <span className="text-slate-500 text-sm font-semibold mb-2">Total Records</span>
          <span className="text-3xl font-black text-slate-800">{data.length || 0}</span>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <span className="text-slate-500 text-sm font-semibold mb-2">Recently Updated</span>
          <span className="text-3xl font-black text-blue-600">{Math.min(data.length, 5)}</span>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <span className="text-slate-500 text-sm font-semibold mb-2">Pending Actions</span>
          <span className="text-3xl font-black text-amber-500">2</span>
        </div>
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <span className="text-slate-500 text-sm font-semibold mb-2">System Status</span>
          <span className="text-3xl font-black text-emerald-500">Active</span>
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-bold text-slate-800 flex items-center gap-2">
            Intake Data Explorer
          </h2>
          <div className="relative">
            <input 
              type="text" 
              placeholder="Search records..." 
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="px-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 w-64 bg-slate-50" 
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">ID / Ref</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Primary Details</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-slate-400">
                    <p className="font-medium">Loading Secure Data...</p>
                  </td>
                </tr>
              ) : filteredData.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-16 text-center text-slate-500">
                    <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center text-3xl text-slate-400 mx-auto mb-4">
                       📦
                    </div>
                    <p className="font-bold text-slate-700 text-lg mb-1">No intake found</p>
                    <p className="text-sm">Try adjusting your search or add a new record.</p>
                  </td>
                </tr>
              ) : (
                filteredData.map((item, idx) => (
                  <tr key={idx} className="hover:bg-emerald-50/30 transition-colors group">
                    <td className="px-6 py-4 text-sm font-mono text-slate-600">{item.id || item.ref_id || idx + 1001}</td>
                    <td className="px-6 py-4">
                      <p className="font-bold text-slate-900">{item.name || item.title || item.item_name || 'Generic Item'}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{item.description || item.brand_name || 'No description available'}</p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        {item.status || 'Active'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <button className="px-3 py-1 bg-white border border-slate-200 rounded text-xs font-bold text-slate-600 hover:text-emerald-600 hover:border-emerald-200 transition-colors">
                          Edit
                        </button>
                        <button className="px-3 py-1 bg-white border border-slate-200 rounded text-xs font-bold text-slate-600 hover:text-blue-600 hover:border-blue-200 transition-colors">
                          Transfer
                        </button>
                      </div>
                    </td>
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
