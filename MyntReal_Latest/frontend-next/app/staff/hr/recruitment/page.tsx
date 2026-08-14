"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Candidate {
  id: number;
  name: string;
  email: string;
  phone: string;
  position_applied: string;
  application_date: string;
  status: string;
  experience_years: number;
}

export default function RecruitmentPage() {
  const { token } = useStaffAuth();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchCandidates = async () => {
      try {
        setLoading(true);
        // Using generic HR recruitment endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/hr/candidates`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setCandidates(data.items || []);
        } else {
          setCandidates([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch candidates, using empty state", err);
        setCandidates([]);
      } finally {
        setLoading(false);
      }
    };

    fetchCandidates();
  }, [token]);

  const filteredCandidates = candidates.filter(c => 
    (c.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     c.position_applied.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (statusFilter === "" || c.status === statusFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Recruitment & Candidates</h1>
          <p className="text-sm text-gray-500 mt-2">Manage job postings, applicant tracking, and interview pipelines.</p>
        </div>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-briefcase mr-2"></i> Job Postings
          </button>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Add Candidate
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Applicants</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{candidates.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Screening</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {candidates.filter(c => c.status === "SCREENING").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Interviewing</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            {candidates.filter(c => c.status === "INTERVIEWING").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Offered / Hired</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {candidates.filter(c => c.status === "OFFERED" || c.status === "HIRED").length}
          </p>
        </div>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input 
                type="text" 
                placeholder="Search candidates..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <select 
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Stages</option>
              <option value="NEW">New Applied</option>
              <option value="SCREENING">Screening</option>
              <option value="INTERVIEWING">Interviewing</option>
              <option value="OFFERED">Offered</option>
              <option value="HIRED">Hired</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading candidate pipeline...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-user-tie text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No candidates found</h3>
            <p className="text-gray-500 mb-4">There are currently no applicants matching your filters.</p>
            <button className="px-4 py-2 font-medium rounded hover:opacity-90 transition-colors bg-indigo-50 text-indigo-600">
              Create Job Posting
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Applicant Name</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Position Applied</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Applied On</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Exp. (Yrs)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Stage</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredCandidates.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{c.name}</p>
                      <p className="text-xs text-gray-500">{c.email}</p>
                    </td>
                    <td className="p-4 text-sm font-medium text-indigo-600">{c.position_applied}</td>
                    <td className="p-4 text-sm text-gray-600">
                      {new Date(c.application_date).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-sm font-bold text-gray-900">{c.experience_years}</span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        c.status === "HIRED" || c.status === "OFFERED" ? "bg-green-100 text-green-800" : 
                        c.status === "REJECTED" ? "bg-red-100 text-red-800" :
                        c.status === "INTERVIEWING" ? "bg-blue-100 text-blue-800" :
                        "bg-amber-100 text-amber-800"
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <Link href={`/staff/hr/recruitment/${c.id}`} className="text-indigo-600 hover:text-indigo-800 text-sm font-medium mx-2">
                        View
                      </Link>
                      <button className="text-gray-500 hover:text-gray-800 text-sm font-medium mx-2">
                        <i className="fas fa-file-pdf"></i>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
