"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface ProcurementEntry {
  id: number;
  request_no: string;
  date: string;
  requested_by: string;
  department: string;
  total_items: number;
  estimated_cost: number;
  status: string;
  priority: string;
}

export default function ProcurementPage() {
  const { token } = useStaffAuth();
  const [requests, setRequests] = useState<ProcurementEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchProcurement = async () => {
      try {
        setLoading(true);
        // Using generic procurement endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/inventory/procurement`, {
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

    fetchProcurement();
  }, [token]);

  const filteredRequests = requests.filter(r => 
    r.request_no.toLowerCase().includes(searchTerm.toLowerCase()) || 
    r.requested_by.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.department.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Procurement & Requisitions</h1>
          <p className="text-sm text-gray-500 mt-2">Manage purchase requests, approvals, and raw material procurement tracking.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/vendors" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-store mr-2"></i> Vendor Directory
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> New Requisition
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Pending Approval</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {requests.filter(r => r.status === "PENDING_APPROVAL").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Approved & Pending PO</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            {requests.filter(r => r.status === "APPROVED").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">PO Issued / In Transit</p>
          <p className="text-2xl font-bold text-indigo-600 mt-1">
            {requests.filter(r => r.status === "PO_ISSUED").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Completed (MTD)</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {requests.filter(r => r.status === "COMPLETED").length}
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
                placeholder="Search requisitions..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none">
              <option value="">All Priorities</option>
              <option value="HIGH">High Priority</option>
              <option value="NORMAL">Normal</option>
              <option value="LOW">Low</option>
            </select>
          </div>
          <button className="text-gray-500 hover:text-gray-700">
            <i className="fas fa-filter mr-1"></i> Advanced Filter
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
              <i className="fas fa-shopping-basket text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No requisitions found</h3>
            <p className="text-gray-500 mb-4">There are currently no procurement requests recorded.</p>
            <button className="px-4 py-2 font-medium rounded hover:opacity-90 transition-colors bg-indigo-50 text-indigo-600">
              Create New Requisition
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Req No.</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Requested By / Dept</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Items</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Est. Cost (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Priority</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredRequests.map(req => (
                  <tr key={req.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm text-gray-600">{new Date(req.date).toLocaleDateString()}</td>
                    <td className="p-4 text-sm font-medium text-indigo-600">{req.request_no}</td>
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{req.requested_by}</p>
                      <p className="text-xs text-gray-500">{req.department}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs font-bold">
                        {req.total_items} items
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <p className="text-sm font-bold text-gray-900">{req.estimated_cost.toFixed(2)}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-xs font-bold ${
                        req.priority === "HIGH" ? "text-red-600" : 
                        req.priority === "LOW" ? "text-gray-500" : "text-amber-600"
                      }`}>
                        <i className={`fas ${req.priority === 'HIGH' ? 'fa-arrow-up' : req.priority === 'LOW' ? 'fa-arrow-down' : 'fa-minus'} mr-1`}></i>
                        {req.priority}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        req.status === "COMPLETED" ? "bg-green-100 text-green-800" : 
                        req.status === "PO_ISSUED" ? "bg-indigo-100 text-indigo-800" :
                        req.status === "APPROVED" ? "bg-blue-100 text-blue-800" :
                        req.status === "REJECTED" ? "bg-red-100 text-red-800" :
                        "bg-amber-100 text-amber-800" // Pending
                      }`}>
                        {req.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <Link href={`/staff/accounts/procurement/${req.id}`} className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                        Review
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
