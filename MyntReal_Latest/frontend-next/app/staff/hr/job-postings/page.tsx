"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";

interface JobPosting {
  id: string;
  title: string;
  department: string;
  location: string;
  job_type: string;
  status: string;
  created_at: string;
  actual_applicants: number;
  base_display_count: number;
}

export default function JobPostings() {
  const [activeTab, setActiveTab] = useState("active");
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJobs();
  }, [activeTab]);

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      // Pass status query parameter to fetch filtered jobs
      const res = await api.get(`/staff/hr/jobs?status=${activeTab}`);
      // Based on careers.py the backend returns a flat array in `res.data`
      if (Array.isArray(res.data)) {
        setJobs(res.data);
      } else if (res.data && Array.isArray(res.data.items)) {
        setJobs(res.data.items);
      } else {
        setJobs([]);
      }
    } catch (err: any) {
      console.error("Failed to fetch jobs:", err);
      if (err.response?.status === 403) {
        setError("You do not have HR privileges to view job postings.");
      } else {
        setError("Failed to load job postings. Please try again.");
      }
    } finally {
      setLoading(false);
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
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Job Postings</h1>
          <p className="text-sm text-gray-500 mt-1">Manage recruitment pipelines and active job vacancies.</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={fetchJobs}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-sm"
          >
            <i className="fas fa-sync-alt mr-2"></i> Refresh
          </button>
          <button className="px-5 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-bold shadow-md hover:bg-black transition-colors">
            <i className="fas fa-plus mr-2"></i> Create Job Post
          </button>
        </div>
      </div>

      {/* Tabs & Search */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-4">
        <nav className="flex space-x-8 overflow-x-auto custom-scrollbar">
          {["active", "draft", "closed"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors capitalize -mb-[17px]
                ${activeTab === tab
                  ? "border-gray-900 text-gray-900"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"}
              `}
            >
              {tab} Postings
            </button>
          ))}
        </nav>
        
        <div className="relative w-full md:w-64">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <i className="fas fa-search text-gray-400"></i>
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-gray-200 rounded-lg leading-5 bg-white placeholder-gray-400 focus:outline-none focus:ring-gray-900 focus:border-gray-900 sm:text-sm transition-colors shadow-sm"
            placeholder="Search roles..."
          />
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 text-sm font-medium flex items-center gap-2">
          <i className="fas fa-shield-alt text-lg"></i>
          {error}
        </div>
      )}

      {/* Job List */}
      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          // Skeleton loader
          [...Array(3)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-24 mb-3"></div>
                  <div className="h-6 bg-gray-200 rounded w-64 mb-3"></div>
                  <div className="h-4 bg-gray-100 rounded w-96"></div>
                </div>
                <div className="flex gap-6">
                  <div className="w-16 h-12 bg-gray-200 rounded-lg"></div>
                  <div className="w-24 h-10 bg-gray-200 rounded-lg"></div>
                </div>
              </div>
            </div>
          ))
        ) : jobs.length > 0 ? (
          jobs.map((job) => (
            <div key={job.id} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow group">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                
                {/* Left: Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-semibold text-gray-500 uppercase tracking-wider">#{job.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-gray-100 text-gray-600 border border-gray-200">
                      {job.job_type || 'Full-Time'}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition-colors">{job.title}</h3>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    <span className="flex items-center gap-1.5"><i className="fas fa-building text-gray-400"></i> {job.department || 'General'}</span>
                    <span className="flex items-center gap-1.5"><i className="fas fa-map-marker-alt text-gray-400"></i> {job.location || 'Remote'}</span>
                    <span className="flex items-center gap-1.5"><i className="far fa-calendar-alt text-gray-400"></i> {formatDate(job.created_at)}</span>
                  </div>
                </div>

                {/* Right: Stats & Actions */}
                <div className="flex items-center justify-between md:justify-end gap-6 md:w-1/3">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900">{(job.actual_applicants || 0) + (job.base_display_count || 0)}</p>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Applicants</p>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <button className="px-4 py-2 bg-gray-50 text-gray-700 text-sm font-semibold border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors shadow-sm">
                      View
                    </button>
                    <button className="w-9 h-9 flex items-center justify-center text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors border border-transparent hover:border-gray-200">
                      <i className="fas fa-ellipsis-v"></i>
                    </button>
                  </div>
                </div>
                
              </div>
            </div>
          ))
        ) : !error ? (
          <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-12 text-center">
            <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm border border-gray-100">
               <i className="fas fa-folder-open text-2xl text-gray-300"></i>
            </div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">No Postings Found</h3>
            <p className="text-gray-500">There are no {activeTab} job postings at this time.</p>
          </div>
        ) : null}
      </div>

    </div>
  );
}
