"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";

export default function SuperAdminPlacementApprovals() {
  const { user, token } = useSuperAdminAuth();

  const [activeTab, setActiveTab] = useState("pending");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    
    const fetchData = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/super-admin/network/approvals`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
          const json = await res.json();
          if (json.success) {
            setData(json.data);
          }
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [token]);

  const pendingRequests = data?.approvals || [];

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col h-[calc(100vh-64px)]">
      <div className="flex justify-between items-end mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight uppercase">Placement Approvals</h1>
          <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Network Genealogy & Node Overrides</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-gray-900 text-white font-bold rounded shadow-sm hover:bg-gray-800 transition-colors uppercase text-xs tracking-wider">
            <i className="fas fa-sitemap mr-2"></i> Auto-Place All
          </button>
        </div>
      </div>

      <div className="flex space-x-6 mb-6 shrink-0 border-b border-gray-200">
        <button 
          onClick={() => setActiveTab("pending")}
          className={`pb-3 text-xs font-black uppercase tracking-widest transition-colors border-b-2 ${activeTab === 'pending' ? 'border-red-600 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
        >
          Pending Requests (3)
        </button>
        <button 
          onClick={() => setActiveTab("history")}
          className={`pb-3 text-xs font-black uppercase tracking-widest transition-colors border-b-2 ${activeTab === 'history' ? 'border-red-600 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
        >
          Approval History
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
          <div className="relative w-96">
            <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm"></i>
            <input 
              type="text" 
              placeholder="Search by Member ID, Sponsor, or Request ID..." 
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded text-sm focus:ring-1 focus:ring-red-500 outline-none"
            />
          </div>
          <button className="text-gray-500 hover:text-gray-900 text-sm font-bold uppercase tracking-wider">
            <i className="fas fa-filter mr-2"></i> Filter List
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex justify-center items-center">
            <i className="fas fa-circle-notch fa-spin text-3xl text-gray-400"></i>
          </div>
        ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left">
            <thead className="bg-white sticky top-0 z-10">
              <tr className="border-b border-gray-200">
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Request ID / Date</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">New Member</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Sponsor</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Requested Position</th>
                <th className="p-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Super Admin Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              
              {activeTab === 'pending' && pendingRequests.map((req: any, idx: number) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors group">
                  <td className="p-4">
                    <p className="font-mono text-xs font-bold text-gray-900">{req.id}</p>
                    <p className="text-[10px] text-gray-500 mt-1 uppercase">{new Date(req.requestDate).toLocaleString([], { hour: '2-digit', minute:'2-digit', month:'short', day:'numeric' })}</p>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center">
                      <div className="w-8 h-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xs mr-3">
                        <i className="fas fa-user-plus"></i>
                      </div>
                      <span className="text-sm font-bold text-gray-900">{req.memberName}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="text-sm font-bold text-gray-700">{req.sponsorName}</span>
                  </td>
                  <td className="p-4">
                    <span className="bg-gray-100 text-gray-800 text-xs font-bold px-3 py-1 rounded uppercase tracking-wider border border-gray-200">
                      {req.requestedPosition}
                    </span>
                  </td>
                  <td className="p-4 text-right space-x-2">
                    <button className="px-3 py-1.5 bg-white border border-red-200 text-red-600 hover:bg-red-50 text-xs font-bold rounded uppercase tracking-wider transition-colors">
                      Deny
                    </button>
                    <button className="px-3 py-1.5 bg-green-600 text-white hover:bg-green-700 text-xs font-bold rounded uppercase tracking-wider transition-colors">
                      Approve
                    </button>
                  </td>
                </tr>
              ))}
              
              {activeTab === 'pending' && pendingRequests.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-16 text-center text-gray-500">
                    <i className="fas fa-check-circle text-4xl mb-4 text-green-300"></i>
                    <p className="text-sm font-bold uppercase tracking-widest text-gray-400">All caught up! No pending approvals.</p>
                  </td>
                </tr>
              )}

              {activeTab === 'history' && (
                <tr>
                  <td colSpan={5} className="p-16 text-center text-gray-500">
                    <i className="fas fa-history text-4xl mb-4 text-gray-300"></i>
                    <p className="text-sm font-bold uppercase tracking-widest text-gray-400">No recent history found.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        )}
      </div>
    </div>
  );
}
