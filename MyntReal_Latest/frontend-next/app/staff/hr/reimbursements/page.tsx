"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface ReimbursementClaim {
  id: number;
  claim_number: string;
  employee_name: string;
  employee_id: string;
  category: string; // TRAVEL, MEALS, SUPPLIES
  amount: number;
  date_incurred: string;
  date_submitted: string;
  status: string; // PENDING, APPROVED, REJECTED, PAID
  has_receipt: boolean;
}

export default function ReimbursementsPage() {
  const { token } = useStaffAuth();
  const [claims, setClaims] = useState<ReimbursementClaim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("PENDING");

  useEffect(() => {
    if (!token) return;
    
    const fetchClaims = async () => {
      try {
        setLoading(true);
        // Using generic HR reimbursements endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/hr/reimbursements`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setClaims(data.items || []);
        } else {
          setClaims([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch claims, using empty state", err);
        setClaims([]);
      } finally {
        setLoading(false);
      }
    };

    fetchClaims();
  }, [token]);

  const filteredClaims = claims.filter(c => 
    (c.employee_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
     c.claim_number.toLowerCase().includes(searchTerm.toLowerCase())) &&
    (statusFilter === "" || c.status === statusFilter)
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Reimbursements & Claims</h1>
          <p className="text-sm text-gray-500 mt-2">Process employee expenses, review receipts, and approve reimbursements.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/hr/employees" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-users mr-2"></i> Directory
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-file-invoice-dollar mr-2"></i> Submit Claim
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Pending Review</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {claims.filter(c => c.status === "PENDING").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Pending Payment</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            ₹{claims.filter(c => c.status === "APPROVED").reduce((sum, c) => sum + c.amount, 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Paid (MTD)</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            ₹{claims.filter(c => c.status === "PAID").reduce((sum, c) => sum + c.amount, 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-red-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Rejected</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            {claims.filter(c => c.status === "REJECTED").length}
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
                placeholder="Search claim or employee..." 
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
              <option value="PENDING">Pending Review</option>
              <option value="APPROVED">Approved (Pending Payout)</option>
              <option value="PAID">Paid</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading reimbursement claims...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredClaims.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-receipt text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No claims found</h3>
            <p className="text-gray-500 mb-4">There are currently no reimbursement claims matching your criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Claim No.</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Employee</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Category</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date Incurred</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Amount (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredClaims.map(claim => (
                  <tr key={claim.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm font-medium text-indigo-600">{claim.claim_number}</td>
                    <td className="p-4">
                      <p className="text-sm font-bold text-gray-900">{claim.employee_name}</p>
                      <p className="text-xs text-gray-500">{claim.employee_id}</p>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center space-x-2">
                        <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-medium">
                          {claim.category.replace('_', ' ')}
                        </span>
                        {claim.has_receipt && (
                          <i className="fas fa-paperclip text-gray-400" title="Receipt attached"></i>
                        )}
                      </div>
                    </td>
                    <td className="p-4 text-sm text-gray-600">
                      {new Date(claim.date_incurred).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-right">
                      <p className="text-sm font-bold text-gray-900">{claim.amount.toFixed(2)}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        claim.status === "PAID" ? "bg-green-100 text-green-800" : 
                        claim.status === "APPROVED" ? "bg-blue-100 text-blue-800" :
                        claim.status === "REJECTED" ? "bg-red-100 text-red-800" :
                        "bg-amber-100 text-amber-800"
                      }`}>
                        {claim.status}
                      </span>
                    </td>
                    <td className="p-4 text-center space-x-2">
                      <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                        Review
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
