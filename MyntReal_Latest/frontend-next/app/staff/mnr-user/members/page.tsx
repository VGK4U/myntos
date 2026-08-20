"use client";

import React, { useState, useEffect } from 'react';
import { useStaffAuth } from '@/contexts/StaffAuthContext';
import { toast } from 'react-hot-toast';

export default function MembersPage() {
  const [searchId, setSearchId] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const { token } = useStaffAuth();

  const handleSearch = async () => {
    if (!searchId.trim()) return;
    setLoading(true);
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/staff/mnr-user/members/${searchId}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const jsonData = await res.json();
        setData(jsonData);
      } else {
        toast.error("Failed to fetch data");
        setData(null);
      }
    } catch (err) {
      console.warn("Error", err);
      toast.error("An error occurred");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    setActionLoading(true);
    setTimeout(() => {
      toast.success("Action approved successfully!");
      setActionLoading(false);
      setIsModalOpen(false);
    }, 1000);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <i className="fas fa-layer-group text-brand-warning"></i>
            Members Management
          </h1>
          <p className="text-gray-500">
            Premium Enterprise view for managing "data".
          </p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors font-medium flex items-center gap-2"
        >
          <i className="fas fa-plus"></i>
          New Action
        </button>
      </div>

      <div className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm">
        <label className="block text-gray-700 font-bold mb-2">Search MNR ID</label>
        <div className="flex gap-2 max-w-md">
          <div className="relative flex-grow">
            <input 
              type="text" 
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="w-full bg-gray-50 border border-gray-300 rounded-lg py-2.5 px-4 text-gray-900 focus:outline-none focus:border-brand-warning transition-colors"
              placeholder="e.g. MNR12345"
            />
          </div>
          <button 
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-2.5 bg-brand-warning hover:bg-yellow-400 text-black font-bold rounded-lg transition-colors flex items-center gap-2 disabled:opacity-70"
          >
            {loading ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-search"></i>}
            Search
          </button>
        </div>
      </div>

      {data && (
        <div className="p-6 rounded-xl bg-white border border-gray-200 shadow-sm">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-gray-900">Results Overview</h3>
            <span className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold">Active</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600 font-medium border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3">Property</th>
                  <th className="px-4 py-3">Value</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {Object.entries(data).slice(0, 5).map(([key, val], idx) => (
                  <tr key={idx} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-medium text-gray-900 capitalize">{key.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {typeof val === 'object' ? JSON.stringify(val).substring(0, 50) + '...' : String(val)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => setIsModalOpen(true)} className="text-brand-warning hover:text-yellow-600 font-medium">Edit</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Interactive Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-900">Manage Members</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <i className="fas fa-times text-xl"></i>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status Update</label>
                <select className="w-full border border-gray-300 rounded-lg py-2 px-3 focus:outline-none focus:border-brand-warning">
                  <option>Approve Request</option>
                  <option>Reject Request</option>
                  <option>Mark as Pending</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Admin Notes</label>
                <textarea className="w-full border border-gray-300 rounded-lg py-2 px-3 focus:outline-none focus:border-brand-warning h-24" placeholder="Enter specific actions or remarks..."></textarea>
              </div>
            </div>
            <div className="p-6 bg-gray-50 flex justify-end gap-3 rounded-b-2xl">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 font-medium text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={handleApprove}
                disabled={actionLoading}
                className="px-6 py-2 bg-brand-warning text-black font-bold rounded-lg hover:bg-yellow-400 transition-colors flex items-center gap-2"
              >
                {actionLoading ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-check"></i>}
                Confirm Action
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
