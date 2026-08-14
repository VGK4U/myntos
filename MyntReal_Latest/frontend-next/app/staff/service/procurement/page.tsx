"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface ProcurementRequest {
  id: number;
  request_number: string;
  job_number: string | null;
  requested_by: string;
  part_name: string;
  part_number: string;
  quantity: number;
  urgency: string; // STANDARD, HIGH, AOG
  status: string; // PENDING, APPROVED, ORDERED, RECEIVED, REJECTED
  request_date: string;
}

export default function ServiceProcurementPage() {
  const { token } = useStaffAuth();
  const [requests, setRequests] = useState<ProcurementRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("PENDING");

  useEffect(() => {
    if (!token) return;
    
    const fetchRequests = async () => {
      try {
        setLoading(true);
        // Using generic Service endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/service/procurement`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setRequests(data.items || []);
        } else {
          setRequests([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch procurement requests, using empty state", err);
        setRequests([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRequests();
  }, [token]);

  const filteredRequests = requests.filter(r => 
    (r.part_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     r.part_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
     r.request_number.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (statusFilter === "" || r.status === statusFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Service Spares Procurement</h1>
          <p className="text-sm text-gray-500 mt-2">Manage internal requests for replacement parts, tools, and consumables for service jobs.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/service/tracking" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-map-marker-alt mr-2"></i> Shop Floor
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Request Part
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Pending Approvals</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {requests.filter(r => r.status === "PENDING").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Ordered (In Transit)</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            {requests.filter(r => r.status === "ORDERED").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-500">
          <p className="text-xs font-bold text-gray-500 uppercase">AOG (Urgent)</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            {requests.filter(r => r.urgency === "AOG" && r.status !== "RECEIVED" && r.status !== "REJECTED").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Received (MTD)</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {requests.filter(r => r.status === "RECEIVED").length}
          </p>
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
                placeholder="Search part name, number, or request ID..." 
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
              <option value="PENDING">Pending Approval</option>
              <option value="APPROVED">Approved (To Order)</option>
              <option value="ORDERED">Ordered</option>
              <option value="RECEIVED">Received</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
          <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
            <i className="fas fa-file-export mr-1"></i> Export Log
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading procurement requests...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredRequests.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-box-open text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No requests found</h3>
            <p className="text-gray-500 mb-4">There are currently no procurement requests matching your filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Request Details</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Part Information</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Qty</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Urgency</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredRequests.map(req => (
                  <tr key={req.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-bold text-indigo-600">{req.request_number}</p>
                      {req.job_number && (
                        <p className="text-xs text-gray-500 mt-0.5">For Job: {req.job_number}</p>
                      )}
                      <p className="text-xs text-gray-400 mt-1">By: {req.requested_by}</p>
                    </td>
                    <td className="p-4">
                      <p className="text-sm font-medium text-gray-900">{req.part_name}</p>
                      <p className="text-xs font-mono text-gray-500 mt-0.5">PN: {req.part_number}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-sm font-bold text-gray-900">{req.quantity}</span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${
                        req.urgency === "AOG" ? "border-red-200 bg-red-50 text-red-700" :
                        req.urgency === "HIGH" ? "border-amber-200 bg-amber-50 text-amber-700" : 
                        "border-gray-200 bg-gray-50 text-gray-700"
                      }`}>
                        {req.urgency}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        req.status === "PENDING" ? "bg-amber-100 text-amber-800" :
                        req.status === "APPROVED" ? "bg-blue-100 text-blue-800" :
                        req.status === "ORDERED" ? "bg-purple-100 text-purple-800" :
                        req.status === "RECEIVED" ? "bg-green-100 text-green-800" : 
                        "bg-red-100 text-red-800"
                      }`}>
                        {req.status}
                      </span>
                    </td>
                    <td className="p-4 text-center space-x-2">
                      {req.status === "PENDING" ? (
                        <>
                          <button className="text-green-600 hover:text-green-800 text-sm font-medium" title="Approve">
                            <i className="fas fa-check"></i>
                          </button>
                          <button className="text-red-600 hover:text-red-800 text-sm font-medium" title="Reject">
                            <i className="fas fa-times"></i>
                          </button>
                        </>
                      ) : (
                        <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                          Update
                        </button>
                      )}
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
