"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface LeaveRequest {
  id: number;
  employee_name: string;
  employee_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  total_days: number;
  reason: string;
  status: string; // PENDING, APPROVED, REJECTED
  applied_on: string;
}

export default function LeaveManagementPage() {
  const { token } = useStaffAuth();
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("PENDING");

  useEffect(() => {
    if (!token) return;
    
    const fetchLeaves = async () => {
      try {
        setLoading(true);
        // Using generic HR leaves endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/hr/leaves`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setLeaves(data.items || []);
        } else {
          setLeaves([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch leaves, using empty state", err);
        setLeaves([]);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaves();
  }, [token]);

  const filteredLeaves = leaves.filter(l => 
    (l.employee_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     l.employee_id.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (statusFilter === "" || l.status === statusFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Leave Management</h1>
          <p className="text-sm text-gray-500 mt-2">Approve employee leave requests, track PTO balances, and manage team availability.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/hr/attendance" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-clock mr-2"></i> Attendance
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> Apply Leave (Admin)
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Pending Approvals</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {leaves.filter(l => l.status === "PENDING").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Approved (MTD)</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {leaves.filter(l => l.status === "APPROVED").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Rejected (MTD)</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            {leaves.filter(l => l.status === "REJECTED").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Leave Days</p>
          <p className="text-2xl font-bold text-indigo-600 mt-1">
            {leaves.filter(l => l.status === "APPROVED").reduce((sum, l) => sum + l.total_days, 0)}
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
                placeholder="Search employee..." 
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
              <option value="">All Statuses</option>
              <option value="PENDING">Pending Approval</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading leave requests...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredLeaves.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-umbrella-beach text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No leave requests found</h3>
            <p className="text-gray-500 mb-4">There are currently no leaves matching your criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Employee</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Leave Type</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Duration</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Days</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Applied On</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredLeaves.map(leave => (
                  <tr key={leave.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{leave.employee_name}</p>
                      <p className="text-xs text-gray-500">{leave.employee_id}</p>
                    </td>
                    <td className="p-4">
                      <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-medium">
                        {leave.leave_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      {new Date(leave.start_date).toLocaleDateString()} - {new Date(leave.end_date).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-center">
                      <span className="text-sm font-bold text-indigo-600">{leave.total_days}</span>
                    </td>
                    <td className="p-4 text-sm text-gray-500">
                      {new Date(leave.applied_on).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        leave.status === "APPROVED" ? "bg-green-100 text-green-800" : 
                        leave.status === "REJECTED" ? "bg-red-100 text-red-800" :
                        "bg-amber-100 text-amber-800"
                      }`}>
                        {leave.status}
                      </span>
                    </td>
                    <td className="p-4 text-center space-x-2">
                      {leave.status === "PENDING" ? (
                        <>
                          <button className="text-green-600 hover:text-green-800 text-sm font-medium">
                            <i className="fas fa-check"></i>
                          </button>
                          <button className="text-red-600 hover:text-red-800 text-sm font-medium">
                            <i className="fas fa-times"></i>
                          </button>
                        </>
                      ) : (
                        <button className="text-gray-400 hover:text-gray-600 text-sm font-medium">
                          <i className="fas fa-eye"></i>
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
