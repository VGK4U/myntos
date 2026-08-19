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
}

export default function MyLeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination / Filter states (can be expanded later)
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalLeads, setTotalLeads] = useState(0);

  useEffect(() => {
    fetchLeads();
  }, [page]);

  const fetchLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      // Backend expects company_id as per DC protocol for data siloing
      const res = await api.get(`/api/v1/crm/unified-my-leads/search-partner?q=${encodeURIComponent("")}`);
      
      if (res.data && res.data.leads) {
        setLeads(res.data.leads);
        setTotalPages(res.data.total_pages || 1);
        setTotalLeads(res.data.total || res.data.leads.length);
      } else if (Array.isArray(res.data)) {
        // Fallback if backend returns flat array
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
    if (s === 'new') return <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold uppercase tracking-wider">New</span>;
    if (s === 'contacted') return <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-bold uppercase tracking-wider">Contacted</span>;
    if (s === 'interested') return <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold uppercase tracking-wider">Interested</span>;
    if (s === 'won' || s === 'converted') return <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold uppercase tracking-wider">Won</span>;
    if (s === 'lost' || s === 'dead') return <span className="px-2 py-1 bg-rose-100 text-rose-700 rounded-full text-xs font-bold uppercase tracking-wider">Lost</span>;
    return <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-bold uppercase tracking-wider">{status}</span>;
  };

  const getPriorityBadge = (priority: string) => {
    const p = (priority || "").toLowerCase();
    if (p === 'high') return <span className="text-rose-500 font-bold"><i className="fas fa-fire mr-1"></i> High</span>;
    if (p === 'medium') return <span className="text-amber-500 font-bold"><i className="fas fa-grip-lines mr-1"></i> Medium</span>;
    if (p === 'low') return <span className="text-blue-500 font-bold"><i className="fas fa-arrow-down mr-1"></i> Low</span>;
    return <span>{priority}</span>;
  };

  return (
    <div className="max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Leads Pipeline</h1>
          <p className="text-sm text-gray-500 mt-1">Manage and track your assigned leads</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={fetchLeads}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-sm"
          >
            <i className="fas fa-sync-alt mr-2"></i>Refresh
          </button>
          <Link 
            href="/staff/leads/add-lead"
            className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-bold shadow-sm hover:bg-black transition-colors flex items-center"
          >
            <i className="fas fa-plus mr-2"></i>Add Lead
          </Link>
        </div>
      </div>

      {/* Stats/Filters Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-blue-600">
              <i className="fas fa-users"></i>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-medium uppercase">Total Leads</p>
              <p className="text-lg font-bold text-gray-900">{totalLeads}</p>
            </div>
          </div>
        </div>
        
        <div className="relative">
          <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
          <input 
            type="text"
            placeholder="Search leads..."
            className="pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all w-64"
          />
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {error && (
          <div className="p-4 bg-rose-50 border-b border-rose-200 text-rose-600 text-sm font-medium flex items-center justify-between">
            <span className="flex items-center gap-2"><i className="fas fa-exclamation-triangle"></i> {error}</span>
            <button onClick={fetchLeads} className="underline hover:text-rose-800">Retry</button>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Lead Info</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Contact</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Priority</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Source</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Created Date</th>
                <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                // Loading Skeleton
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="p-4"><div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div><div className="h-3 bg-gray-100 rounded w-1/2"></div></td>
                    <td className="p-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                    <td className="p-4"><div className="h-6 bg-gray-200 rounded-full w-20"></div></td>
                    <td className="p-4"><div className="h-4 bg-gray-200 rounded w-16"></div></td>
                    <td className="p-4"><div className="h-4 bg-gray-200 rounded w-20"></div></td>
                    <td className="p-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                    <td className="p-4 text-right"><div className="h-8 bg-gray-200 rounded w-8 ml-auto"></div></td>
                  </tr>
                ))
              ) : leads.length === 0 ? (
                // Empty State
                <tr>
                  <td colSpan={7} className="p-12 text-center">
                    <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
                      <i className="fas fa-inbox text-2xl"></i>
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 mb-1">No Leads Found</h3>
                    <p className="text-gray-500 mb-4 text-sm">You don't have any leads assigned to you yet.</p>
                    <Link 
                      href="/staff/leads/add-lead"
                      className="inline-flex items-center text-sm font-bold text-gray-900 hover:text-gray-600"
                    >
                      <i className="fas fa-plus mr-2"></i>Create your first lead
                    </Link>
                  </td>
                </tr>
              ) : (
                // Data Rows
                leads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-gray-50 transition-colors group">
                    <td className="p-4">
                      <div className="font-bold text-gray-900">{lead.name}</div>
                      <div className="text-xs text-gray-500 mt-1">ID: #{lead.id}</div>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center text-sm text-gray-900">
                        <i className="fas fa-phone-alt text-gray-400 w-4 mr-1 text-xs"></i>
                        {lead.phone}
                      </div>
                      {lead.email && (
                        <div className="flex items-center text-xs text-gray-500 mt-1">
                          <i className="fas fa-envelope text-gray-400 w-4 mr-1"></i>
                          {lead.email}
                        </div>
                      )}
                    </td>
                    <td className="p-4">
                      {getStatusBadge(lead.status)}
                    </td>
                    <td className="p-4 text-sm">
                      {getPriorityBadge(lead.priority)}
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      {lead.source || '-'}
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      {new Date(lead.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </td>
                    <td className="p-4 text-right">
                      <button className="w-8 h-8 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-900 hover:text-white hover:border-gray-900 transition-all opacity-0 group-hover:opacity-100">
                        <i className="fas fa-chevron-right"></i>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <div className="p-4 border-t border-gray-200 flex items-center justify-between bg-gray-50/50">
            <span className="text-sm text-gray-500">
              Showing page <span className="font-bold text-gray-900">{page}</span> of <span className="font-bold text-gray-900">{totalPages}</span>
            </span>
            <div className="flex gap-2">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-gray-300 rounded text-sm text-gray-600 hover:bg-white disabled:opacity-50"
              >
                Previous
              </button>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-300 rounded text-sm text-gray-600 hover:bg-white disabled:opacity-50"
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
