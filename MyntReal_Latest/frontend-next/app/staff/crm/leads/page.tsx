"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Lead {
  id: number;
  name: string;
  phone: string;
  email: string;
  source: string;
  assigned_to: string;
  status: string; // NEW, CONTACTED, INTERESTED, NEGOTIATION, CONVERTED, DEAD
  created_at: string;
  last_contacted_at: string | null;
}

export default function LeadsManagerPage() {
  const { token, hasRole } = useStaffAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchLeads = async () => {
      try {
        setLoading(true);
        // Using generic CRM leads endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/crm/leads`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setLeads(data.items || []);
        } else {
          setLeads([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch leads, using empty state", err);
        setLeads([]);
      } finally {
        setLoading(false);
      }
    };

    fetchLeads();
  }, [token]);

  const filteredLeads = leads.filter(l => 
    (l.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     l.phone.includes(searchTerm)) &&
    (statusFilter === "" || l.status === statusFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Leads Manager</h1>
          <p className="text-sm text-gray-500 mt-2">Track, assign, and convert your incoming leads from all sources.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/crm/dashboard" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-chart-pie mr-2"></i> Analytics
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Add Lead
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50 flex-wrap gap-4">
          <div className="flex items-center space-x-4 flex-grow max-w-2xl">
            <div className="relative flex-grow">
              <i className="fas fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
              <input 
                type="text" 
                placeholder="Search name or phone..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none" 
              />
            </div>
            <select 
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none w-48"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="NEW">New (Uncontacted)</option>
              <option value="CONTACTED">Contacted</option>
              <option value="INTERESTED">Interested</option>
              <option value="NEGOTIATION">Negotiation</option>
              <option value="CONVERTED">Converted</option>
              <option value="DEAD">Dead / Lost</option>
            </select>
          </div>
          <div className="flex space-x-2">
            <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
              <i className="fas fa-filter mr-1"></i> Advanced
            </button>
            <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
              <i className="fas fa-file-export mr-1"></i> Export
            </button>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading your leads...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredLeads.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-user-tag text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No leads found</h3>
            <p className="text-gray-500 mb-4">There are currently no leads matching your search criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Lead Info</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Contact</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Source & Agent</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Last Activity</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredLeads.map(lead => (
                  <tr key={lead.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{lead.name}</p>
                      <p className="text-xs text-gray-500">Added: {new Date(lead.created_at).toLocaleDateString()}</p>
                    </td>
                    <td className="p-4">
                      <p className="text-sm font-medium text-indigo-600">{lead.phone}</p>
                      <p className="text-xs text-gray-500">{lead.email || 'No email'}</p>
                    </td>
                    <td className="p-4">
                      <span className="inline-block bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs font-medium mb-1">
                        {lead.source}
                      </span>
                      <p className="text-xs font-medium text-gray-900 mt-1">
                        <i className="fas fa-headset text-gray-400 mr-1"></i>
                        {lead.assigned_to}
                      </p>
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      {lead.last_contacted_at 
                        ? new Date(lead.last_contacted_at).toLocaleDateString() 
                        : <span className="text-red-500 font-medium">Never</span>}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        lead.status === "NEW" ? "bg-blue-100 text-blue-800" :
                        lead.status === "CONVERTED" ? "bg-green-100 text-green-800" : 
                        lead.status === "DEAD" ? "bg-gray-200 text-gray-800" :
                        lead.status === "INTERESTED" ? "bg-amber-100 text-amber-800" :
                        "bg-purple-100 text-purple-800"
                      }`}>
                        {lead.status}
                      </span>
                    </td>
                    <td className="p-4 text-center space-x-3">
                      <button className="text-green-500 hover:text-green-700 text-sm" title="WhatsApp">
                        <i className="fab fa-whatsapp text-lg"></i>
                      </button>
                      <button className="text-indigo-500 hover:text-indigo-700 text-sm" title="Call">
                        <i className="fas fa-phone-alt"></i>
                      </button>
                      <Link href={`/staff/crm/leads/${lead.id}`} className="text-gray-500 hover:text-gray-800 text-sm font-medium">
                        View
                      </Link>
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
