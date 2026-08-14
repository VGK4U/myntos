"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface Ticket {
  id: number;
  ticket_number: string;
  customer_name: string;
  subject: string;
  priority: string; // LOW, MEDIUM, HIGH, URGENT
  status: string; // OPEN, IN_PROGRESS, WAITING, RESOLVED, CLOSED
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
}

export default function TicketQueuePage() {
  const { token } = useStaffAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("OPEN"); // Default to open tickets

  useEffect(() => {
    if (!token) return;
    
    const fetchTickets = async () => {
      try {
        setLoading(true);
        // Using generic Service endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/service/tickets`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setTickets(data.items || []);
        } else {
          setTickets([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch tickets, using empty state", err);
        setTickets([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTickets();
  }, [token]);

  const filteredTickets = tickets.filter(t => 
    (t.ticket_number.toLowerCase().includes(searchTerm.toLowerCase()) || 
     t.customer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
     t.subject.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (statusFilter === "" || 
     (statusFilter === "OPEN" && ["OPEN", "IN_PROGRESS", "WAITING"].includes(t.status)) ||
     (statusFilter === "RESOLVED" && ["RESOLVED", "CLOSED"].includes(t.status)) ||
     t.status === statusFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Support Ticket Queue</h1>
          <p className="text-sm text-gray-500 mt-2">Manage customer issues, assign technicians, and track resolution SLAs.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/service/dashboard" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-chart-line mr-2"></i> Dashboard
          </Link>
          <Link href="/staff/service/tickets/new" className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Raise Ticket
          </Link>
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
                placeholder="Search ticket #, customer, or subject..." 
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
              <option value="">All Tickets</option>
              <option value="OPEN">All Active (Open/IP/Wait)</option>
              <option value="UNASSIGNED">Unassigned</option>
              <option value="RESOLVED">Resolved / Closed</option>
              <option value="URGENT">Urgent Priority</option>
            </select>
          </div>
          <div className="flex space-x-2">
            <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
              <i className="fas fa-filter mr-1"></i> Filters
            </button>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading ticket queue...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-ticket-alt text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No tickets found</h3>
            <p className="text-gray-500 mb-4">There are currently no tickets matching your filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Ticket Details</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Customer</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Priority</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Assigned To</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Last Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredTickets.map(ticket => (
                  <tr key={ticket.id} className="hover:bg-gray-50 transition-colors cursor-pointer">
                    <td className="p-4">
                      <div className="flex items-start space-x-3">
                        <i className={`fas fa-circle text-[8px] mt-1.5 ${ticket.status === 'OPEN' ? 'text-blue-500' : 'text-gray-300'}`}></i>
                        <div>
                          <p className="text-sm font-bold text-indigo-600 mb-0.5">{ticket.ticket_number}</p>
                          <p className="text-sm text-gray-900 line-clamp-1 max-w-xs">{ticket.subject}</p>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <p className="text-sm font-medium text-gray-900">{ticket.customer_name}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
                        ticket.priority === "URGENT" ? "border-red-200 bg-red-50 text-red-700" :
                        ticket.priority === "HIGH" ? "border-amber-200 bg-amber-50 text-amber-700" : 
                        ticket.priority === "MEDIUM" ? "border-blue-200 bg-blue-50 text-blue-700" : 
                        "border-gray-200 bg-gray-50 text-gray-700"
                      }`}>
                        <i className={`fas fa-flag text-[8px] mr-1`}></i> {ticket.priority}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        ticket.status === "OPEN" ? "bg-blue-100 text-blue-800" :
                        ticket.status === "IN_PROGRESS" ? "bg-indigo-100 text-indigo-800" :
                        ticket.status === "RESOLVED" ? "bg-green-100 text-green-800" : 
                        ticket.status === "WAITING" ? "bg-amber-100 text-amber-800" :
                        "bg-gray-200 text-gray-800"
                      }`}>
                        {ticket.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4">
                      {ticket.assigned_to ? (
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-[10px]">
                            {ticket.assigned_to.charAt(0)}
                          </div>
                          <span className="text-sm text-gray-700">{ticket.assigned_to}</span>
                        </div>
                      ) : (
                        <button className="text-xs font-medium text-indigo-600 hover:text-indigo-800 border border-dashed border-indigo-300 rounded px-2 py-1 hover:bg-indigo-50 transition-colors">
                          Assign
                        </button>
                      )}
                    </td>
                    <td className="p-4 text-sm text-gray-500">
                      {new Date(ticket.updated_at).toLocaleString([], {month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit'})}
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
