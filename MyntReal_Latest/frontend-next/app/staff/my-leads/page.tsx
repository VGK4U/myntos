"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import Link from 'next/link';

interface Lead {
  id: number;
  name: string;
  phone: string;
  email: string | null;
  status: string;
  priority: string;
  source: string;
  created_at: string;
  handler_name?: string;
  company_id?: number;
}

export default function MyLeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // DC Protocol Data Siloing filters
  const [segment, setSegment] = useState<"my" | "assigned" | "fresh">("my");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLeads, setTotalLeads] = useState(0);

  useEffect(() => {
    fetchLeads();
  }, [page, segment]);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      // Backend expects company_id as per DC protocol for data siloing, handled by user token automatically in Unified Leads endpoint
      const res = await api.get(`/crm/unified-my-leads?segment=${segment}&page=${page}&per_page=20`);
      
      if (res.data && res.data.leads) {
        setLeads(res.data.leads);
        setTotalPages(res.data.total_pages || 1);
        setTotalLeads(res.data.total || res.data.leads.length);
      } else if (Array.isArray(res.data)) {
        // Fallback
        setLeads(res.data);
        setTotalLeads(res.data.length);
      }
    } catch (err: any) {
      console.error("Failed to fetch leads:", err);
      setError("Could not load leads. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    if (s === 'new') return <span className="px-2.5 py-1 bg-blue-100 text-blue-700 rounded-lg text-xs font-bold uppercase tracking-wider">New</span>;
    if (s === 'contacted') return <span className="px-2.5 py-1 bg-amber-100 text-amber-700 rounded-lg text-xs font-bold uppercase tracking-wider">Contacted</span>;
    if (s === 'interested') return <span className="px-2.5 py-1 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold uppercase tracking-wider">Interested</span>;
    if (s === 'won' || s === 'converted') return <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-lg text-xs font-bold uppercase tracking-wider">Converted</span>;
    if (s === 'lost' || s === 'dead') return <span className="px-2.5 py-1 bg-rose-100 text-rose-700 rounded-lg text-xs font-bold uppercase tracking-wider">Lost</span>;
    return <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg text-xs font-bold uppercase tracking-wider">{status}</span>;
  };

  const getPriorityBadge = (priority: string) => {
    const p = (priority || "").toLowerCase();
    if (p === 'high') return <span className="text-rose-600 font-bold text-xs"><i className="fas fa-fire mr-1"></i>High</span>;
    if (p === 'medium') return <span className="text-amber-600 font-bold text-xs"><i className="fas fa-bolt mr-1"></i>Medium</span>;
    if (p === 'low') return <span className="text-slate-500 font-bold text-xs"><i className="fas fa-snowflake mr-1"></i>Low</span>;
    return <span className="text-slate-400 text-xs">{priority}</span>;
  };

  return (
    <div className="p-6 lg:p-10 max-w-[1600px] mx-auto bg-slate-50 min-h-screen">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold uppercase tracking-wider mb-2">
            CRM Central
          </div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Unified Leads Engine</h1>
          <p className="text-slate-500 mt-1">Manage and convert your assigned enterprise leads</p>
        </div>
        
        <div className="flex gap-3">
          <Link href="/staff/leads/add-lead" className="px-5 py-2.5 bg-slate-900 text-white font-bold rounded-xl shadow-lg shadow-slate-900/20 hover:bg-slate-800 transition-all flex items-center gap-2 text-sm">
            <i className="fas fa-plus"></i> New Lead
          </Link>
          <button className="px-5 py-2.5 bg-white border border-slate-200 text-slate-700 font-bold rounded-xl hover:border-slate-300 hover:bg-slate-50 transition-all flex items-center gap-2 text-sm">
            <i className="fas fa-cloud-download-alt"></i> Export
          </button>
        </div>
      </div>

      {/* Segments Navigation */}
      <div className="bg-white p-2 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap gap-2 mb-6">
        {[
          { id: "my", label: "My Leads", icon: "fa-user" },
          { id: "assigned", label: "Assigned to Me", icon: "fa-thumbtack" },
          { id: "fresh", label: "Fresh Pool", icon: "fa-water" }
        ].map(s => (
          <button 
            key={s.id}
            onClick={() => { setSegment(s.id as any); setPage(1); }}
            className={`flex-1 min-w-[120px] px-4 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 ${
              segment === s.id 
                ? 'bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-100' 
                : 'text-slate-500 hover:bg-slate-50 border border-transparent'
            }`}
          >
            <i className={`fas ${s.icon}`}></i> {s.label}
          </button>
        ))}
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-bold text-slate-800">
            {segment === 'my' ? 'Your Owned Leads' : segment === 'assigned' ? 'Delegated to You' : 'Unclaimed Leads'}
            <span className="ml-3 text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-1 rounded-md">{totalLeads} Total</span>
          </h2>
          <div className="relative">
            <i className="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs"></i>
            <input type="text" placeholder="Search by name or phone..." className="pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 w-64" />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Lead Contact</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status & Priority</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Source</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Created</th>
                <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    <i className="fas fa-circle-notch fa-spin text-3xl mb-3"></i>
                    <p className="font-medium">Syncing CRM Database...</p>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-rose-500">
                    <i className="fas fa-exclamation-triangle text-3xl mb-3"></i>
                    <p className="font-medium">{error}</p>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center text-slate-500">
                    <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center text-3xl text-slate-400 mx-auto mb-4">
                      <i className="fas fa-folder-open"></i>
                    </div>
                    <p className="font-bold text-slate-700 text-lg mb-1">No leads found in this segment</p>
                    <p className="text-sm">Try switching tabs or adjusting your search filters.</p>
                  </td>
                </tr>
              ) : (
                leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-indigo-50/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center text-indigo-700 font-bold shrink-0">
                          {(lead.name || "?")[0].toUpperCase()}
                        </div>
                        <div>
                          <p className="font-bold text-slate-900 group-hover:text-indigo-700 transition-colors">{lead.name}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-slate-500"><i className="fas fa-phone-alt text-[10px] mr-1"></i>{lead.phone}</span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-2 items-start">
                        {getStatusBadge(lead.status)}
                        {getPriorityBadge(lead.priority)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-1 rounded-md border border-slate-200">
                        {lead.source || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm font-semibold text-slate-700">{new Date(lead.created_at).toLocaleDateString()}</p>
                      <p className="text-xs text-slate-500">{new Date(lead.created_at).toLocaleTimeString()}</p>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-2 text-indigo-600 bg-indigo-50 hover:bg-indigo-100 hover:text-indigo-800 rounded-lg transition-colors font-bold text-sm inline-flex items-center gap-2">
                        View <i className="fas fa-chevron-right text-xs"></i>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination Footer */}
        {!loading && totalPages > 1 && (
          <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50">
            <span className="text-sm font-medium text-slate-600">Page {page} of {totalPages}</span>
            <div className="flex gap-2">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-white hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Previous
              </button>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 border border-slate-200 rounded-lg text-sm font-bold text-slate-700 hover:bg-white hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
