"use client";

import React, { useState, useEffect } from "react";
import { useSuperAdminAuth } from "@/contexts/SuperAdminAuthContext";
import { getApiUrl } from "@/lib/api";
import { Megaphone, Activity, MousePointerClick, Plus, Search, Trash2, Edit } from "lucide-react";

export default function SuperAdminPopupControl() {
  const { user, token } = useSuperAdminAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/super-admin/config/popups`, {
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

  const popups = data?.popups || [];

  const handleDelete = async (popupId: number) => {
    if (!confirm('Are you sure you want to delete this popup?')) return;
    try {
      const res = await fetch(`${getApiUrl()}/api/v1/banners/popups/${popupId}`, {
        method: 'DELETE',
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        alert("Popup deleted successfully");
        window.location.reload();
      } else {
        alert("Failed to delete popup");
      }
    } catch(err) {
      console.error(err);
      alert("Error deleting popup");
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 bg-slate-50 min-h-[calc(100vh-64px)]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Global Popup Control</h1>
          <p className="text-sm text-slate-500 mt-1">Manage System-Wide Alerts, Offers, and Forced Notifications</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-indigo-600 text-white hover:bg-indigo-700 h-9 px-4 py-2 shadow">
            <Plus className="mr-2 h-4 w-4" /> Create New Popup
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border bg-indigo-900 text-white shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Megaphone className="h-24 w-24" />
          </div>
          <div className="p-6 relative z-10">
            <h3 className="text-indigo-200 text-sm font-medium mb-2">Active Broadcasts</h3>
            <div className="text-4xl font-bold">{data?.metrics?.active_broadcasts || 0}</div>
          </div>
        </div>
        <div className="rounded-xl border bg-white text-slate-950 shadow-sm">
          <div className="p-6">
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-slate-500 text-sm font-medium">Total Impressions (MTD)</h3>
              <Activity className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-3xl font-bold">{data?.metrics?.total_impressions || '0'}</div>
          </div>
        </div>
        <div className="rounded-xl border bg-white text-slate-950 shadow-sm">
          <div className="p-6">
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-slate-500 text-sm font-medium">Avg Click-Through Rate</h3>
              <MousePointerClick className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-3xl font-bold">{data?.metrics?.avg_ctr || '0%'}</div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border bg-white text-slate-950 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b bg-slate-50/50">
          <h3 className="font-semibold text-slate-800">Popup Inventory</h3>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search popups..."
              className="flex h-9 w-[250px] rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-slate-500 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 pl-9"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex h-48 items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          </div>
        ) : (
          <div className="relative w-full overflow-auto">
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b">
                <tr className="border-b transition-colors hover:bg-slate-50">
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Popup Details</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Target</th>
                  <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Performance</th>
                  <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Actions</th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {popups.map((popup: any, idx: number) => (
                  <tr key={idx} className="border-b transition-colors hover:bg-slate-50">
                    <td className="p-6 align-middle">
                      <div className="font-medium text-slate-900">{popup.title}</div>
                      <div className="text-xs text-slate-500 font-mono mt-1">ID: {popup.id} • Type: {popup.type}</div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 border border-indigo-200">
                        {popup.target}
                      </div>
                    </td>
                    <td className="p-6 align-middle">
                      <div className="flex gap-6">
                        <div>
                          <div className="text-xs text-slate-500">Views</div>
                          <div className="font-medium">{popup.views.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500">Clicks</div>
                          <div className="font-medium text-indigo-600">{popup.clicks.toLocaleString()}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-6 align-middle text-right">
                      <div className="flex items-center justify-end gap-4">
                        <div className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          popup.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 
                          popup.status === 'SCHEDULED' ? 'bg-blue-100 text-blue-800' : 'bg-slate-100 text-slate-800'
                        }`}>
                          {popup.status}
                        </div>
                        <button className="text-slate-400 hover:text-indigo-600 transition-colors">
                          <Edit className="h-4 w-4" />
                        </button>
                        <button onClick={() => handleDelete(popup.id)} className="text-slate-400 hover:text-rose-600 transition-colors">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {popups.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-12 text-center text-slate-500">
                      <Megaphone className="mx-auto h-12 w-12 mb-4 opacity-20" />
                      <p className="text-lg font-medium text-slate-900">No popups configured</p>
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
