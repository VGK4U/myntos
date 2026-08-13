"use client";

import { useState } from "react";
import Link from "next/link";

// Mock data
const MOCK_LEADS = [
  { id: "L-9082", name: "Ramesh Sharma", phone: "+91 98765 43210", source: "Meta Ads", product: "Flats (3BHK)", status: "New", assignedTo: "Unassigned", date: "Today, 10:45 AM" },
  { id: "L-9081", name: "Sunita Verma", phone: "+91 99887 76655", source: "Website", product: "Plots (Premium)", status: "Contacted", assignedTo: "Priya S.", date: "Today, 09:15 AM" },
  { id: "L-9080", name: "Anil Kumar", phone: "+91 91234 56789", source: "Referral", product: "Commercial", status: "Site Visit", assignedTo: "Rahul K.", date: "Yesterday" },
  { id: "L-9079", name: "Meera Reddy", phone: "+91 98888 77777", source: "WhatsApp", product: "Flats (2BHK)", status: "Negotiation", assignedTo: "Anita", date: "Yesterday" },
  { id: "L-9078", name: "Vikram Singh", phone: "+91 95555 44444", source: "Meta Ads", product: "Plots (Standard)", status: "Closed Won", assignedTo: "Rahul K.", date: "Aug 10, 2026" },
  { id: "L-9077", name: "Pooja Patel", phone: "+91 92222 11111", source: "Walk-in", product: "Flats (3BHK)", status: "Lost", assignedTo: "Priya S.", date: "Aug 09, 2026" },
];

export default function CRMAllLeadsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const filteredLeads = MOCK_LEADS.filter(lead => {
    const matchesSearch = lead.name.toLowerCase().includes(searchTerm.toLowerCase()) || lead.phone.includes(searchTerm);
    const matchesStatus = statusFilter === "All" || lead.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight mb-1">All Leads Database</h1>
          <p className="text-gray-500">Manage, filter, and track all incoming leads across all channels.</p>
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 font-bold rounded-lg shadow-sm hover:bg-gray-50 transition-colors text-sm">
            <i className="fas fa-download mr-2"></i> Export CSV
          </button>
          <button className="px-4 py-2 bg-gray-900 text-white font-bold rounded-lg shadow-sm hover:bg-black transition-colors text-sm">
            <i className="fas fa-plus mr-2"></i> Add Lead
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {/* Filters and Search Header */}
        <div className="p-4 border-b border-gray-100 bg-gray-50/50 flex flex-col md:flex-row gap-4 justify-between items-center">
          <div className="relative w-full md:w-96">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <i className="fas fa-search text-gray-400"></i>
            </div>
            <input
              type="text"
              placeholder="Search by name or phone..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-gray-900 focus:border-gray-900"
            />
          </div>

          <div className="flex flex-wrap gap-2 w-full md:w-auto">
            <select 
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-lg text-sm bg-white focus:ring-gray-900 focus:border-gray-900 py-2 px-3 flex-1 md:flex-none"
            >
              <option value="All">All Statuses</option>
              <option value="New">New</option>
              <option value="Contacted">Contacted</option>
              <option value="Site Visit">Site Visit</option>
              <option value="Negotiation">Negotiation</option>
              <option value="Closed Won">Closed Won</option>
              <option value="Lost">Lost</option>
            </select>

            <select className="border border-gray-300 rounded-lg text-sm bg-white focus:ring-gray-900 focus:border-gray-900 py-2 px-3 flex-1 md:flex-none">
              <option>All Agents</option>
              <option>Unassigned</option>
              <option>Priya S.</option>
              <option>Rahul K.</option>
            </select>
          </div>
        </div>

        {/* Data Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white border-b border-gray-200 text-xs uppercase tracking-wider text-gray-500">
                <th className="p-4 font-bold">Lead Details</th>
                <th className="p-4 font-bold">Contact</th>
                <th className="p-4 font-bold">Source / Product</th>
                <th className="p-4 font-bold">Status</th>
                <th className="p-4 font-bold">Assigned To</th>
                <th className="p-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredLeads.map((lead) => (
                <tr key={lead.id} className="hover:bg-gray-50 transition-colors">
                  <td className="p-4">
                    <div className="font-bold text-gray-900">{lead.name}</div>
                    <div className="text-xs text-gray-500">{lead.id} • {lead.date}</div>
                  </td>
                  <td className="p-4">
                    <div className="text-sm text-gray-900 font-medium">{lead.phone}</div>
                    <div className="flex gap-2 mt-1">
                      <button className="text-emerald-500 hover:text-emerald-600" title="WhatsApp"><i className="fab fa-whatsapp"></i></button>
                      <button className="text-blue-500 hover:text-blue-600" title="Call"><i className="fas fa-phone-alt"></i></button>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="text-sm font-medium text-gray-900">{lead.source}</div>
                    <div className="text-xs text-gray-500">{lead.product}</div>
                  </td>
                  <td className="p-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold
                      ${lead.status === 'New' ? 'bg-blue-100 text-blue-800' : ''}
                      ${lead.status === 'Contacted' ? 'bg-indigo-100 text-indigo-800' : ''}
                      ${lead.status === 'Site Visit' ? 'bg-amber-100 text-amber-800' : ''}
                      ${lead.status === 'Negotiation' ? 'bg-orange-100 text-orange-800' : ''}
                      ${lead.status === 'Closed Won' ? 'bg-emerald-100 text-emerald-800' : ''}
                      ${lead.status === 'Lost' ? 'bg-rose-100 text-rose-800' : ''}
                    `}>
                      {lead.status}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className={`text-sm ${lead.assignedTo === 'Unassigned' ? 'text-rose-500 font-bold' : 'text-gray-900 font-medium'}`}>
                      {lead.assignedTo}
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <button className="px-3 py-1.5 bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 rounded text-xs font-bold transition-colors">
                      View Profile
                    </button>
                  </td>
                </tr>
              ))}
              {filteredLeads.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-gray-500">
                    No leads found matching your criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="p-4 border-t border-gray-100 bg-gray-50 flex items-center justify-between text-sm">
          <span className="text-gray-500">Showing 1 to {filteredLeads.length} of 1,245 entries</span>
          <div className="flex gap-1">
            <button className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-500 disabled:opacity-50" disabled>Previous</button>
            <button className="px-3 py-1 border border-gray-900 rounded bg-gray-900 text-white font-bold">1</button>
            <button className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50">2</button>
            <button className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50">3</button>
            <span className="px-2 py-1 text-gray-400">...</span>
            <button className="px-3 py-1 border border-gray-300 rounded bg-white text-gray-700 hover:bg-gray-50">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
