"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";
import { Trophy, Car, Coins, CheckCircle, PackageSearch, Truck, IndianRupee, AlertCircle, Plus, FileDown, Search, Filter } from "lucide-react";

export default function SuperAdminAwardsPage() {
  const { user, token } = useSuperAdminAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/super-admin/awards`, {
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

  const awards = data?.awards || [];

  const handleUpdateStatus = async (awardId: string, awardType: string, newStatus: string) => {
    if (!newStatus) return;
    const rawId = awardId.replace('AWD-', '');
    const typeStr = awardType === 'Dynamic Award' ? 'direct' : awardType.toLowerCase();
    
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/rvz/awards/${typeStr}/${rawId}/override`, {
        method: 'POST',
        headers: { 
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ new_status: newStatus, reason: "Superadmin manual update" })
      });
      if (res.ok) {
        alert("Status updated successfully");
        window.location.reload();
      } else {
        alert("Failed to update status");
      }
    } catch(err) {
      console.error(err);
      alert("Error updating status");
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50 min-h-[calc(100vh-64px)]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Awards Procurement</h1>
          <p className="text-sm text-slate-500 mt-1">Manage fulfillment of physical member rewards and vehicles</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-slate-200 bg-white hover:bg-slate-100 hover:text-slate-900 h-9 px-4 py-2">
            <FileDown className="mr-2 h-4 w-4" /> Export CSV
          </button>
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-slate-900 text-slate-50 hover:bg-slate-900/90 h-9 px-4 py-2 shadow">
            <Plus className="mr-2 h-4 w-4" /> Add Reward
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[
          { title: "Pending Procurement", value: data?.metrics?.pending || 0, icon: PackageSearch, color: "text-amber-500", bg: "bg-amber-100" },
          { title: "Ready For Delivery", value: data?.metrics?.ready || 0, icon: Truck, color: "text-blue-500", bg: "bg-blue-100" },
          { title: "Delivered (YTD)", value: data?.metrics?.delivered || 0, icon: CheckCircle, color: "text-emerald-500", bg: "bg-emerald-100" },
          { title: "Total Cost", value: `₹ ${data?.metrics?.total_cost || '0'}`, icon: IndianRupee, color: "text-rose-500", bg: "bg-rose-100" }
        ].map((metric, i) => (
          <div key={i} className="rounded-xl border bg-white text-slate-950 shadow-sm">
            <div className="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
              <h3 className="tracking-tight text-sm font-medium">{metric.title}</h3>
              <div className={`p-2 rounded-full ${metric.bg}`}>
                <metric.icon className={`h-4 w-4 ${metric.color}`} />
              </div>
            </div>
            <div className="p-6 pt-0">
              <div className="text-2xl font-bold">{metric.value}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border bg-white text-slate-950 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search awards..."
                className="flex h-9 w-full md:w-[300px] rounded-md border border-slate-200 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 pl-9"
              />
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex h-48 items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900"></div>
          </div>
        ) : (
          <div className="relative w-full overflow-auto">
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b bg-slate-50/50">
                <tr className="border-b transition-colors hover:bg-slate-100/50">
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">ID & Date</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Member</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Reward</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Status</th>
                  <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Action</th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {awards.map((award: any, idx: number) => (
                  <tr key={idx} className="border-b transition-colors hover:bg-slate-50">
                    <td className="p-6 align-middle">
                      <div className="font-medium text-slate-900">{award.id}</div>
                      <div className="text-xs text-slate-500">{new Date(award.requestDate).toLocaleDateString()}</div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="font-medium text-slate-900">{award.memberName}</div>
                      <div className="text-xs text-slate-500 font-mono">{award.memberId}</div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="flex items-center gap-2">
                        {award.awardType.includes('EV') ? <Car className="h-4 w-4 text-blue-500" /> : 
                         award.awardType.includes('Coin') ? <Coins className="h-4 w-4 text-amber-500" /> : 
                         <Trophy className="h-4 w-4 text-purple-500" />}
                        <span className="font-medium text-slate-900">{award.awardType}</span>
                      </div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        award.status === 'DELIVERED' ? 'bg-emerald-100 text-emerald-800' :
                        award.status === 'READY_FOR_DELIVERY' ? 'bg-blue-100 text-blue-800' :
                        'bg-amber-100 text-amber-800'
                      }`}>
                        {award.status.replace(/_/g, ' ')}
                      </div>
                    </td>
                    <td className="p-6 align-middle text-right">
                      <select 
                        className="flex h-9 w-full md:w-auto ml-auto rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950"
                        onChange={(e) => handleUpdateStatus(award.id, award.awardType, e.target.value)}
                        defaultValue=""
                      >
                        <option value="" disabled>Update...</option>
                        <option value="Procured">Mark Procured</option>
                        <option value="Processed for Dispatch">Mark Dispatched</option>
                        <option value="Delivered">Mark Delivered</option>
                      </select>
                    </td>
                  </tr>
                ))}
                {awards.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-12 text-center text-slate-500">
                      <PackageSearch className="mx-auto h-12 w-12 mb-4 opacity-20" />
                      <p className="text-lg font-medium text-slate-900">No awards found</p>
                      <p className="text-sm">There are currently no awards in the system.</p>
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
