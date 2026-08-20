"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";
import { Search, Filter, Network, UserPlus, CheckCircle, XCircle, History, Clock } from "lucide-react";

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
          if (json.success) setData(json.data);
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
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50 min-h-[calc(100vh-64px)]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Placement Approvals</h1>
          <p className="text-sm text-slate-500 mt-1">Network Genealogy & Node Overrides</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-slate-900 text-white hover:bg-slate-800 h-9 px-4 py-2 shadow">
            <Network className="mr-2 h-4 w-4" /> Auto-Place All
          </button>
        </div>
      </div>

      <div className="flex border-b border-slate-200 gap-8">
        <button 
          onClick={() => setActiveTab("pending")}
          className={`pb-4 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'pending' ? 'border-rose-600 text-rose-600' : 'border-transparent text-slate-500 hover:text-slate-900'}`}
        >
          <span className="flex items-center gap-2"><Clock className="h-4 w-4" /> Pending Requests ({pendingRequests.length})</span>
        </button>
        <button 
          onClick={() => setActiveTab("history")}
          className={`pb-4 text-sm font-semibold transition-colors border-b-2 ${activeTab === 'history' ? 'border-rose-600 text-rose-600' : 'border-transparent text-slate-500 hover:text-slate-900'}`}
        >
          <span className="flex items-center gap-2"><History className="h-4 w-4" /> Approval History</span>
        </button>
      </div>

      <div className="rounded-xl border bg-white text-slate-950 shadow-sm overflow-hidden flex flex-col">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 border-b gap-4 bg-slate-50/50">
          <div className="relative w-full sm:w-[350px]">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search by Member ID, Sponsor, or Request ID..." 
              className="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 pl-9"
            />
          </div>
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-slate-200 bg-white hover:bg-slate-100 hover:text-slate-900 h-9 px-4 py-2">
            <Filter className="mr-2 h-4 w-4" /> Filter List
          </button>
        </div>

        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-rose-600"></div>
          </div>
        ) : (
          <div className="relative w-full overflow-auto">
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b">
                <tr className="border-b transition-colors hover:bg-slate-50">
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Request ID & Date</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">New Member</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Sponsor</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Requested Position</th>
                  <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Super Admin Action</th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {activeTab === 'pending' && pendingRequests.map((req: any, idx: number) => (
                  <tr key={idx} className="border-b transition-colors hover:bg-slate-50">
                    <td className="p-6 align-middle">
                      <div className="font-mono font-medium text-slate-900">{req.id}</div>
                      <div className="text-xs text-slate-500 mt-1">{new Date(req.requestDate).toLocaleString([], { hour: '2-digit', minute:'2-digit', month:'short', day:'numeric' })}</div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                          <UserPlus className="h-4 w-4" />
                        </div>
                        <span className="font-semibold text-slate-900">{req.memberName}</span>
                      </div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="font-medium text-slate-700">{req.sponsorName}</div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="inline-flex items-center rounded-md border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-800">
                        {req.requestedPosition}
                      </div>
                    </td>
                    <td className="p-6 align-middle text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button className="inline-flex items-center justify-center rounded-md text-xs font-semibold transition-colors border border-rose-200 bg-white text-rose-600 hover:bg-rose-50 h-8 px-3">
                          <XCircle className="mr-1.5 h-3 w-3" /> Deny
                        </button>
                        <button className="inline-flex items-center justify-center rounded-md text-xs font-semibold transition-colors bg-emerald-600 text-white hover:bg-emerald-700 h-8 px-3 shadow-sm">
                          <CheckCircle className="mr-1.5 h-3 w-3" /> Approve
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                
                {activeTab === 'pending' && pendingRequests.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-16 text-center text-slate-500">
                      <CheckCircle className="mx-auto h-12 w-12 mb-4 text-emerald-400 opacity-50" />
                      <p className="text-lg font-medium text-slate-900">All caught up!</p>
                      <p className="text-sm">There are no pending placement approvals.</p>
                    </td>
                  </tr>
                )}

                {activeTab === 'history' && (
                  <tr>
                    <td colSpan={5} className="p-16 text-center text-slate-500">
                      <History className="mx-auto h-12 w-12 mb-4 opacity-20" />
                      <p className="text-lg font-medium text-slate-900">No recent history</p>
                      <p className="text-sm">Approval history will appear here.</p>
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
