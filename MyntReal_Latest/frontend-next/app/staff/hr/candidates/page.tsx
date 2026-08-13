"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";

interface Candidate {
  id: number;
  job_id: number;
  job_title: string;
  full_name: string;
  email: string;
  phone: string;
  exp_years: number;
  current_company: string;
  status: string;
  applied_at: string;
}

export default function Candidates() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination and filtering
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  const APP_STATUSES = ["applied", "reviewing", "interview", "offered", "hired", "rejected"];

  useEffect(() => {
    fetchCandidates();
  }, [page, statusFilter]);

  const fetchCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      let url = `/staff/hr/applications?page=${page}&page_size=20`;
      if (statusFilter !== "all") url += `&status=${statusFilter}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;

      const res = await api.get(url);
      
      if (Array.isArray(res.data)) {
        setCandidates(res.data);
      } else if (res.data && Array.isArray(res.data.applications)) {
        setCandidates(res.data.applications);
      } else if (res.data && Array.isArray(res.data.items)) {
        setCandidates(res.data.items);
      } else {
        setCandidates([]);
      }
    } catch (err: any) {
      console.error("Failed to fetch candidates:", err);
      if (err.response?.status === 403) {
        setError("You do not have HR privileges to view candidates.");
      } else {
        setError("Failed to load candidates. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch(status) {
      case 'applied': return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'reviewing': return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'interview': return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'offered': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case 'hired': return 'bg-gray-900 text-white border-black';
      case 'rejected': return 'bg-rose-100 text-rose-700 border-rose-200';
      default: return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in zoom-in duration-500">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Candidates Pipeline</h1>
          <p className="text-sm text-gray-500 mt-1">Review, track, and manage job applications.</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchCandidates}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-sm"
          >
            <i className="fas fa-sync-alt mr-2"></i> Refresh
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center gap-4">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <i className="fas fa-search text-gray-400"></i>
          </div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchCandidates()}
            className="block w-full pl-10 pr-3 py-2 border border-gray-200 rounded-lg leading-5 bg-gray-50 placeholder-gray-400 focus:outline-none focus:ring-gray-900 focus:border-gray-900 focus:bg-white sm:text-sm transition-colors"
            placeholder="Search by name, email, or phone (Press Enter)"
          />
        </div>
        
        <div className="flex items-center gap-3 w-full md:w-auto">
          <select 
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="block w-full md:w-48 pl-3 pr-10 py-2 text-base border-gray-200 focus:outline-none focus:ring-gray-900 focus:border-gray-900 sm:text-sm rounded-lg bg-gray-50"
          >
            <option value="all">All Statuses</option>
            {APP_STATUSES.map(s => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 text-sm font-medium flex items-center gap-2">
          <i className="fas fa-shield-alt text-lg"></i>
          {error}
        </div>
      )}

      {/* Candidates Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Candidate</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Applied Position</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Experience</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Applied Date</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                <th scope="col" className="px-6 py-4 text-right text-xs font-bold text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-32 mb-2"></div><div className="h-3 bg-gray-100 rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-40"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-16"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-6 bg-gray-200 rounded-full w-20"></div></td>
                    <td className="px-6 py-4 text-right"><div className="h-8 bg-gray-200 rounded w-16 ml-auto"></div></td>
                  </tr>
                ))
              ) : candidates.length > 0 ? (
                candidates.map((candidate) => (
                  <tr key={candidate.id} className="hover:bg-gray-50 transition-colors group">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-gray-900">{candidate.full_name}</span>
                        <div className="text-xs text-gray-500 mt-1 flex items-center gap-3">
                          <span className="flex items-center gap-1"><i className="fas fa-envelope text-gray-400"></i> {candidate.email}</span>
                          <span className="flex items-center gap-1"><i className="fas fa-phone text-gray-400"></i> {candidate.phone}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 font-medium">{candidate.job_title || 'Unknown Job'}</div>
                      <div className="text-xs text-gray-500 mt-1">ID: #{candidate.job_id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{candidate.exp_years} Years</div>
                      <div className="text-xs text-gray-500 truncate max-w-[150px]">{candidate.current_company || '-'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(candidate.applied_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 inline-flex text-xs leading-5 font-bold rounded-full border uppercase tracking-wider ${getStatusBadgeColor(candidate.status)}`}>
                        {candidate.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button className="text-gray-400 hover:text-gray-900 transition-colors p-2 rounded-lg hover:bg-gray-100">
                        <i className="fas fa-external-link-alt"></i>
                      </button>
                    </td>
                  </tr>
                ))
              ) : !error ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-3">
                      <i className="fas fa-users text-gray-400 text-xl"></i>
                    </div>
                    <p className="text-sm font-medium text-gray-900">No candidates found.</p>
                    <p className="text-sm text-gray-500 mt-1">Try adjusting your search or filters.</p>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        
        {/* Pagination placeholder */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing <span className="font-medium">1</span> to <span className="font-medium">{candidates.length}</span> candidates
          </div>
          <div className="flex gap-2">
            <button 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <button 
              onClick={() => setPage(p => p + 1)}
              disabled={candidates.length < 20}
              className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
