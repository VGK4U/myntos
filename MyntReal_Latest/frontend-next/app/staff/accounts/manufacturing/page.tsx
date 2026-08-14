"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useStaffAuth } from "@/contexts/StaffAuthContext";
import { getApiUrl } from "@/lib/api";

interface ManufacturingEntry {
  id: number;
  journal_no: string;
  date: string;
  bom_number: string;
  product_name: string;
  quantity_produced: number;
  total_cost: number;
  status: string;
}

export default function ManufacturingPage() {
  const { token } = useStaffAuth();
  const [entries, setEntries] = useState<ManufacturingEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    if (!token) return;
    
    const fetchManufacturing = async () => {
      try {
        setLoading(true);
        // Using generic manufacturing endpoint
        const res = await fetch(`${getApiUrl()}/api/v1/staff/inventory/manufacturing`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        
        if (res.ok) {
          const data = await res.json();
          setEntries(data.items || []);
        } else {
          setEntries([]); // Fallback
        }
      } catch (err: any) {
        console.warn("Failed to fetch manufacturing journals, using empty state", err);
        setEntries([]);
      } finally {
        setLoading(false);
      }
    };

    fetchManufacturing();
  }, [token]);

  const filteredEntries = entries.filter(e => 
    e.product_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    e.journal_no.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Manufacturing Journal</h1>
          <p className="text-sm text-gray-500 mt-2">Track production runs, raw material consumption, and finished goods output.</p>
        </div>
        <div className="flex space-x-3">
          <Link href="/staff/accounts/bom" className="px-4 py-2 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg shadow-sm hover:bg-gray-50 transition-colors">
            <i className="fas fa-sitemap mr-2"></i> BOM Master
          </Link>
          <button className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg shadow-sm hover:bg-indigo-700 transition-colors">
            <i className="fas fa-plus mr-2"></i> New Production Run
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-indigo-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Runs (MTD)</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{entries.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-green-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Total Output Qty</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {entries.reduce((sum, e) => sum + e.quantity_produced, 0)}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-amber-500">
          <p className="text-xs font-bold text-gray-500 uppercase">In Progress</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">
            {entries.filter(e => e.status === "IN_PROGRESS").length}
          </p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border-l-4 border-blue-500">
          <p className="text-xs font-bold text-gray-500 uppercase">Est. Production Cost</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            ₹{entries.reduce((sum, e) => sum + e.total_cost, 0).toFixed(2)}
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
                placeholder="Search production runs..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:border-indigo-500 outline-none w-64" 
              />
            </div>
            <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-700 outline-none">
              <option value="">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
          <button className="text-gray-500 hover:text-gray-700">
            <i className="fas fa-filter mr-1"></i> Filter Date
          </button>
        </div>
        
        {loading ? (
          <div className="p-12 text-center text-gray-500">
            <i className="fas fa-spinner fa-spin text-3xl mb-3 text-indigo-500"></i>
            <p>Loading production records...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500 bg-red-50">
            <i className="fas fa-exclamation-triangle text-2xl mb-2"></i>
            <p>{error}</p>
          </div>
        ) : filteredEntries.length === 0 ? (
          <div className="p-16 text-center text-gray-500 flex flex-col items-center">
            <div className="w-16 h-16 bg-indigo-50 text-indigo-300 rounded-full flex items-center justify-center mb-4">
              <i className="fas fa-industry text-2xl"></i>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-1">No manufacturing runs</h3>
            <p className="text-gray-500 mb-4">There are currently no production runs recorded.</p>
            <button className="px-4 py-2 font-medium rounded hover:opacity-90 transition-colors bg-indigo-50 text-indigo-600">
              Start New Production
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Journal No.</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Product (Output)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">BOM Ref</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Qty Produced</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Total Cost (₹)</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Status</th>
                  <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredEntries.map(entry => (
                  <tr key={entry.id} className="hover:bg-gray-50 transition-colors">
                    <td className="p-4 text-sm text-gray-600">{new Date(entry.date).toLocaleDateString()}</td>
                    <td className="p-4 text-sm font-medium text-indigo-600">{entry.journal_no}</td>
                    <td className="p-4 text-sm font-bold text-gray-900">{entry.product_name}</td>
                    <td className="p-4 text-sm text-gray-600">{entry.bom_number}</td>
                    <td className="p-4 text-right">
                      <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded text-sm font-bold">
                        {entry.quantity_produced}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <p className="text-sm font-bold text-gray-900">{entry.total_cost.toFixed(2)}</p>
                    </td>
                    <td className="p-4 text-center">
                      <span className={`text-[10px] font-bold px-2 py-1 rounded ${
                        entry.status === "COMPLETED" ? "bg-green-100 text-green-800" : 
                        entry.status === "IN_PROGRESS" ? "bg-amber-100 text-amber-800" :
                        "bg-red-100 text-red-800"
                      }`}>
                        {entry.status}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <Link href={`/staff/accounts/manufacturing/${entry.id}`} className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                        View Details
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
